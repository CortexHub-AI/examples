"""OpenAI Agents Research Assistant with CortexHub

A research assistant demonstrating:
- Multi-turn conversations with tool use
- Web search and content fetching
- Research note storage
- Report generation
- Tool tracing via CortexHub

Run:
    uv run python main.py
"""

import os
import asyncio
import json
import time
import urllib.request
from dotenv import load_dotenv

load_dotenv(override=True)

# =============================================================================
# CORTEXHUB: 2-line integration
# =============================================================================
import cortexhub
cortex = cortexhub.init("research-assistant", cortexhub.Framework.OPENAI_AGENTS)

# =============================================================================
# OpenAI Agents imports (after CortexHub init to enable auto-patching)
# =============================================================================
from agents import Agent, Runner, function_tool


# =============================================================================
# Research Tools
# =============================================================================

@function_tool
def search_papers(query: str, limit: int = 5, year_from: int | None = None) -> dict:
    """Search academic databases for research papers.
    
    Args:
        query: Search query (keywords, paper title, author name)
        limit: Maximum number of results (default: 5)
        year_from: Only include papers from this year onwards
    
    Returns:
        List of matching papers with title, authors, abstract, and URL
    """
    # Simulated search results
    papers = [
        {
            "title": "Attention Is All You Need",
            "authors": ["Ashish Vaswani", "Noam Shazeer", "Niki Parmar"],
            "year": 2017,
            "abstract": "The dominant sequence transduction models are based on complex recurrent or convolutional neural networks...",
            "url": "https://arxiv.org/abs/1706.03762",
            "citations": 85000,
        },
        {
            "title": "BERT: Pre-training of Deep Bidirectional Transformers",
            "authors": ["Jacob Devlin", "Ming-Wei Chang", "Kenton Lee"],
            "year": 2018,
            "abstract": "We introduce a new language representation model called BERT...",
            "url": "https://arxiv.org/abs/1810.04805",
            "citations": 75000,
        },
        {
            "title": "Language Models are Few-Shot Learners",
            "authors": ["Tom Brown", "Benjamin Mann", "Nick Ryder"],
            "year": 2020,
            "abstract": "Recent work has demonstrated substantial gains on many NLP tasks...",
            "url": "https://arxiv.org/abs/2005.14165",
            "citations": 45000,
        },
        {
            "title": "Training language models to follow instructions with human feedback",
            "authors": ["Long Ouyang", "Jeff Wu", "Xu Jiang"],
            "year": 2022,
            "abstract": "Making language models bigger does not inherently make them better...",
            "url": "https://arxiv.org/abs/2203.02155",
            "citations": 12000,
        },
        {
            "title": "Constitutional AI: Harmlessness from AI Feedback",
            "authors": ["Yuntao Bai", "Saurav Kadavath", "Sandipan Kundu"],
            "year": 2022,
            "abstract": "As AI systems become more capable, we would like to enlist their help...",
            "url": "https://arxiv.org/abs/2212.08073",
            "citations": 3500,
        },
    ]
    
    # Filter by year if specified
    if year_from:
        papers = [p for p in papers if p["year"] >= year_from]
    
    return {
        "query": query,
        "total_results": len(papers[:limit]),
        "papers": papers[:limit],
    }


@function_tool
def fetch_url(url: str, extract_text: bool = True) -> dict:
    """Fetch content from a URL.
    
    Args:
        url: The URL to fetch
        extract_text: If True, extract main text content (default: True)
    
    Returns:
        Page content including title, text, and metadata
    """
    # Simulated fetch - in real implementation would actually fetch
    return {
        "url": url,
        "status": "success",
        "title": "Research Paper Abstract",
        "content": f"[Simulated content from {url}]\n\n"
                   "This paper presents a novel approach to natural language processing "
                   "using transformer architectures. We demonstrate state-of-the-art results "
                   "on multiple benchmarks including GLUE, SuperGLUE, and SQuAD.",
        "content_length": 2500,
        "fetched_at": "2026-01-24T12:00:00Z",
    }


@function_tool
def store_finding(
    title: str,
    content: str,
    source_url: str | None = None,
    tags: list[str] | None = None,
    notes: str | None = None
) -> dict:
    """Store a research finding or note.
    
    Args:
        title: Title of the finding
        content: Main content/summary
        source_url: Optional URL of the source
        tags: Optional list of tags for categorization
        notes: Optional additional notes
    
    Returns:
        Confirmation with finding ID
    """
    import random
    finding_id = f"finding-{random.randint(1000, 9999)}"
    
    return {
        "success": True,
        "finding_id": finding_id,
        "title": title,
        "tags": tags or [],
        "message": f"Finding '{title}' stored with ID {finding_id}",
    }


@function_tool
def execute_analysis(code: str, data_source: str | None = None) -> dict:
    """Execute data analysis code (Python).
    
    Args:
        code: Python code to execute
        data_source: Optional data source identifier
    
    Returns:
        Execution results
    
    Note: This tool may require approval for security reasons.
    """
    # Simulated code execution - in real implementation would use sandbox
    return {
        "success": True,
        "output": "[Simulated analysis output]\n"
                  "Analysis complete:\n"
                  "- Total records: 1000\n"
                  "- Mean score: 0.85\n"
                  "- Std deviation: 0.12",
        "execution_time_ms": 150,
        "warning": "Code execution is sandboxed for security",
    }


@function_tool
def generate_report(
    title: str,
    sections: list[str],
    include_citations: bool = True,
    format: str = "markdown"
) -> dict:
    """Generate a formatted research report.
    
    Args:
        title: Report title
        sections: List of section titles to include
        include_citations: Whether to include citations (default: True)
        format: Output format - "markdown" or "html" (default: markdown)
    
    Returns:
        Generated report content
    """
    report = f"# {title}\n\n"
    
    for i, section in enumerate(sections, 1):
        report += f"## {i}. {section}\n\n"
        report += f"[Content for {section} section]\n\n"
    
    if include_citations:
        report += "## References\n\n"
        report += "1. Vaswani et al. (2017). Attention Is All You Need.\n"
        report += "2. Devlin et al. (2018). BERT: Pre-training of Deep Bidirectional Transformers.\n"
    
    return {
        "success": True,
        "title": title,
        "format": format,
        "content": report,
        "word_count": len(report.split()),
    }


@function_tool
def send_report(recipient: str, report_id: str, subject: str) -> dict:
    """Send a generated report to a recipient.
    
    Args:
        recipient: Email address of the recipient
        report_id: ID of the report to send
        subject: Email subject line
    
    Returns:
        Send confirmation
    """
    return {
        "success": True,
        "recipient": recipient,
        "report_id": report_id,
        "subject": subject,
        "message": f"Report sent to {recipient}",
    }


# =============================================================================
# Agent Definition
# =============================================================================

research_agent = Agent(
    name="ResearchAssistant",
    instructions="""You are a helpful research assistant specializing in AI and machine learning.

Your capabilities:
- Search for academic papers on any topic
- Fetch and summarize web content
- Store research findings for later reference
- Generate formatted research reports

Best practices:
1. Always search for papers before making claims about research
2. Store important findings so you can reference them later
3. Include citations when generating reports
4. Be thorough but concise in your summaries

When asked about a topic:
1. First search for relevant papers
2. Fetch detailed content if needed
3. Store key findings
4. Summarize for the user""",
    model="gpt-4o-mini",
    tools=[
        search_papers,
        fetch_url,
        store_finding,
        execute_analysis,
        generate_report,
        send_report,
    ],
)


# =============================================================================
# Main
# =============================================================================

def _get_api_url() -> str:
    return os.getenv("CORTEXHUB_API_URL") or getattr(cortex, "api_url", "")


def _wait_for_approval(
    approval_id: str,
    api_url: str,
    api_key: str,
) -> tuple[str | None, dict | None]:
    if not approval_id:
        print("\nNo approval_id provided; cannot poll for decision.")
        return None, None

    url = f"{api_url.rstrip('/')}/v1/approvals/{approval_id}"
    headers = {"X-API-Key": api_key}
    print(f"\nWaiting for approval decision at {url}...")
    while True:
        req = urllib.request.Request(url, headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        status = data.get("status")
        if status and status.lower() != "pending":
            decision = data.get("decision")
            print(f"\n✅ Approval resolved: {status}")
            if decision:
                print(f"   Actor: {decision.get('actor')}")
                print(f"   Reason: {decision.get('reason')}")
            return status.lower(), decision
        time.sleep(3)


async def run_research_query(query: str, *, max_retries: int = 1):
    """Run a research query through the agent."""
    
    print("\n" + "=" * 60)
    print(f"QUERY: {query}")
    print("=" * 60)

    attempts = 0
    while True:
        try:
            result = await Runner.run(
                research_agent,
                query,
            )
            
            # Print the final response
            print(f"\n[RESPONSE]")
            print(result.final_output)
            break
            
        except cortexhub.PolicyViolationError as e:
            print(f"\n❌ BLOCKED BY CORTEXHUB: {e}")
            break
        except cortexhub.ApprovalRequiredError as e:
            print(f"\n⏸️  APPROVAL REQUIRED")
            print(f"   Approval ID: {e.approval_id}")
            print(f"   Tool: {e.tool_name}")
            print(f"   Reason: {e.reason}")
            print(f"   Expires: {e.expires_at}")
            print(f"\n   Decision endpoint: {e.decision_endpoint}")
            print(f"   Configure a webhook to receive approval.decisioned event")

            api_key = os.getenv("CORTEXHUB_API_KEY", "")
            api_url = _get_api_url()
            if not api_key or not e.approval_id or not api_url:
                break

            status, _decision = _wait_for_approval(e.approval_id, api_url, api_key)
            if status == "approved":
                attempts += 1
                if attempts <= max_retries:
                    print("\nRe-running the query after approval...")
                    continue
                print("\nApproval received, but max retries reached. Re-run to continue.")
                break
            if status in {"denied", "expired"}:
                print(f"\nApproval {status}. Skipping this query.")
                break
            break


async def main():
    """Run example research scenarios."""
    
    print("\n" + "=" * 60)
    print("OpenAI Agents Research Assistant")
    print("with CortexHub")
    print("=" * 60)
    
    queries = [
        "Find recent papers on transformer architectures and summarize the key innovations.",
        "Store a finding about the importance of attention mechanisms in NLP.",
        "Generate a brief report on 'The Evolution of Language Models' with sections on Transformers, BERT, and GPT.",
    ]
    
    for query in queries:
        await run_research_query(query)
        print()
    
    print("\n" + "=" * 60)
    print("Session Complete")
    print("=" * 60)
    print("\nCheck your CortexHub dashboard to see:")
    print("- All tool invocations logged")
    print("- PII detected (author names, URLs, emails)")
    print("- Telemetry recorded")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
