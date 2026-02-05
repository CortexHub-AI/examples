# OpenAI Agents Research Assistant

A research assistant built with OpenAI Agents SDK, governed by CortexHub.

## What This Example Demonstrates

- **Multi-turn conversations**: Agent maintains context across queries
- **Tool governance**: Web search, code execution, file operations
- **PII detection**: URLs, emails, researcher names
- **Rate limiting**: Policies can limit expensive operations

## Quick Start

```bash
# Install dependencies (from repo root)
uv sync

# Set environment variables
cp .env.example .env
# Edit .env with your API keys

# Run the example
uv run python openai-agents/main.py
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | OpenAI API key for GPT-4 |
| `CORTEXHUB_API_KEY` | CortexHub API key (optional - observation mode works without) |

## The Agent

The research assistant can:
- Search the web for academic papers
- Fetch and summarize web content
- Store research findings
- Generate reports with citations

## Tools

| Tool | Description | Risk Level |
|------|-------------|------------|
| `search_papers` | Search academic databases | Low |
| `fetch_url` | Retrieve web page content | Low |
| `store_finding` | Save research notes | Low |
| `execute_analysis` | Run data analysis code | High |
| `generate_report` | Create formatted report | Medium |

## CortexHub Integration

This example uses the standard 2-line integration:

```python
import cortexhub
cortex = cortexhub.init("research-assistant", cortexhub.Framework.OPENAI_AGENTS)
```

CortexHub automatically:
- Intercepts all OpenAI Agents function tool calls
- Detects PII in arguments and results
- Enforces policies before tool execution
- Reports telemetry to your dashboard

## Approval Flow

If a policy requires approval, the example will:
- Print the approval details and decision endpoint
- Wait for the approval decision using your `CORTEXHUB_API_KEY`
- Re-run the query once after approval

## Sample Policies

**Code Execution Policy:**
```
Tools matching: execute_analysis
Condition: contains_dangerous_code == true
Effect: DENY with message "Potentially unsafe code blocked"
```

**Rate Limit Policy:**
```
Tools matching: search_papers, fetch_url
Condition: calls_per_minute > 10
Effect: ESCALATE with message "Rate limit exceeded, requires approval"
```

## Expected Output

```
============================================================
QUERY: Find recent papers on transformer architectures
============================================================

[TOOL] search_papers(query="transformer architectures", limit=5)
  → Found 5 papers
  ⚠️ PII: 5 PERSON (author names)

[TOOL] fetch_url(url="https://arxiv.org/abs/...")
  → Content retrieved (2500 chars)
  ⚠️ PII: URL detected

[TOOL] store_finding(title="Attention Is All You Need", ...)
  → Finding stored with ID: finding-001
  ✓ Policy: ALLOWED
```