# Customer Support Example (Single-Agent)

This folder contains a **single-agent subscription cancellation scenario** implemented in all four supported frameworks.

## Flow (End-User Perspective)
1) Run once with **no policies** enabled in the CortexHub dashboard.  
   - You will see the cancellation execute and recommendations appear in the dashboard.
2) Enable the recommended policies in the dashboard.  
3) Run again to see **enforcement behavior** (allow/deny/approval) and improved compliance.

## Run Commands

```bash
uv run python customer-support/langgraph_example.py
uv run python customer-support/crewai_example.py
uv run python customer-support/openai_agents.py
uv run python customer-support/claude_agents.py
```

## Scenario
- Subscription cancellation (high-risk customer action).
- Contains customer PII to show guardrails and policy recommendations.
