# LangGraph Customer Support Agent

A multi-agent customer support system built with LangGraph, governed by CortexHub.

## What This Example Demonstrates

- **Multi-agent workflow**: Router → Support/Billing/Refund specialists
- **Tool governance**: CortexHub automatically intercepts all tool calls
- **PII detection**: Credit card numbers, emails, names are detected and reported
- **Policy enforcement**: Refund limits, access controls, data protection

## Quick Start

```bash
# Install dependencies (from repo root)
uv sync

# Set environment variables
cp .env.example .env
# Edit .env with your API keys

# Run the example
uv run python langgraph/main.py
```

## Minimal Refund + Approval Example

For a screenshot-friendly example that only shows refund + approval handling:

```bash
uv run python langgraph/simple_refund_approval.py
```

Note: Use integer types for money fields (smallest unit like cents) so
threshold policies evaluate cleanly on the raw field name.

## Environment Variables

| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | OpenAI API key for GPT-4 |
| `CORTEXHUB_API_KEY` | CortexHub API key (optional - observation mode works without) |

## Architecture

```
┌─────────────┐
│   Router    │ ← Classifies intent
└──────┬──────┘
       │
   ┌───┴───┬───────────┐
   ▼       ▼           ▼
┌──────┐ ┌──────┐ ┌────────┐
│Support│ │Billing│ │ Refund │ ← Specialized agents
└──────┘ └──────┘ └────────┘
   │       │           │
   └───────┴───────────┘
           │
    Tool Invocations
    (CortexHub governed)
```

## Tools

| Tool | Description | Governance |
|------|-------------|------------|
| `lookup_customer` | Find customer by ID | Logged |
| `update_customer_email` | Update email address | PII detected |
| `get_account_balance` | Check billing balance | Logged |
| `issue_refund` | Process refunds | Policy: max $500 |
| `create_support_ticket` | Create tickets | Logged |

## CortexHub Integration

This example uses the standard 2-line integration:

```python
import cortexhub
cortex = cortexhub.init("customer-support", cortexhub.Framework.LANGGRAPH)
```

That's it! CortexHub automatically:
- Intercepts all LangGraph tool invocations
- Detects PII in arguments and results
- Evaluates policies before execution
- Reports telemetry to your dashboard

Note: For approval workflows, configure `ToolNode` to surface tool errors
(e.g., `handle_tool_errors=False`) so `ApprovalRequiredError` can pause execution.

## Sample Policies

Create these policies in CortexHub dashboard:

**Refund Limit Policy:**
```
Tools matching: issue_refund
Condition: amount > 500
Effect: DENY with message "Refunds over $500 require manager approval"
```

**Customer Data Access:**
```
Tools matching: lookup_customer, update_customer*
Condition: role != "support" AND role != "billing"
Effect: DENY with message "Only support/billing can access customer data"
```

## Expected Output

```
============================================================
Customer: "I need a refund for order #12345, charged $299"
============================================================

[TOOL] lookup_customer(order_id="12345")
  → Customer: John Smith (john@email.com)
  ⚠️ PII: 1 EMAIL, 1 PERSON

[TOOL] issue_refund(order_id="12345", amount=299.00)
  → Refund processed: $299.00
  ✓ Policy: ALLOWED (under $500 limit)