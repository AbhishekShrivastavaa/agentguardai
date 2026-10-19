# AgentGuard AI Presentation Demo

## One sentence

AgentGuard AI is an inline security gateway for AI applications: requests pass through inspection and policy checks before reaching a model, while agent tool requests are checked before a runtime can execute them.

## Five minute walkthrough

1. **Introduce the problem.** AI agents can read context, call tools, and send data to external models. A normal chat demo does not show what is inspected or why an action is allowed.
2. **Show the dashboard.** Point out live backend health, the gateway map, recent events, risk trends, and the global activity map. Explain that the agent and integration topology is labeled demo inventory; it is not connected to real company telemetry.
3. **Run Prompt injection.** Open Playground → Attack simulator → Prompt injection. Show the five stages, the blocked verdict, the plain-language reason, and the matching audit event. Explain that a blocked prompt is stopped before the AI provider call.
4. **Run Sensitive data.** The preset uses synthetic contact and card values. Show the `REDACTED` verdict and explain that the model receives masked values while the surrounding text remains useful.
5. **Run Metadata SSRF and Runaway agent.** Show the private metadata destination and the recursion-depth limit. Explain that the simulator evaluates these requests but never executes a tool.
6. **Show Policy Studio.** Toggle one DLP detector or add a custom phrase rule, save it, then run the matching scenario again. Demonstrate that the policy is persisted by the API.
7. **Close with evidence.** Open Forensic audit vault, inspect the five-stage record and threat taxonomy, then export the filtered audit as JSON. Briefly show Analytics for risk, classifier, and OWASP-tagged event summaries.

## Suggested opening

“Our project places AgentGuard between an AI application and its model provider. It normalizes incoming text, detects instruction attacks, masks configured sensitive values, validates tool requests, applies policy, and records an explainable decision. The demo uses synthetic data and does not execute tools.”

## Suggested closing

“The prototype demonstrates how an inline inspection point can reduce common prompt, data-loss, and agent-tool risks. It is a student demonstration, not a guarantee that every attack can be detected or a production security certification. The next work is broader evaluation, persistent production storage, and stronger image and indirect-injection inspection.”

## Live model integration

The browser Playground uses the authenticated `/gateway/scan` demo endpoint. External OpenAI-compatible clients can use:

```text
Base URL: https://<agentguard-api-host>/v1
Endpoint: POST /chat/completions
Authorization: Bearer <AGENTGUARD_API_KEY>
```

The key belongs in the backend host's secret settings or the local backend `.env`, never in frontend code. The compatible proxy currently supports non-streaming text messages. It denies unregistered or unsanctioned tools, and it does not execute tools itself.

## Before presenting

- Start or verify the backend first, then load the frontend and register a demo account.
- Confirm the health indicator is online and the provider shows configured if you want to demonstrate live model responses.
- Run the four scan-only presets before the session so the event list and charts are populated.
- Keep the sensitive-data scenario synthetic. Do not enter real API keys, personal information, or customer prompts.
- Have the local app available as a backup if a hosted API or model provider is unavailable.
