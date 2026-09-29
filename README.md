# Applywise

A graduate application adviser using **CrewAI + Streamlit + Groq**. Find your fit,
clarify missing evidence only when needed, and accept targeted resume edits.

## Included

- Modern light interface with a green palette, progress steps, evidence cards,
  side-by-side edits, and download controls.
- PDF, DOCX, TXT, and pasted text for resume and job description.
- Relevance score out of 10, separate eligibility guidance, and readability checks.
- **Optional questions only when useful**: zero to six, one round. Users can
  disable questions before analysis or skip them afterwards. There is no quota.
- Two CrewAI agents: application analyst and resume editor.
- Up to five evidence-linked replacements. Every edit is unchecked by default.
- Complete section-layout proposal when substantial restructuring is justified.
- Copyable text and TXT/DOCX downloads generated without another model call.
- Fictional offline demo; never silently substituted for a live failure.
- Tests, GitHub CI, pinned dependencies, and deployment configuration.

## 1. Run locally

Use **Python 3.12** and run commands from the folder containing `streamlit_app.py`.

```bash
python -m venv .venv
```

Activate it:

```bash
# macOS / Linux
source .venv/bin/activate

# Windows PowerShell
.venv\Scripts\Activate.ps1
```

Then install and launch:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip check
python -m streamlit run streamlit_app.py
```

Click **Try the sample demo** to explore without a key.

## 2. Enable live analysis

Get a key from https://console.groq.com/keys. Enter it in the app's Settings, or
copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and edit it:

```toml
GROQ_API_KEY = "your-real-key"
GROQ_MODEL = "openai/gpt-oss-20b"
```

Never commit real keys. The real secrets file is ignored by Git. Environment
variables with these names are supported; a key entered in the UI overrides the
environment and Secrets for that session. `.env` files are not loaded. No OpenAI
key is needed: all inference goes to Groq.

## 3. Upload to GitHub

Create an empty repository in your account. Put the **contents** of this project
folder at its root, including `.streamlit` and `.github`. Do not upload virtual
environments, real resumes, secrets, or caches.

Alternatively, replace `YOUR_USERNAME` and run:

```bash
git init
git add .
git commit -m "Build Applywise application adviser"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/applywise.git
git push -u origin main
```

Use your own GitHub authentication. No repository has been created or pushed on
your behalf. The included GitHub workflow runs tests without API credentials.

## 4. Deploy with Streamlit Community Cloud

1. Push your repository and check that CI passes.
2. Open https://share.streamlit.io/ and create an app from that repository.
3. Select branch `main`, entrypoint `streamlit_app.py`.
4. Under Advanced settings, choose **Python 3.12** explicitly.
5. Paste the Groq configuration into **Secrets**, then deploy.
6. Test the offline demo, then a live run with fictional documents.

If deploying with your own paid key, restrict access or use the optional
`APP_PASSWORD = "a-long-private-password"` secret for a small demo. The shared
password is not production authentication or abuse protection. Another option is
to leave the server key unset and let visitors supply their own keys.

CrewAI has a substantial dependency tree; the first build may take longer than
a minimal Streamlit app. This project does not require custom system packages.

## Architecture and call budget

| Stage | Component | Groq requests |
|---|---|---:|
| Extract documents and basic checks | Python | 0 |
| Compare evidence, recommend, optionally ask questions | Analyst agent | 1 |
| Reassess confirmed answers, only if supplied | Same analyst | 0 or 1 |
| Rewrite selected blocks / propose complete layout | Editor agent | 0 or 1 |
| Calculate score, accept edits, preview, export | Python | 0 |

Normal complete path: **two requests**, or **three when answers are supplied**.
Editing is skipped when there are no targets and no restructuring is needed.
Questions do not require a separate generation call. Reruns, tabs, checkboxes,
exports, and reopening saved edits do not initiate requests. Explicit retries do.

Each role is a real CrewAI `Agent`, invoked with `Agent.kickoff()`. A custom
CrewAI `BaseLLM` adapter calls the official Groq SDK and enforces one HTTP request
per stage. Groq retries, delegation, tools, planning, persistent agent memory, and
automatic output-repair calls are disabled. The Streamlit state machine provides
the human checkpoint; a second Flow state machine is unnecessary for this MVP.

Strict JSON is enforced at the provider boundary and Pydantic validates locally.
Malformed or untraceable output fails closed without silently spending another
request. Sidebar metrics show attempted requests and provider-reported tokens;
failed requests may not report usage. Groq is the billing authority.

The analyst sees complete extracted documents. The editor sees selected blocks
and relevant evidence; complete layout work needs the entire resume. No RAG/vector
database is used for two short documents. RAG can be added later for a larger
personal evidence collection.

## Scoring and truthfulness

Required criteria weigh 3; preferred criteria weigh 1. Supported = 1, partial =
0.5, not evidenced/contradicted = 0. The score is `10 × weighted points / total
weight`. Weights and the requirement set remain fixed after clarification.

An explicit prerequisite mismatch takes priority over a high score. Unknown
prerequisites remain unknown. With no unresolved gate, a score of 7 suggests
Apply; otherwise Consider as a stretch. **These are prototype rules, not validated
hiring thresholds or interview probabilities.** This is not a real employer ATS.

Every requirement must quote the job description. Positive/partial/contradictory
candidate assessments require actual source quotes. Edits must cite candidate
evidence, target existing approved blocks, and avoid new unsupported numbers or
dates. Full layouts must contain every original block exactly once. There is no
claim that keyword changes create qualifications.

Source validation is **not semantic proof**: a model can still exaggerate a
qualitative claim or misinterpret evidence. Answers are candidate assertions,
not credential verification. Human review is required before accepting edits.

## Source files

| File | Purpose |
|---|---|
| `streamlit_app.py` | UI, consent, optional questions, acceptance, session state |
| `applywise/service.py` | CrewAI analyst and editor |
| `applywise/llm.py` | Groq adapter, schemas, error handling, call budget |
| `applywise/prompts.py` | Role instructions and factual constraints |
| `applywise/models.py` | Structured contracts |
| `applywise/documents.py` | File/text extraction and limits |
| `applywise/validation.py` | Evidence checks and deterministic scoring |
| `applywise/export.py` | Accepted patches and TXT/DOCX output |
| `applywise/ui.py`, `styles.css` | Presentation |
| `applywise/demo.py`, `examples/` | Fictional offline demo |
| `tests/` | Core, actual-agent/mock-provider, and Streamlit tests |
| `.github/workflows/ci.yml` | GitHub automated checks |
| `requirements.txt`, `constraints.txt` | Compatible dependency pins |

## Testing

```bash
python -m pip install -r requirements-dev.txt
python -m pip check
python -m ruff check .
python -m pytest -q
```

See `TESTING.md` for the actual verification result and limitations. The integration
tests run real CrewAI agents with a **mocked Groq transport**, so they verify
integration and request counts, not model quality. Live testing needs your API key.

## Boundaries

- English-oriented MVP; recognized section headings and prompts are English.
- Google Drive, arbitrary URLs, `.doc`, and OCR are deferred. Download/convert to
  DOCX or text-based PDF, or paste the content.
- Limits: 5 MB/file, 10 PDF pages, 24,000 extracted characters, 180 content lines,
  and 1,000 characters per answer. Account token limits can be lower than model
  context limits. Shorten input or wait if Groq rate-limits the request.
- DOCX headers, footers, and floating text boxes are omitted. PDF text order can
  be imperfect. Review Source preview and correct input before using the result.
- Readability checks are extraction/structure signals, not a complete layout or
  ATS test. Pasted text cannot reveal the original layout.
- Downloads are TXT and single-column DOCX; original graphics, typography, and
  pagination are not preserved. PDF export is not included.
- New answers can inform existing relevant blocks. The editor does not invent
  entire new experience sections or attach coursework to unrelated projects.
- Session-only storage means a server restart or session loss can lose work.
  Download the final result. Clearing the workspace does not erase files already
  downloaded or data retained by hosting/Groq infrastructure. Check their policies.
- No shared CV cache or application database. Agents have no filesystem, network,
  or code tools. Prompt injection is mitigated, not claimed solved.
- Before broader public use, add real authentication, per-user budgets, hardened
  file parsing, operational monitoring without CV content, and retention controls.

## Troubleshooting

| Issue | Action |
|---|---|
| Install conflicts | Use a fresh Python 3.12 environment with supplied requirements. |
| Invalid key | Check Settings or Secrets. An OpenAI key will not work. |
| Model unavailable | Check Groq's current catalog and project model permissions. |
| Rate limit | Wait, reduce input size, or check account quota. No automatic retry loop runs. |
| Validation failure | Inspect extracted text and retry explicitly. Rejected content is never applied. |
| Unreadable PDF | OCR externally, export DOCX, or paste text. |
| Changed edits after preparing downloads | Prepare downloads again so the file matches the new selections. |

## References verified September 29, 2026

CrewAI 1.15.22 and Streamlit 1.64.0 were verified against published releases.
Pydantic 2.12.5 is pinned because this CrewAI release requires `<2.13`. Compatible
versions take precedence over independently selecting the latest of everything.
The two offered Groq models were listed as production models supporting strict
structured output; model availability may change separately from Python packages.

- https://pypi.org/project/crewai/
- https://pypi.org/project/streamlit/
- https://docs.crewai.com/en/concepts/agents
- https://docs.crewai.com/en/learn/custom-llm
- https://docs.crewai.com/en/telemetry
- https://console.groq.com/docs/models
- https://console.groq.com/docs/structured-outputs
- https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy
- https://docs.streamlit.io/develop/api-reference/app-testing/st.testing.v1.apptest
