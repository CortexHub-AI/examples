# Claude Agent SDK DevOps Assistant

A DevOps assistant built with Claude Agent SDK, governed by CortexHub.

## What This Example Demonstrates

- **MCP custom tools**: DevOps operations via `@tool` decorator
- **Built-in tool governance**: Bash, Read, Write via hooks
- **Approval workflows**: Production deployments require approval
- **Security scanning**: Automated vulnerability detection

## Quick Start

```bash
# Install dependencies (from repo root)
uv sync

# Set environment variables
cp .env.example .env
# Edit .env with your API keys

# Run the example
uv run python claude-agents/main.py
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `ANTHROPIC_API_KEY` | Anthropic API key for Claude |
| `CORTEXHUB_API_KEY` | CortexHub API key (optional - observation mode works without) |

## Tools

### Custom MCP Tools (DevOps)

| Tool | Description | Risk Level |
|------|-------------|------------|
| `check_security` | Scan for vulnerabilities | Low |
| `deploy_service` | Deploy to environment | High |
| `get_service_status` | Check service health | Low |
| `rollback_deployment` | Rollback to previous | High |

### Built-in Tools (Claude Agent SDK)

| Tool | Description | Governance |
|------|-------------|------------|
| `Bash` | Execute shell commands | PreToolUse hook |
| `Read` | Read files | PreToolUse hook |
| `Write` | Write files | PreToolUse hook |

## CortexHub Integration

This example uses the standard 2-line integration:

```python
import cortexhub
cortex = cortexhub.init("devops-assistant", cortexhub.Framework.CLAUDE_AGENTS)
```

### Custom Tools Governance

Custom MCP tools created with `@tool` are automatically wrapped by CortexHub:

```python
from claude_agent_sdk import tool

@tool("deploy_service", "Deploy a service", {...})
async def deploy_service(args):
    # CortexHub automatically intercepts this
    ...
```

### Built-in Tools Governance

Built-in tools are governed via PreToolUse/PostToolUse hooks:

```python
from cortexhub.adapters.claude_agents import ClaudeAgentsAdapter

adapter = ClaudeAgentsAdapter(cortex)
hooks = adapter.create_governance_hooks()

options = ClaudeAgentOptions(
    hooks=hooks,  # CortexHub governance
    allowed_tools=["Bash", "Read"],
)
```

## Approval Flow

If a policy requires approval, the example will:
- Print the approval details and decision endpoint
- Wait for the approval decision using your `CORTEXHUB_API_KEY`
- Re-run the task once after approval

## Sample Policies

**Production Deployment Policy:**
```
Tools matching: deploy_service
Condition: environment == "production"
Effect: ESCALATE to ops-lead for approval
```

**Dangerous Command Policy:**
```
Tools matching: Bash
Condition: command contains "rm -rf" OR command contains "sudo"
Effect: DENY with message "Dangerous commands blocked"
```

## Expected Output

```
============================================================
TASK: Deploy payment-service to staging, version 2.1.0
============================================================

[TOOL] get_service_status(service="payment-service")
  → Status: RUNNING, Health: HEALTHY
  ✓ Policy: ALLOWED

[TOOL] check_security(path="/app")
  → 2 issues found (1 high, 1 medium)
  ⚠️ Review recommended

[TOOL] deploy_service(service="payment-service", env="staging", version="2.1.0")
  → Deployment initiated: deploy-payment-service-staging-001
  ✓ Policy: ALLOWED (staging environment)

============================================================
TASK: Deploy payment-service to production, version 2.1.0
============================================================

[TOOL] deploy_service(service="payment-service", env="production", version="2.1.0")
  ⏸️ APPROVAL REQUIRED
     Request ID: req-abc123
     Reason: Production deployments require ops-lead approval
```