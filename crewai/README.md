# CrewAI Financial Operations Team

A multi-agent financial operations team built with CrewAI, governed by CortexHub.

## What This Example Demonstrates

- **Multi-agent collaboration**: Analyst, Compliance, and Processor agents
- **Tool governance**: All financial tools are intercepted and policy-checked
- **PII detection**: Account numbers, SSNs, transaction data
- **Approval workflows**: High-value transfers require explicit approval

## Quick Start

```bash
# Install dependencies (from repo root)
uv sync

# Set environment variables
cp .env.example .env
# Edit .env with your API keys

# Run the example
uv run python crewai/main.py
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | OpenAI API key for GPT-4 |
| `CORTEXHUB_API_KEY` | CortexHub API key (optional - observation mode works without) |

## The Crew

```
┌─────────────────┐
│ Financial       │
│ Analyst         │ ← Reviews transactions, identifies patterns
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Compliance      │
│ Officer         │ ← Checks regulatory requirements
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Transaction     │
│ Processor       │ ← Executes approved transactions
└─────────────────┘
```

## Tools

| Tool | Description | Risk Level |
|------|-------------|------------|
| `lookup_account` | Find account details | Low |
| `check_transaction_history` | Get recent transactions | Low |
| `verify_compliance` | Run compliance checks | Medium |
| `initiate_transfer` | Start a money transfer | High |
| `approve_transfer` | Approve pending transfer | High |

## CortexHub Integration

This example uses the standard 2-line integration:

```python
import cortexhub
cortex = cortexhub.init("financial-ops", cortexhub.Framework.CREWAI)
```

CortexHub automatically:
- Wraps all CrewAI tool definitions
- Detects PII like account numbers and SSNs
- Enforces transfer limits via policies
- Requires approval for high-value transactions

## Approval Flow

If a policy requires approval, the example will:
- Print the approval details and decision endpoint
- Wait for the approval decision using your `CORTEXHUB_API_KEY`
- Re-run the transfer once after approval

## Sample Policies

**Transfer Limit Policy:**
```
Tools matching: initiate_transfer
Condition: amount > 10000
Effect: ESCALATE to manager for approval
```

**Compliance Check Required:**
```
Tools matching: approve_transfer
Condition: compliance_status != "passed"
Effect: DENY with message "Compliance check required"
```

## Expected Output

```
============================================================
TASK: Process wire transfer of $5,000 to account ACCT-7890
============================================================

[ANALYST] Reviewing transaction request...
  → lookup_account(account_id="ACCT-7890")
  ⚠️ PII: ACCOUNT_NUMBER detected

[COMPLIANCE] Running regulatory checks...
  → verify_compliance(amount=5000, destination="ACCT-7890")
  ✓ Compliance: PASSED

[PROCESSOR] Executing transfer...
  → initiate_transfer(amount=5000, to_account="ACCT-7890")
  ✓ Policy: ALLOWED (under $10,000 limit)
  → Transfer initiated: TXN-12345
```