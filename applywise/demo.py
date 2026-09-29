"""Fixed fictional sample; never substituted for failed live inference."""
from pathlib import Path
from applywise.documents import from_text
from applywise.models import Analysis, Answer, EditPlan, Evidence

ROOT = Path(__file__).resolve().parent.parent


def documents():
    return (from_text((ROOT / "examples/resume.txt").read_text(), "Demo resume"),
            from_text((ROOT / "examples/job.txt").read_text(), "Demo job", "J"))


def analysis():
    cv, _ = documents()
    facts = {b.id: b.text for b in cv.blocks}
    criteria = [
        ("Relevant bachelor's degree", "A bachelor's degree in computer science or a related discipline is required.", "required", True, "supported", "C4", "The listed degree matches the subject requirement."),
        ("Python and pandas", "Python and pandas for data cleaning are required.", "required", False, "supported", "C5", "The university project demonstrates relevant data cleaning."),
        ("SQL querying", "SQL querying skills are required.", "required", False, "not_evidenced", None, "SQL is not stated; that does not establish absence of the skill."),
        ("Communication and teamwork", "Ability to communicate findings and work with a team is required.", "required", False, "partial", "C8", "Volunteering demonstrates explanation and teamwork; analytical presentations are not explicit."),
        ("Power BI", "Power BI experience is preferred.", "preferred", False, "not_evidenced", None, "Power BI experience is not stated."),
    ]
    requirements = []
    for i, (label, quote, importance, gate, status, source, reason) in enumerate(criteria):
        requirements.append(dict(id=f"R{i+1}", label=label, job_quote=quote, importance=importance,
                                 hard_gate=gate, status=status, reason=reason,
                                 evidence=[dict(source_id=source, quote=facts[source])] if source else []))
    return Analysis.model_validate(dict(
        role="Junior Data Analyst",
        summary="Your Python project supports data-cleaning work. SQL and Power BI are not yet evidenced; relevant coursework could clarify those gaps.",
        requirements=requirements,
        questions=[dict(id="Q1", requirement_id="R3", question="Have you used SQL in coursework or a project? Describe your contribution.", why="SQL is required but not mentioned."),
                   dict(id="Q2", requirement_id="R5", question="Have you built a Power BI report or dashboard? What did you build?", why="This could evidence a preferred skill.")],
        target_block_ids=["C3", "C5"], restructure=False,
        structure_reason="Recognizable sections already exist.",
    ))


def demo_answers():
    return [Answer(id="A1", requirement_id="R3", question=analysis().questions[0].question,
                   text="In database coursework, I wrote SQL SELECT queries with JOIN and GROUP BY to summarize a library database.")]


def clarified():
    result = analysis()
    result.questions = []
    result.requirements[2].status = "supported"
    result.requirements[2].evidence = [Evidence(source_id="A1", quote=demo_answers()[0].text)]
    result.requirements[2].reason = "The candidate confirms relevant SQL coursework; this is self-reported evidence."
    result.summary = "Python project work and confirmed SQL coursework cover the main technical requirements. Power BI remains unevidenced and is preferred, not mandatory."
    return result


def edits():
    cv, _ = documents()
    return EditPlan.model_validate(dict(edits=[
        dict(block_id="C3", replacement="Computer science graduate with university project experience in Python, pandas, data cleaning, and reporting.",
             reason="Bring relevant existing project work into the summary.",
             evidence=[dict(source_id="C4", quote="BS Computer Science"), dict(source_id="C5", quote=cv.blocks[4].text)]),
        dict(block_id="C5", replacement="Used Python and pandas to clean survey data and create charts for a university reporting system.",
             reason="Lead with the tools and work most relevant to the role.",
             evidence=[dict(source_id="C5", quote=cv.blocks[4].text)]),
    ], layout=[], notes=["SQL and Power BI remain gaps unless supported by your own experience."]))
