# AgentGuard AI

AgentGuard AI is an academic demonstration of an inline security gateway for AI applications and tool-using agents. It inspects requests before they reach a configured model provider, applies policy, masks configured sensitive values, screens model output, and records an explainable audit event.

The current prototype demonstrates a focused set of controls using synthetic data. It is not a guarantee against every attack and is not a production security certification.

## Inspection pipeline

1. **Normalize:** compatibility-normalize Unicode, remove invisible formatting characters, and map a small set of common Greek/Cyrillic lookalikes.
2. **Inspect instructions:** apply curated injection and system-override rules with a local Naive Bayes model as a supporting signal.
3. **Apply DLP:** detect configured emails, phones, payment-card numbers, cloud/API tokens, JWTs and private-key blocks; mask matching text before forwarding.
4. **Check agent tools:** validate inventory, the Policy Studio allow-list, dangerous command patterns, private/metadata URLs, sensitive arguments, and recursion depth. Unknown tools fail closed.
5. **Enforce policy and audit:** return an explainable allow, redact, flag, or block result and store a redacted event with pipeline evidence and OWASP LLM tags.

The gateway also scans model output for sensitive values. Tool decisions do not execute tools: the agent runtime must call the gateway before execution and must enforce its decision.

## Product areas

- **Dashboard:** gateway health, editable demo-agent inventory, global activity map, recent events and threat posture.
- **Playground:** real-model chat through the authenticated `/gateway/scan` endpoint plus four synthetic scan-only attack scenarios.
- **Policy Studio:** risk threshold, DLP detector toggles, registered-tool allow-list, and exact-phrase block/flag rules.
- **Agent Action Gateway:** evaluate shell, file, network, secret and tool intents; review approval-required events.
- **Threat Analytics:** risk and classifier history, detection reasons, OWASP-tagged categories, CSV report.
- **Forensic Audit Vault:** searchable event records with stage evidence and filtered JSON export.
- **OpenAI-compatible proxy:** non-streaming text chat completions at `POST /v1/chat/completions`.

Demo inventory on the dashboard is explicitly labeled as sample data. The global map is illustrative and does not represent request geolocation.

## Local setup

Prerequisites: Python 3.11+, Node.js 20+, and npm.

### Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Set `JWT_SECRET_KEY` to a long random value. Add `GROQ_API_KEY` only if you want live model responses. Set `AGENTGUARD_API_KEY` if you plan to call the OpenAI-compatible proxy. Keep these backend secrets out of the frontend and Git.

```powershell
uvicorn app.main:app --reload --port 8001
```

SQLite is the default database; its file is created by the app in the backend directory. The API docs are at `http://127.0.0.1:8001/docs`.

### Frontend

In another terminal:

```powershell
cd frontend
npm ci
Copy-Item .env.example .env
npm run dev
```

The local frontend uses `VITE_API_URL=http://127.0.0.1:8001`. Register a demo account in the app to access the dashboard and authenticated policy controls.

## OpenAI-compatible gateway

Point a compatible client at the AgentGuard API host, with the backend-only gateway key:

```python
from openai import OpenAI

client = OpenAI(
    base_url="https://<agentguard-api-host>/v1",
    api_key="<AGENTGUARD_API_KEY>",
)
response = client.chat.completions.create(
    model="openai/gpt-oss-120b",
    messages=[{"role": "user", "content": "Explain zero-trust AI gateways."}],
)
```

The endpoint supports non-streaming text messages and registered tool schemas. Streaming and multimodal image inspection are not implemented. Tools must be present in inventory and explicitly sanctioned or allow-listed; returned tool calls are checked before the gateway returns them. The gateway itself never executes a tool.

## Demo runbook

Follow [docs/PRESENTATION_DEMO.md](docs/PRESENTATION_DEMO.md) for a five-minute presentation flow. The attack presets are scan-only and use synthetic values; they do not call the model or execute tools.

## Deployment

The GitHub Actions workflow builds the frontend for the repository path `/agentguardai/` and publishes it to GitHub Pages. Enable **Settings → Pages → Build and deployment → GitHub Actions** in the repository, then rerun the latest workflow.

The Render Blueprint in `render.yaml` defines the FastAPI service, generated JWT and gateway API secrets, CORS origin, and a `GROQ_API_KEY` secret input. Create the Blueprint from the repository and enter the Groq key through Render's secret settings; never commit or paste it into frontend configuration. The frontend deployment already points at the configured Render hostname. If the API host changes, update `VITE_API_URL` in `.github/workflows/deploy-pages.yml` and redeploy Pages.

The Blueprint uses SQLite on the free service plan, so user, policy, inventory and event data may reset when the instance restarts or redeploys. Use a persistent managed database before relying on durable records.

## Scope and limits

- Security checks combine curated patterns, a small local text classifier, configurable DLP and explicit tool policies. They cannot detect every semantic, indirect, encoded or future attack.
- Unicode handling covers compatibility forms and a selected set of lookalikes; it is not a complete homoglyph defense.
- Hostname checks resolve DNS at decision time. Any real tool executor must pin the approved destination address and re-check redirects to limit DNS rebinding and redirect-based SSRF.
- Text-only proxy requests are inspected. Image payloads and streaming responses fail closed or are rejected rather than inspected.
- The demo should use synthetic prompts, test accounts, and non-sensitive data only.

## Repository

[AbhishekShrivastavaa/agentguardai](https://github.com/AbhishekShrivastavaa/agentguardai)
