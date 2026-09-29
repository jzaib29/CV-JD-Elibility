"""Provenance and structural checks, not proof of semantic truth."""
import re
from collections import Counter
from applywise.models import Scorecard


class OutputError(ValueError):
    pass


def norm(text):
    return " ".join(text.split()).casefold()


def sources(cv, answers):
    return {**{b.id: b.text for b in cv.blocks}, **{a.id: a.text for a in answers}}


def check_evidence(evidence, source_map, context="Evidence"):
    """Repair only unambiguous, verbatim source attribution; never fuzzy-match."""
    for index, e in enumerate(evidence, 1):
        quote = norm(e.quote)
        prefix = f"{context}, evidence {index}"
        if len(quote) < 3:
            raise OutputError(f"{prefix}: quote is empty or too short. No result was applied.")
        if e.source_id in source_map and quote in norm(source_map[e.source_id]):
            continue
        matches = [sid for sid, text in source_map.items() if quote in norm(text)]
        if len(matches) == 1:
            # Correct a source ID only when the supplied text uniquely proves it.
            e.source_id = matches[0]
            continue
        detail = ("quote matches multiple other blocks; its source is ambiguous"
                  if matches else "quote was not found in any supplied resume block or answer")
        raise OutputError(
            f"{prefix}: {detail}. No unverified result was applied. "
            "Retry the analysis explicitly; do not change your resume to match the model."
        )


def validate_analysis(result, cv, jd, answers, previous=None):
    ids = [r.id for r in result.requirements]
    if len(set(ids)) != len(ids):
        raise OutputError("Duplicate requirement identifiers were returned.")
    for req_index, req in enumerate(result.requirements, 1):
        if not req.job_quote.strip() or norm(req.job_quote) not in norm(jd.text):
            raise OutputError("A requirement could not be traced to the job description.")
        check_evidence(req.evidence, sources(cv, answers), f"Requirement {req_index}")
        if req.status != "not_evidenced" and not req.evidence:
            raise OutputError("A qualification assessment lacked supporting evidence.")
    if previous:
        old = {r.id: r for r in previous.requirements}
        if set(ids) != set(old):
            raise OutputError("The clarification changed the requirement set.")
        for req in result.requirements:
            for field in ("label", "job_quote", "importance", "hard_gate"):
                setattr(req, field, getattr(old[req.id], field))
        if result.questions:
            raise OutputError("Only one optional question round is allowed.")
    if len({q.id for q in result.questions}) != len(result.questions):
        raise OutputError("Duplicate questions were returned.")
    if any(q.requirement_id not in ids for q in result.questions):
        raise OutputError("A question referred to an unknown requirement.")
    if not set(result.target_block_ids) <= {b.id for b in cv.blocks}:
        raise OutputError("An edit target was not found in the resume.")
    return result


def score_analysis(result):
    weights = {"required": 3, "preferred": 1}
    points = {"supported": 1, "partial": .5, "not_evidenced": 0, "contradicted": 0}
    total = sum(weights[r.importance] for r in result.requirements)
    score = round(10 * sum(weights[r.importance] * points[r.status] for r in result.requirements) / total, 1)
    gates = [r for r in result.requirements if r.hard_gate]
    if any(r.status == "contradicted" for r in gates):
        eligibility, advice = "Confirmed mismatch", "Resolve prerequisite first"
        reason = "Supplied evidence conflicts with an explicit prerequisite; better wording cannot remove it."
    elif any(r.status != "supported" for r in gates):
        eligibility, advice = "Needs clarification", "Clarify prerequisite first"
        reason = "An explicit prerequisite remains unevidenced. This does not establish ineligibility."
    else:
        eligibility = "Stated gates supported" if gates else "No explicit gates identified"
        advice = "Apply" if score >= 7 else "Consider as a stretch"
        reason = "Your supplied evidence covers much of the role." if score >= 7 else "Review the gaps before investing time; you can still choose to apply."
    return Scorecard(score=score, supported=sum(r.status == "supported" for r in result.requirements),
                     total=len(result.requirements), eligibility=eligibility, recommendation=advice, reason=reason)


def validate_edits(plan, cv, answers, analysis):
    source_map, seen = sources(cv, answers), set()
    for edit_index, edit in enumerate(plan.edits, 1):
        if edit.block_id not in analysis.target_block_ids or edit.block_id in seen:
            raise OutputError("An edit targeted an unapproved or duplicate block.")
        seen.add(edit.block_id)
        if not edit.replacement.strip() or len(edit.replacement) > 1500:
            raise OutputError("An edit was empty or too long.")
        check_evidence(edit.evidence, source_map, f"Edit {edit_index}")
        supported = source_map[edit.block_id] + " " + " ".join(e.quote for e in edit.evidence)
        def numbers(value):
            return set(re.findall(r"\d+(?:[.,]\d+)*%?", value))
        if not numbers(edit.replacement) <= numbers(supported):
            raise OutputError("An edit introduced an unsupported number or date.")
    if analysis.restructure:
        proposed = [bid for section in plan.layout for bid in section.block_ids]
        if Counter(proposed) != Counter(b.id for b in cv.blocks):
            raise OutputError("The full layout omitted or duplicated original content.")
    elif plan.layout:
        raise OutputError("A full layout was returned when section edits were requested.")
    return plan
