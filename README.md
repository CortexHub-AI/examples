# CortexHub Examples

Production-ready examples showing CortexHub governance for AI agentic frameworks.

These examples are intended for customer usage and install CortexHub from PyPI.

All examples share a **single uv project** so you install dependencies once.

## Supported Frameworks

| Framework | Example | Description |
|-----------|---------|-------------|
| [LangGraph](./langgraph/) | Customer Support Agent | Multi-agent workflow with router and specialists |
| [CrewAI](./crewai/) | Financial Operations Team | Multi-agent crew for financial transactions |
| [OpenAI Agents](./openai-agents/) | Research Assistant | Multi-turn research with web search |
| [Claude Agents](./claude-agents/) | DevOps Assistant | MCP tools with deployment workflows |
| [Safety Policies](./safety/) | Safety Controls | Policy-driven controls for sensitive tools |

## Domain Compliance Journeys (Single-Agent)

These are **single-agent, real-world scenarios** implemented across all four frameworks.
Run each scenario twice:
1) **Without policies** to generate recommendations
2) **After enabling policies** in the dashboard to see enforcement (allow/deny/approval)

| Domain | Folder | Scenario |
|--------|--------|----------|
| Healthcare | [healthcare](./healthcare/) | Patient intake + prescription |
| Finance | [finance](./finance/) | High-value refund |
| Customer Support | [customer-support](./customer-support/) | Subscription cancellation |

## Quick Start

From the repo root, pick any framework and run:

```bash
# Install dependencies (once)
uv sync

# Set up environment
cp .env.example .env
# Edit .env with your API keys (CortexHub API key is required)

# Run
uv run python langgraph/main.py
```

## What You'll See

Each example demonstrates:
- **2-line CortexHub integration** - Just import and init
- **Automatic tool interception** - All framework tools are governed
- **PII detection** - Emails, names, SSNs detected in real-time
- **Policy enforcement** - Block, allow, or escalate tool calls
- **Telemetry** - All activity logged to CortexHub dashboard

Example output:
```
============================================================
TASK: Process refund for order #12345
============================================================

[TOOL] lookup_customer(order_id="12345")
  → Customer: John Smith (john@email.com)
  ⚠️ PII: 1 EMAIL, 1 PERSON

[TOOL] issue_refund(order_id="12345", amount=299.00)
  → Refund processed: $299.00
  ✓ Policy: ALLOWED (under $500 limit)
```

## Requirements

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) - Fast Python package manager
- API keys for your chosen LLM provider (OpenAI, Anthropic)
- CortexHub API key (required for all examples)

## CortexHub Integration Pattern

Every example uses the same 2-line pattern:

```python
import cortexhub
cortex = cortexhub.init("agent-name", cortexhub.Framework.LANGGRAPH)
```

That's it! CortexHub automatically:
1. Patches the framework's tool infrastructure
2. Intercepts all tool invocations
3. Runs PII/secrets detection on arguments and results
4. Evaluates policies before/after execution
5. Reports telemetry to your dashboard

## Project Structure

```
cortexhub-examples/
├── langgraph/           # Framework example
├── crewai/              # Framework example
├── openai-agents/       # Framework example
├── claude-agents/       # Framework example
├── healthcare/          # Domain journey (all frameworks)
├── finance/             # Domain journey (all frameworks)
├── customer-support/    # Domain journey (all frameworks)
```

## Running All Examples

To run all examples sequentially:

```bash
make run-all
```

Or run individual examples:

```bash
make langgraph
make crewai
make openai-agents
make claude-agents
make safety
```

## Creating Your Own Agent

Use any example as a template:

```bash
# Copy an example
cp -r langgraph my-agent
cd my-agent

# Update pyproject.toml with your project name
# Update main.py with your agent logic

# Run
uv sync
uv run python main.py
```

## Links

- [CortexHub Documentation](https://docs.cortexhub.ai)
- [Dashboard](https://app.cortexhub.ai)
