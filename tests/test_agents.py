"""Real CrewAI execution; fake Groq transport. No network/key required."""
from types import SimpleNamespace
from unittest.mock import Mock
import pytest
from applywise import demo
from applywise.llm import DEFAULT_MODEL, GroqLLM, ProviderError, strict_schema
from applywise.models import Analysis
from applywise.service import ResumeService
from applywise.validation import OutputError


def response(content):
    return SimpleNamespace(choices=[SimpleNamespace(finish_reason="stop", message=SimpleNamespace(content=content))],
                           usage=SimpleNamespace(prompt_tokens=100, completion_tokens=50))


def test_adapter_budget():
    client = Mock()
    client.chat.completions.create.return_value = response(demo.analysis().model_dump_json())
    llm = GroqLLM("fake", DEFAULT_MODEL, Analysis.model_json_schema(), "test", client)
    assert llm.call("data").startswith("Final Answer:")
    with pytest.raises(ProviderError, match="limit"):
        llm.call("second attempt")
    assert client.chat.completions.create.call_count == 1
    assert llm.usage.input_tokens == 100
    schema = strict_schema(Analysis.model_json_schema())
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == set(schema["properties"])


def test_crewai_end_to_end(monkeypatch):
    client = Mock()
    client.chat.completions.create.side_effect = [response(x.model_dump_json()) for x in [demo.analysis(), demo.clarified(), demo.edits()]]
    monkeypatch.setattr("applywise.llm.Groq", lambda **kwargs: client)
    service = ResumeService("fake", DEFAULT_MODEL)
    cv, jd = demo.documents()
    first = service.analyze(cv, jd)
    second = service.analyze(cv, jd, demo.demo_answers(), first)
    assert len(service.edit(cv, second, demo.demo_answers()).edits) == 2
    assert client.chat.completions.create.call_count == 3
    assert [u.requests for u in service.usage] == [1, 1, 1]


def test_questions_can_be_disabled(monkeypatch):
    client = Mock()
    client.chat.completions.create.return_value = response(demo.analysis().model_dump_json())
    monkeypatch.setattr("applywise.llm.Groq", lambda **kwargs: client)
    result = ResumeService("fake", DEFAULT_MODEL).analyze(*demo.documents(), allow_questions=False)
    assert result.questions == []
    assert client.chat.completions.create.call_count == 1


def test_no_targets_no_call(monkeypatch):
    client = Mock()
    monkeypatch.setattr("applywise.llm.Groq", lambda **kwargs: client)
    result = demo.analysis()
    result.target_block_ids = []
    assert ResumeService("fake", DEFAULT_MODEL).edit(demo.documents()[0], result, []).edits == []
    assert not client.chat.completions.create.called


def test_truncated_response():
    client, result = Mock(), response('{"partial":')
    result.choices[0].finish_reason = "length"
    client.chat.completions.create.return_value = result
    with pytest.raises(ProviderError, match="incomplete"):
        GroqLLM("fake", DEFAULT_MODEL, Analysis.model_json_schema(), "test", client).call("data")


def test_malformed_output_no_retry(monkeypatch):
    client = Mock()
    client.chat.completions.create.return_value = response('{"invalid":true}')
    monkeypatch.setattr("applywise.llm.Groq", lambda **kwargs: client)
    with pytest.raises(OutputError):
        ResumeService("fake", DEFAULT_MODEL).analyze(*demo.documents())
    assert client.chat.completions.create.call_count == 1
