from pathlib import Path
from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parents[1] / "streamlit_app.py"


def click(app, label):
    next(b for b in app.button if b.label == label).click().run()
    assert not app.exception


def test_demo_export(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("APP_PASSWORD", raising=False)
    app = AppTest.from_file(str(APP), default_timeout=20).run()
    assert not app.exception
    click(app, "Try the sample demo ↗")
    assert app.metric[0].value == "5.8 / 10"
    click(app, "Use the sample SQL answer")
    assert app.metric[0].value == "8.1 / 10"
    click(app, "Create targeted improvements ↗")
    app.checkbox(key="accept_C5").check().run()
    click(app, "Prepare downloads")
    assert app.session_state["export_docx"].startswith(b"PK")
    assert "Used Python and pandas" in app.session_state["export_signature"]
    click(app, "Back to assessment")
    click(app, "Open saved improvements ↗")
    click(app, "Clear workspace")
    assert not app.metric


def test_optional_question_skip():
    app = AppTest.from_file(str(APP), default_timeout=20).run()
    click(app, "Try the sample demo ↗")
    click(app, "Skip questions and continue")
    click(app, "Create targeted improvements ↗")
    app.run()
    assert not app.exception
    assert "usage" not in app.session_state


def test_missing_live_key(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    app = AppTest.from_file(str(APP), default_timeout=20).run()
    app.checkbox(key="consent").check().run()
    click(app, "Find my fit ↗")
    assert any("API key" in e.value for e in app.error)


def test_password(monkeypatch):
    monkeypatch.setenv("APP_PASSWORD", "sample-test-password")
    app = AppTest.from_file(str(APP), default_timeout=20).run()
    app.text_input[0].input("wrong")
    click(app, "Open workspace")
    assert app.error
    app.text_input[0].input("sample-test-password")
    click(app, "Open workspace")
    assert any(b.label == "Try the sample demo ↗" for b in app.button)


def test_live_rerun_does_not_spend_again(monkeypatch):
    from applywise import demo
    from applywise.service import ResumeService
    calls = []

    def analyze(self, cv, jd, **kwargs):
        calls.append("analysis")
        result = demo.analysis()
        if not kwargs.get("allow_questions", True):
            result.questions = []
        return result

    def edit(self, cv, analysis, answers):
        calls.append("edit")
        return demo.edits()

    monkeypatch.setattr(ResumeService, "analyze", analyze)
    monkeypatch.setattr(ResumeService, "edit", edit)
    monkeypatch.setenv("GROQ_API_KEY", "test-only-fake")
    app = AppTest.from_file(str(APP), default_timeout=20).run()
    app.text_area(key="text_C").input((demo.ROOT / "examples/resume.txt").read_text())
    app.text_area(key="text_J").input((demo.ROOT / "examples/job.txt").read_text())
    app.checkbox(key="allow_questions").uncheck()
    app.checkbox(key="consent").check().run()
    click(app, "Find my fit ↗")
    assert not any(b.label == "Skip questions and continue" for b in app.button)
    app.run()
    click(app, "Create targeted improvements ↗")
    app.checkbox(key="accept_C3").check().run()
    click(app, "Prepare downloads")
    click(app, "Back to assessment")
    click(app, "Open saved improvements ↗")
    assert calls == ["analysis", "edit"]
