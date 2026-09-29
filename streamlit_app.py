"""Run: python -m streamlit run streamlit_app.py"""
import hmac
import os
import streamlit as st
from applywise import demo
from applywise.documents import InputError, from_file, from_text
from applywise.export import assemble, as_text, as_docx
from applywise.models import Answer
from applywise.ui import hero, heading, steps, style
from applywise.validation import OutputError, score_analysis, validate_analysis, validate_edits

st.set_page_config(page_title="Applywise · A clearer next step", page_icon="↗", layout="wide")
style()


def setting(name, fallback=""):
    if os.environ.get(name):
        return os.environ[name]
    try:
        return str(st.secrets.get(name, fallback))
    except (FileNotFoundError, st.errors.StreamlitSecretNotFoundError):
        return fallback


def reset():
    for key in list(st.session_state):
        del st.session_state[key]


def run_stage(method, *args, **kwargs):
    from applywise.llm import ProviderError
    from applywise.service import ResumeService
    service = ResumeService(api_key, model)
    try:
        return getattr(service, method)(*args, **kwargs)
    except (ProviderError, OutputError) as exc:
        st.error(str(exc))
        return None
    finally:
        st.session_state.setdefault("usage", []).extend(service.usage)


password = setting("APP_PASSWORD")
if password and not st.session_state.get("authenticated"):
    hero()
    with st.form("access"):
        entered = st.text_input("Workspace password", type="password")
        if st.form_submit_button("Open workspace", type="primary"):
            if hmac.compare_digest(entered, password):
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("That password did not match.")
    st.stop()

with st.sidebar:
    st.markdown("## ↗ applywise")
    st.caption("LESS GUESSWORK. MORE DIRECTION.")
    st.divider()
    st.markdown("**Your application workspace**")
    st.write("Understand your fit before rewriting your story.")
    with st.expander("Settings", expanded=not setting("GROQ_API_KEY")):
        typed_key = st.text_input("Groq API key", type="password", key="api_key_input")
        models = ["openai/gpt-oss-20b", "openai/gpt-oss-120b"]
        configured = setting("GROQ_MODEL", models[0])
        model = st.selectbox("Model", models, index=models.index(configured) if configured in models else 0)
        st.caption("20B is the lower-cost default. Model access depends on your Groq project.")
    api_key = typed_key.strip() or setting("GROQ_API_KEY")
    st.caption("KEY CONFIGURED" if api_key else "DEMO AVAILABLE · NO KEY NEEDED")
    st.button("Clear workspace", on_click=reset, width="stretch")
    st.divider()
    st.caption("Uploads stay in this session. Live analysis sends extracted text and answers to Groq. No shared document cache or database is used.")
    if st.session_state.get("usage"):
        usage = st.session_state.usage
        with st.expander("Run details"):
            st.write(f"Requests attempted: {sum(u.requests for u in usage)}")
            st.write(f"Reported tokens: {sum(u.input_tokens+u.output_tokens for u in usage):,}")
            st.caption("Failed requests may not report tokens. See Groq for billing.")
            st.dataframe([u.model_dump() for u in usage], hide_index=True)

hero()
stage = st.session_state.get("stage", "input")
steps({"input": 0, "review": 1, "edit": 2}[stage])
if st.session_state.get("demo_mode"):
    st.info("DEMO PREVIEW · Fictional sample data and fixed outputs. No LLM requests. Clear the workspace to analyze your own documents.")

if stage == "input":
    left, right = st.columns([3, 1])
    with left:
        heading("Start here", "Two documents. One clearer direction.", "Add your resume and the full job description.")
    with right:
        if st.button("Try the sample demo ↗", width="stretch"):
            cv, jd = demo.documents()
            result = validate_analysis(demo.analysis(), cv, jd, [])
            st.session_state.update(cv=cv, jd=jd, analysis=result, answers=[], demo_mode=True,
                                    questions_done=False, stage="review")
            st.rerun()
    values = {}
    for column, label, prefix in zip(st.columns(2, gap="large"), ["Your resume", "Job description"], ["C", "J"]):
        with column, st.container(border=True):
            st.markdown(f"#### {label}")
            mode = st.radio(f"Input method for {label.lower()}", ["Paste text", "Upload file"], horizontal=True, key=f"mode_{prefix}")
            if mode == "Paste text":
                values[prefix] = ("text", st.text_area(label, height=240, key=f"text_{prefix}",
                                                       placeholder="Paste complete content here…", label_visibility="collapsed"))
            else:
                values[prefix] = ("file", st.file_uploader(label, type=["pdf", "docx", "txt"],
                                                         key=f"file_{prefix}", label_visibility="collapsed"))
                st.caption("Text-based PDFs · 5 MB / 10 pages maximum")
    ask = st.checkbox("Allow optional questions when important evidence is missing", value=True, key="allow_questions")
    st.caption("Never mandatory. At most six questions in one round; you can skip any or all of them.")
    consent = st.checkbox("I agree to send these documents to Groq and will review suggested edits.", key="consent")
    if st.button("Find my fit ↗", type="primary", disabled=not consent, width="stretch"):
        if not api_key:
            st.error("Add a Groq API key in Settings, or try the sample demo.")
        else:
            try:
                docs = {}
                for prefix, (method, value) in values.items():
                    if method == "file":
                        if value is None:
                            raise InputError("Upload both documents or use pasted text.")
                        docs[prefix] = from_file(value.getvalue(), value.name, prefix)
                    else:
                        docs[prefix] = from_text(value, prefix=prefix)
                with st.spinner("Comparing your evidence with the role…"):
                    result = run_stage("analyze", docs["C"], docs["J"], allow_questions=ask)
                if result is not None:
                    st.session_state.update(cv=docs["C"], jd=docs["J"], analysis=result, answers=[],
                                            demo_mode=False, questions_done=not ask, stage="review")
                    st.rerun()
            except InputError as exc:
                st.error(str(exc))
    st.caption("Drive/website importing, scanned PDFs, and legacy DOC are deferred. Download as DOCX/PDF or paste the content.")
else:
    cv, jd, analysis = st.session_state.cv, st.session_state.jd, st.session_state.analysis
    score = score_analysis(analysis)
    st.caption(analysis.role.upper())
    st.subheader(score.recommendation)
    st.write(score.reason)
    columns = st.columns(3)
    columns[0].metric("Evidence match", f"{score.score:.1f} / 10")
    columns[1].metric("Requirements supported", f"{score.supported} / {score.total}")
    columns[2].metric("Readability flags", len(cv.warnings))
    st.caption(f"Eligibility: {score.eligibility}. Advisory evidence score—not an employer's ATS score or interview probability.")
    if stage == "review":
        tabs = st.tabs(["Your fit", "Document check", "Source preview"])
        with tabs[0]:
            st.write(analysis.summary)
            for req in analysis.requirements:
                with st.expander(f"{req.status.replace('_', ' ').title()} · {req.label}"):
                    st.write(req.reason)
                    st.caption(f"{req.importance.title()} · {'Explicit prerequisite' if req.hard_gate else 'Role requirement'}")
                    st.text(f"Job: {req.job_quote}")
                    for evidence in req.evidence:
                        st.text(f"{evidence.source_id}: {evidence.quote}")
                    if not req.evidence:
                        st.caption("No supporting candidate evidence found in supplied material.")
        with tabs[1]:
            for check in cv.checks:
                st.success(check)
            for warning in cv.warnings:
                st.warning(warning)
            st.caption("These checks do not emulate an employer's ATS.")
        with tabs[2]:
            st.caption("Check for missing content or scrambled reading order. Clear the workspace to replace incorrect inputs.")
            for label, doc in [("Resume", cv), ("Job description", jd)]:
                with st.expander(label, expanded=label == "Resume"):
                    st.code("\n".join(f"[{b.id}] {b.section}: {b.text}" for b in doc.blocks), language=None)
                    for warning in doc.warnings:
                        st.caption(warning)
        with st.expander("How the score works"):
            st.write("Required criteria weigh 3; preferred criteria weigh 1. Supported = 1, partial = 0.5, not evidenced/contradicted = 0. Score = 10 × earned weighted points ÷ total weight. A score of 7 suggests Apply only with no unresolved explicit prerequisite. These are prototype rules, not validated hiring thresholds.")
        questions = analysis.questions if not st.session_state.questions_done else []
        if questions:
            st.divider()
            heading("Optional clarification", f"{len(questions)} questions that could matter.",
                    "Answer only what you can, or skip this round. Unanswered items remain unknown.")
            if st.session_state.demo_mode:
                for question in questions:
                    st.write(question.question)
                if st.button("Use the sample SQL answer", type="primary"):
                    answers = demo.demo_answers()
                    result = validate_analysis(demo.clarified(), cv, jd, answers, analysis)
                    st.session_state.update(analysis=result, answers=answers, questions_done=True)
                    st.rerun()
            else:
                with st.form("clarifications"):
                    entered = [st.text_area(q.question, key=f"answer_{q.id}", help=q.why, max_chars=1000, height=85) for q in questions]
                    confirmed = st.checkbox("These answers accurately describe my own experience.")
                    submitted = st.form_submit_button("Update my assessment", type="primary")
                if submitted:
                    if not confirmed:
                        st.warning("Confirm the accuracy of your answers, or skip the questions.")
                    elif not any(a.strip() for a in entered):
                        st.warning("Add at least one answer or skip this round.")
                    elif not api_key:
                        st.error("Add your Groq key in Settings to continue.")
                    else:
                        answers = [Answer(id=f"A{i+1}", question=q.question, requirement_id=q.requirement_id, text=value.strip())
                                   for i, (q, value) in enumerate(zip(questions, entered)) if value.strip()]
                        with st.spinner("Reassessing with confirmed evidence…"):
                            result = run_stage("analyze", cv, jd, answers, analysis)
                        if result is not None:
                            st.session_state.update(analysis=result, answers=answers, questions_done=True)
                            st.rerun()
            if st.button("Skip questions and continue"):
                st.session_state.questions_done = True
                st.rerun()
        else:
            st.divider()
            if analysis.restructure:
                st.info("A full layout update is recommended: " + analysis.structure_reason)
            label = "Open saved improvements ↗" if st.session_state.get("edit_plan") else "Create targeted improvements ↗"
            if st.button(label, type="primary", width="stretch"):
                if st.session_state.get("edit_plan"):
                    plan = st.session_state.edit_plan
                elif st.session_state.demo_mode:
                    plan = validate_edits(demo.edits(), cv, st.session_state.answers, analysis)
                elif not api_key:
                    st.error("Add your Groq key in Settings to continue.")
                    plan = None
                else:
                    with st.spinner("Refining relevant sections using your evidence…"):
                        plan = run_stage("edit", cv, analysis, st.session_state.answers)
                if plan is not None:
                    st.session_state.update(edit_plan=plan, stage="edit")
                    st.rerun()
    else:
        plan = st.session_state.edit_plan
        heading("Your experience, clearer", "Small changes. A stronger explanation.",
                "Review each replacement against its evidence. Select only the changes you want.")
        blocks, accepted = {b.id: b for b in cv.blocks}, set()
        if not plan.edits:
            st.info("No targeted wording changes were recommended.")
        for i, edit in enumerate(plan.edits):
            with st.container(border=True):
                st.markdown(f"**{i+1}. {blocks[edit.block_id].section}**")
                before, after = st.columns(2)
                before.caption("CURRENT")
                before.write(blocks[edit.block_id].text)
                after.caption("SUGGESTED")
                after.write(edit.replacement)
                st.caption(edit.reason)
                with st.expander("Supporting evidence"):
                    for evidence in edit.evidence:
                        st.text(f"{evidence.source_id}: {evidence.quote}")
                if st.checkbox("Use this replacement", key=f"accept_{edit.block_id}"):
                    accepted.add(edit.block_id)
        for note in plan.notes:
            st.info(note)
        use_layout = st.checkbox("Use the proposed section layout") if plan.layout else False
        if plan.layout:
            st.caption("Proposed order: " + " → ".join(s.heading for s in plan.layout))
        rows = assemble(cv, plan, accepted, use_layout)
        final_text = as_text(rows)
        with st.expander("Your resume preview", expanded=True):
            st.code(final_text, language=None)
        st.caption("Only selected edits enter the export; other content is preserved. Formatting is rebuilt in a single column. Evidence links check provenance, not semantic truth—review before applying.")
        if st.button("Prepare downloads", type="primary"):
            st.session_state.export_signature = final_text
            st.session_state.export_docx = as_docx(rows)
        if st.session_state.get("export_signature") == final_text:
            txt, doc = st.columns(2)
            txt.download_button("Download TXT", final_text.encode(), "tailored_resume.txt", "text/plain", width="stretch")
            doc.download_button("Download DOCX", st.session_state.export_docx, "tailored_resume.docx",
                                "application/vnd.openxmlformats-officedocument.wordprocessingml.document", width="stretch")
        if st.button("Back to assessment"):
            st.session_state.stage = "review"
            st.rerun()
st.divider()
st.caption("APPLYWISE · Make a considered application. Keep your story yours.")
