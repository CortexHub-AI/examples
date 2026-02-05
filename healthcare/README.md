# Healthcare Example (Single-Agent)

This folder contains a **single-agent patient intake scenario** implemented in all four supported frameworks.

## Flow (End-User Perspective)
1) Run once with **no policies** enabled in the CortexHub dashboard.  
   - You will see the prescription execute and recommendations appear in the dashboard.
2) Enable the recommended policies in the dashboard.  
3) Run again to see **enforcement behavior** (allow/deny/approval) and improved compliance.

## Run Commands

```bash
uv run python healthcare/langgraph_example.py
uv run python healthcare/crewai.py
uv run python healthcare/openai_agents.py
uv run python healthcare/claude_agents.py
```

## Scenario
- Patient intake + controlled medication prescription.
- Contains PHI/PII to show guardrails and policy recommendations.
