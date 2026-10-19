# AgentGuard AI
### Enterprise GenAI Gateway Firewall & Agent Security Engine

AgentGuard AI is a mini project developed to demonstrate how a security gateway can protect Generative AI applications from potentially malicious prompts, sensitive information exposure, and unsafe AI interactions.

The application is designed to inspect requests before they reach an AI model, evaluate configurable security policies, record security events, and provide a dashboard for monitoring gateway activity.

**Project status:** Under development — 5th Semester Mini Project

---

## 1. Project Overview

Generative AI applications can face security risks such as prompt injection, sensitive information disclosure, and unauthorized tool usage.

AgentGuard AI introduces a security layer between the user and an AI model. This layer analyzes incoming prompts, evaluates security rules, and determines whether a request should be allowed, reviewed, or blocked.

The project aims to provide a simple, demonstrable AI security gateway with a web-based monitoring dashboard.

## 2. Objectives

- Build a web-based GenAI security gateway.
- Detect suspicious prompt patterns using a rule-based scanner.
- Identify configured sensitive information, such as email addresses.
- Evaluate requests using configurable security policies and risk scores.
- Record gateway decisions and security events.
- Provide a dashboard to monitor requests and threats.
- Integrate an AI model provider for approved requests.
- Deploy the application using Render without Docker.

## 3. Planned Features

### Security Engine
- Prompt-injection pattern detection.
- Sensitive information detection.
- Risk scoring and policy evaluation.
- Allow, review, and block decisions.
- AI output scanning.

### Web Dashboard
- Login and authentication.
- Request statistics.
- Security event monitoring.
- Prompt testing playground.
- Policy management.
- Analytics and settings.

### Gateway
- REST API for prompt scanning.
- AI provider integration.
- Request logging.
- API key management.
- Security decision reporting.

> These features are planned for the project. Their availability depends on implementation and testing.

## Agent Runtime Action Gateway

The Action Gateway evaluates an agent's requested action before an agent
runtime executes it. It supports shell commands, file reads and writes,
network destinations, secret access requests, and registered tools.

`POST /gateway/actions/evaluate` returns `ACTION_ALLOWED`, `APPROVAL_REQUIRED`,
or `BLOCKED` and writes an audit event. Pending requests can be reviewed with
`POST /gateway/actions/{event_id}/approve` or `/reject`.
These endpoints and the inventory API require a signed-in bearer token.

Current demo guardrails block destructive shell commands, direct reads of
credential paths, private or cloud metadata network destinations, prompt
injection in action requests, and unregistered tools. Writes, outbound network
requests, secret access, and tools awaiting review require approval.

These endpoints make a policy decision only; this demo does not execute the
requested action. A production agent integration must call this gateway before
execution and must only continue when the decision permits it. Approval records
are not execution grants to an executor that is not connected.

## 4. Technology Stack

| Component | Technology |
|---|---|
| Frontend | React, Vite, JavaScript |
| UI Styling | CSS / Tailwind CSS |
| Backend | Python, FastAPI |
| Database | PostgreSQL |
| Database ORM | SQLAlchemy |
| Database Migrations | Alembic |
| Authentication | JWT-based authentication |
| AI Integration | Compatible hosted LLM API |
| Deployment | Render |
| Version Control | Git and GitHub |

## 5. Project Architecture

```text
                User / AI Application
                         |
                         v
                React Frontend
                         |
                         v
                  FastAPI Backend
                         |
                         v
                AgentGuard Gateway
                         |
                 Security Scanner
                         |
                  Policy Engine
                         |
             +-----------+-----------+
             |           |           |
             v           v           v
           ALLOW       REVIEW      BLOCK
             |
             v
       AI Model Provider
             |
             v
        Output Scanner
             |
             v
      Response to User

       PostgreSQL Database
       Stores application data,
       policies and security events
```

## 6. Project Folder Structure

```text
agentguard-ai/
|
|-- frontend/
|   |-- public/
|   |-- src/
|   |   |-- assets/
|   |   |-- components/
|   |   |-- pages/
|   |   |-- services/
|   |   |-- context/
|   |   |-- App.jsx
|   |   |-- main.jsx
|   |   |-- index.css
|   |-- .env.example
|   |-- package.json
|   |-- vite.config.js
|
|-- backend/
|   |-- app/
|   |   |-- main.py
|   |   |-- config.py
|   |   |-- database.py
|   |   |-- models.py
|   |   |-- schemas.py
|   |   |-- auth.py
|   |   |-- gateway.py
|   |   |-- policies.py
|   |   |-- events.py
|   |   |-- dashboard.py
|   |   |-- ai_provider.py
|   |   |-- security_engine/
|   |       |-- scanner.py
|   |       |-- pii_detector.py
|   |       |-- injection_detector.py
|   |       |-- risk_scorer.py
|   |-- requirements.txt
|   |-- .env.example
|
|-- docs/
|   |-- architecture.md
|   |-- database-design.md
|   |-- testing.md
|
|-- .gitignore
|-- README.md
```

## Public Demo Deployment

The repository includes a GitHub Actions workflow for publishing the frontend
to GitHub Pages and a Render Blueprint for running the FastAPI backend.

1. Push the repository's main branch to GitHub.
2. In Render, create a new Blueprint from this repository and provide
   GROQ_API_KEY when prompted if live model responses are needed.
3. In the GitHub repository settings, enable Pages with GitHub Actions as the
   deployment source. The workflow publishes the frontend on each push.

The public frontend URL is
https://manav1234git.github.io/AgentGuard-AI/ and the configured API hostname is
https://agentguard-ai-manav1234-api.onrender.com. If Render assigns a different
hostname, update the VITE_API_URL in .github/workflows/deploy-pages.yml.

The free Render service uses its local SQLite database, which may reset when
the service restarts or redeploys. Use a managed persistent database for
durable user, inventory, policy, and event records.

## 7. Local Development Setup

### Prerequisites

Install the following:

- Python 3.11 or newer.
- Node.js and npm.
- PostgreSQL.
- Git.
- Visual Studio Code (recommended).

### Step 1: Clone the repository

```bash
git clone YOUR_GITHUB_REPOSITORY_URL
cd agentguard-ai
```

Replace `YOUR_GITHUB_REPOSITORY_URL` with your GitHub repository URL.

### Step 2: Set up the backend

Open a terminal in the backend directory.

Create a Python virtual environment:

```bash
cd backend
python -m venv .venv
```

Activate the environment.

**Windows PowerShell:**

```powershell
.\.venv\Scripts\Activate.ps1
```

**Linux/macOS:**

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create the backend `.env` file using `.env.example` as a template.

Configure the PostgreSQL connection and other required environment variables.

Start the backend:

```bash
uvicorn app.main:app --reload --port 8001
```

The local API should be available at:

- API: http://127.0.0.1:8001
- API documentation: http://127.0.0.1:8001/docs

### Step 3: Set up the frontend

Open another terminal:

```bash
cd frontend
npm install
```

Create a `.env` file based on `.env.example`.

Configure the backend URL:

```dotenv
VITE_API_URL=http://localhost:8001
```

Start the frontend:

```bash
npm run dev
```

Vite will display the local frontend URL, usually:

http://localhost:5173

### Step 4: Configure the database

Create a PostgreSQL database named `agentguard`.

Set the database connection string in the backend environment file:

```dotenv
DATABASE_URL=postgresql+psycopg://USERNAME:PASSWORD@localhost:5432/agentguard
```

Replace the username and password with your PostgreSQL credentials.

Ensure the backend database models and migrations are configured before using database-dependent endpoints.

---

## 8. Environment Variables

### Backend

Example `backend/.env.example`:

```dotenv
DATABASE_URL=postgresql+psycopg://USERNAME:PASSWORD@localhost:5432/agentguard

JWT_SECRET=replace-with-a-secure-random-secret

FRONTEND_URL=http://localhost:5173

AI_PROVIDER_API_KEY=
```

The actual variables required depend on the application's configuration.

### Frontend

Example `frontend/.env.example`:

```dotenv
VITE_API_URL=http://localhost:8001
```

Do not store passwords, private keys, JWT secrets, or AI provider secrets in frontend environment variables.

Do not commit actual `.env` files to GitHub.

---

## 9. Deployment on Render

AgentGuard AI is intended to be deployed using Render's standard services without Docker.

### PostgreSQL

1. Create a PostgreSQL database in Render.
2. Select an appropriate region.
3. Copy its internal database connection URL.
4. Set the URL as `DATABASE_URL` in the backend Web Service environment.

### Backend Web Service

Connect the GitHub repository to a new Render Web Service.

| Setting | Value |
|---|---|
| Root Directory | `backend` |
| Runtime | Python |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `uvicorn app.main:app --host 0.0.0.0:$PORT` |
| Health Check | `/api/v1/health` |

Set the required environment variables in Render.

### Frontend Static Site

Create a Render Static Site using the same GitHub repository.

| Setting | Value |
|---|---|
| Root Directory | `frontend` |
| Build Command | `npm install && npm run build` |
| Publish Directory | `dist` |

Set the frontend's production API URL:

```dotenv
VITE_API_URL=https://YOUR-BACKEND-NAME.onrender.com
```

Replace the placeholder with the deployed backend URL.

Configure backend CORS to allow the deployed frontend origin.

For additional information, see:

- https://render.com/docs/deploy-fastapi
- https://render.com/docs/static-sites
- https://render.com/docs/postgresql-creating-connecting

---

## 10. API Documentation

FastAPI provides interactive API documentation when the backend is running.

Local documentation:

http://127.0.0.1:8001/docs

Planned API endpoints include:

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/auth/register` | Register a user |
| POST | `/api/v1/auth/login` | Authenticate a user |
| GET | `/api/v1/dashboard/stats` | Retrieve dashboard statistics |
| POST | `/api/v1/gateway/scan` | Scan a prompt |
| POST | `/api/v1/gateway/chat` | Scan and forward a prompt to an AI provider |
| GET | `/api/v1/events` | Retrieve security events |
| GET | `/api/v1/policies` | Retrieve security policies |
| POST | `/api/v1/policies` | Create a security policy |

The endpoints should be considered planned until they are implemented and verified.

## 11. Security Considerations

- Store password hashes rather than plaintext passwords.
- Keep AI provider credentials on the backend.
- Validate user input and request sizes.
- Apply authentication and authorization to protected endpoints.
- Avoid storing sensitive prompt contents unnecessarily.
- Use HTTPS for deployed communication.
- Validate AI outputs before returning them.
- Do not execute AI-generated tool actions without appropriate authorization.

The project's rule-based scanner is intended for educational demonstration. It is not a substitute for a production security gateway, and it may miss sophisticated attacks or incorrectly flag benign prompts.

## 12. Testing

Testing should cover:

- Backend health and API responses.
- User authentication.
- Database connectivity.
- Safe prompt handling.
- Suspicious prompt detection.
- Sensitive information detection.
- Policy evaluation.
- Security event creation.
- Frontend-to-backend communication.
- Deployment environment configuration.

Backend tests can be run using:

```bash
pytest
```

Add test cases as each module is implemented.

## 13. Future Scope

- Advanced prompt-injection detection.
- Support for multiple AI model providers.
- Agent tool permission management.
- Human approval workflows.
- Improved analytics and audit trails.
- Policy versioning.
- Security testing against a broader set of GenAI attack scenarios.

## 14. Academic Project Information

**Project Name:** AgentGuard AI – Enterprise GenAI Gateway Firewall & Agent Security Engine

**Project Type:** Mini Project

**Academic Level:** Third Year, Fifth Semester

**Purpose:** Educational demonstration of security controls for Generative AI applications.

**Developed using:** React, FastAPI, PostgreSQL and Render.

---

## License

### Local prompt-risk classifier

The gateway combines explicit security rules with a locally trained Multinomial Naive Bayes text classifier. It uses word and adjacent-word features and adds no Python package requirements. Training examples in `backend/app/security_engine/training_data.jsonl` are synthetic demo examples; expand them with reviewed, representative prompts before relying on the classifier for production decisions.

From the `backend` directory, retrain and evaluate the model with:

```powershell
.\venv\Scripts\python.exe train_security_model.py
```

The script runs a deterministic stratified holdout, prints accuracy, precision, recall and confusion counts, then writes `app/security_engine/security_model.json`. The Playground inspection panel displays the model's attack likelihood. The classifier adds a block signal only above its confidence threshold; the explicit security rules remain active as a separate signal.

This project is developed for academic and educational purposes. Add an appropriate open-source license if you intend to distribute the source code publicly.
