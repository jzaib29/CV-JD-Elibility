"""Official Groq SDK behind CrewAI BaseLLM; one HTTP request per stage."""
import copy
import time
from crewai import BaseLLM
from groq import Groq, APIConnectionError, APITimeoutError, APIStatusError
from applywise.models import Usage

DEFAULT_MODEL = "openai/gpt-oss-20b"
MODELS = (DEFAULT_MODEL, "openai/gpt-oss-120b")


class ProviderError(RuntimeError):
    """Contains only messages safe for display, never raw provider data."""


def strict_schema(schema):
    result = copy.deepcopy(schema)

    def walk(node):
        if isinstance(node, dict):
            for key in ("default", "minItems", "maxItems", "minLength", "maxLength"):
                node.pop(key, None)
            if node.get("type") == "object":
                node["additionalProperties"] = False
                node["required"] = list(node.get("properties", {}))
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)
    walk(result)
    return result


class GroqLLM(BaseLLM):
    def __init__(self, api_key, model, schema, stage, client=None):
        if model not in MODELS:
            raise ProviderError("Select a supported Groq model in Settings.")
        super().__init__(model=model, temperature=0)
        self.client = client or Groq(api_key=api_key, timeout=75, max_retries=0)
        self.schema = strict_schema(schema)
        self.usage = Usage(stage=stage)

    def supports_function_calling(self):
        return False

    def supports_stop_words(self):
        return False

    def get_context_window_size(self):
        return 131_072

    def call(self, messages, tools=None, callbacks=None, available_functions=None, **kwargs):
        if self.usage.requests >= 1:
            raise ProviderError("This stage reached its one-request limit. Review inputs before retrying.")
        if tools:
            raise ProviderError("External tools are disabled for resume analysis.")
        if isinstance(messages, str):
            messages = [{"role": "user", "content": messages}]
        self.usage.requests += 1
        started = time.monotonic()
        try:
            response = self.client.chat.completions.create(
                model=self.model, messages=messages, temperature=0,
                reasoning_effort="low", max_completion_tokens=7000,
                response_format={"type": "json_schema", "json_schema": {
                    "name": "resume_result", "strict": True, "schema": self.schema}},
            )
            if response.usage:
                self.usage.input_tokens = response.usage.prompt_tokens
                self.usage.output_tokens = response.usage.completion_tokens
            choice = response.choices[0]
            if choice.finish_reason != "stop" or not choice.message.content:
                raise ProviderError("The response was incomplete. Shorten the documents and retry.")
            return "Final Answer: " + choice.message.content
        except APITimeoutError as exc:
            raise ProviderError("Groq timed out. Inputs are retained; retry when ready.") from exc
        except APIConnectionError as exc:
            raise ProviderError("Could not reach Groq. Check your connection.") from exc
        except APIStatusError as exc:
            safe = {
                400: "Groq rejected the request. Check the selected model and shorten inputs.",
                401: "Groq rejected the API key. Check Settings or deployment Secrets.",
                403: "This Groq project does not have access to the model.",
                404: "The model is unavailable. Check Groq's current model catalog.",
                413: "The request is too large. Shorten your documents.",
                429: "Groq's rate/token limit was reached. Wait or check your account quota.",
            }
            raise ProviderError(safe.get(exc.status_code, "Groq is temporarily unavailable. Retry later.")) from exc
        finally:
            self.usage.seconds = round(time.monotonic() - started, 2)

    def close(self):
        self.client.close()
