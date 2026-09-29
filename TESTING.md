# Verification report — September 29, 2026

The delivered source was tested on Python 3.12.14 / Linux after reconstruction.

## Passed

- **28 tests passed in 6.65 seconds.**
- Dependency check: 152 installed packages, all compatible.
- Ruff static checks and Python compilation passed.
- Real CrewAI agents executed with a mocked Groq transport. Initial analysis,
  optional reassessment, and editing each used one provider request.
- Optional questions: zero questions is valid; the pre-analysis switch suppresses
  them; users can skip the round; six is the maximum; no second question round.
- Streamlit AppTest covered the sample journey, missing key, password gate,
  question skipping/disabling, accepted edits, export, resetting, and reopening
  saved results without another inference request.
- Core checks covered scoring, fixed criteria after answers, evidence references,
  unsupported numbers, duplicate edits, full-layout content preservation, DOCX
  extraction ordering, selected-edit export, invalid text, and scanned PDF rejection.
- Exported DOCX bytes were reopened and checked for accepted content.

The run emitted 38 deprecation warnings from CrewAI internals; no tests failed.
Retest before changing framework pins.

## Not verified

- Live Groq inference: no user key was supplied. Actual model quality, quota,
  access permissions, latency and charges require a live smoke test.
- GitHub CI execution and Streamlit Cloud hosting: files are provided but no
  repository was connected or deployment created.
- Browser visual review: screenshot tooling was unavailable in this session.
  AppTest checks behavior and exceptions, not pixel layout or accessibility.
- Employer-specific ATS behavior or hiring outcomes.

## Environment note

The build environment initially produced eight truncated dependency files.
They were restored from independently downloaded wheels only after their SHA-256
matched the wheel RECORD entries. All installed hashed files were rechecked with
zero mismatches before the passing test run. No integrity check was disabled.
This repair is specific to this execution environment, not application code.

## Your final deployment smoke test

1. Install in a fresh Python 3.12 environment; run `python -m pip check`.
2. Install `requirements-dev.txt` and run `python -m pytest -q`.
3. Explore the sample demo on desktop and mobile widths.
4. Configure your Groq key in Settings or deployment Secrets, never GitHub.
5. Analyze fictional text with questions disabled, then try a case with a useful
   clarification. Confirm two requests without answers or three with answers.
6. Accept one edit, prepare downloads, and reopen the DOCX.
7. Repeat the demo and live smoke test after deployment.
