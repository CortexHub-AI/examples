# Finance Example (Single-Agent)

This folder contains a **single-agent refund scenario** implemented in all four supported frameworks.

## Flow (End-User Perspective)
1) Run once with **no policies** enabled in the CortexHub dashboard.  
   - You will see the refund execute and recommendations appear in the dashboard.
2) Enable the recommended policies in the dashboard.  
3) Run again to see **enforcement behavior** (allow/deny/approval) and improved compliance.

## Run Commands

```bash
uv run python finance/langgraph_example.py
uv run python finance/crewai.py
uv run python finance/openai_agents.py
uv run python finance/claude_agents.py
```

## Scenario
- High-value refund request (`$750`) to trigger governance recommendations.
- Contains PII (customer name/email) so you can see guardrails in action.
