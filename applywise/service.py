"""Two agents with explicit UI checkpoints and no hidden repair calls."""
import json
from crewai import Agent
from pydantic import ValidationError
from applywise.llm import GroqLLM, ProviderError
from applywise.models import Analysis, EditPlan, ReferencedAnalysis, ReferencedEditPlan
from applywise.prompts import ANALYST, EDITOR
from applywise.validation import OutputError, validate_analysis, validate_edits, sources


def resolve_references(result, source_map, output_type):
    """Copy evidence from supplied sources, never model-authored quotations."""
    data = result.model_dump()
    key = "requirements" if output_type is Analysis else "edits"
    for index, item in enumerate(data[key], 1):
        resolved = []
        seen = set()
        for evidence in item["evidence"]:
            sid = evidence["source_id"]
            if sid not in source_map:
                raise OutputError(
                    f"{key.capitalize()} item {index} cited an unknown source ID. "
                    "No unverified result was applied."
                )
            if sid not in seen:
                resolved.append({"source_id": sid, "quote": source_map[sid]})
                seen.add(sid)
        item["evidence"] = resolved
    return output_type.model_validate(data)


def references_only(analysis):
    if analysis is None:
        return None
    data = analysis.model_dump()
    for requirement in data["requirements"]:
        requirement["evidence"] = [{"source_id": e["source_id"]} for e in requirement["evidence"]]
    return data


class ResumeService:
    def __init__(self, api_key, model):
        self.api_key, self.model, self.usage = api_key, model, []

    def _run(self, role, instructions, payload, output_type, stage):
        llm = GroqLLM(self.api_key, self.model, output_type.model_json_schema(), stage)
        try:
            agent = Agent(role=role, goal="Produce a concise, evidence-grounded JSON result.",
                          backstory=instructions, llm=llm, tools=[],
                          allow_delegation=False, reasoning=False, verbose=False,
                          max_iter=2, max_retry_limit=0, respect_context_window=False)
            # Provider enforces schema; do not enable CrewAI's extra-call converter.
            result = agent.kickoff("Process this JSON DATA according to your instructions:\n" +
                                   json.dumps(payload, ensure_ascii=False))
            raw = result.raw.strip().removeprefix("Final Answer:").strip()
            return output_type.model_validate_json(raw)
        except (ValidationError, json.JSONDecodeError) as exc:
            raise OutputError("The response failed its contract. Nothing was applied. You may retry explicitly.") from exc
        except (ProviderError, OutputError):
            raise
        except Exception as exc:
            current = exc
            for _ in range(5):
                if isinstance(current, ProviderError):
                    raise current
                current = current.__cause__ or current.__context__
                if current is None:
                    break
            raise ProviderError("The agent could not finish. Check key, model access, and input length before retrying.") from exc
        finally:
            self.usage.append(llm.usage)
            llm.close()

    def analyze(self, cv, jd, answers=None, previous=None, allow_questions=True):
        answers = answers or []
        result = self._run("Graduate application analyst", ANALYST,
                           {"resume": [b.model_dump() for b in cv.blocks],
                            "job_description": jd.text,
                            "confirmed_answers": [a.model_dump() for a in answers],
                            "previous_analysis": references_only(previous),
                            "allow_questions": bool(allow_questions and previous is None)},
                           ReferencedAnalysis, "Clarification" if previous else "Analysis")
        result = resolve_references(result, sources(cv, answers), Analysis)
        if not allow_questions:
            result.questions = []
        return validate_analysis(result, cv, jd, answers, previous)

    def edit(self, cv, analysis, answers):
        if not analysis.target_block_ids and not analysis.restructure:
            return EditPlan(edits=[], layout=[], notes=["No changes were needed based on this assessment."])
        targets = set(analysis.target_block_ids)
        evidence_ids = {e.source_id for r in analysis.requirements for e in r.evidence}
        selected = [b for b in cv.blocks if analysis.restructure or b.id in targets | evidence_ids]
        result = self._run("Evidence-led resume editor", EDITOR,
                           {"target_blocks": [b.model_dump() for b in cv.blocks if b.id in targets],
                            "candidate_evidence": [b.model_dump() for b in selected],
                            "confirmed_answers": [a.model_dump() for a in answers],
                            "requirements": references_only(analysis)["requirements"],
                            "restructure": analysis.restructure,
                            "structure_reason": analysis.structure_reason}, ReferencedEditPlan, "Editing")
        selected_sources = {**{b.id: b.text for b in selected},
                            **{a.id: a.text for a in answers}}
        result = resolve_references(result, selected_sources, EditPlan)
        return validate_edits(result, cv, answers, analysis)
