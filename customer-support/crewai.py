"""Customer support agent (CrewAI) with CortexHub.

Single-run example for governance before/after policies.
Run:
    uv run python customer-support/crewai.py
"""

import os
import time
import json
import urllib.request

from dotenv import load_dotenv

load_dotenv()

# -----------------------------------------------------------------------------
# CortexHub: 2-line integration
# -----------------------------------------------------------------------------
import cortexhub

cortex = cortexhub.init("customer-support-crewai", cortexhub.Framework.CREWAI, privacy=False)

# -----------------------------------------------------------------------------
# CrewAI imports (after CortexHub init)
# -----------------------------------------------------------------------------
from crewai import Agent, Task, Crew, Process
from crewai.tools import tool


@tool
def lookup_customer(customer_id: str) -> dict:
    """Look up customer information by ID."""
    return {
        "id": customer_id,
        "name": "Jamie Lee",
        "email": "jamie.lee@example.com",
        "status": "active",
        "plan": "premium",
    }


@tool
def cancel_subscription(customer_id: str, reason: str, immediate: bool = False) -> dict:
    """Cancel a customer's subscription."""
    return {
        "success": True,
        "customer_id": customer_id,
        "reason": reason,
        "effective": "immediately" if immediate else "end_of_billing_period",
        "message": f"Cancellation scheduled for {customer_id}",
    }


def _wait_for_approval(approval_id: str) -> str | None:
    if not approval_id:
        return None
    api_key = os.getenv("CORTEXHUB_API_KEY", "")
    url = f"{cortex.api_url.rstrip('/')}/v1/approvals/{approval_id}"
    headers = {"X-API-Key": api_key}
    while True:
        req = urllib.request.Request(url, headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        status = data.get("status")
        if status and status.lower() != "pending":
            return status.lower()
        time.sleep(2)


def run_demo() -> None:
    agent = Agent(
        role="Customer Support Agent",
        goal="Handle customer requests safely and accurately.",
        backstory="You handle subscription changes and must follow governance rules.",
        tools=[lookup_customer, cancel_subscription],
        verbose=True,
    )

    task = Task(
        description=(
            "Look up customer cust_123, then cancel the subscription because they are moving. "
            "Customer email: jamie.lee@example.com."
        ),
        expected_output="Cancellation confirmation or a governance block/approval.",
        agent=agent,
    )

    crew = Crew(
        agents=[agent],
        tasks=[task],
        process=Process.sequential,
        verbose=True,
    )

    try:
        result = crew.kickoff()
        print("\n" + "=" * 60)
        print("FINAL RESULT")
        print("=" * 60)
        print(result)
    except cortexhub.ApprovalRequiredError as e:
        print("\nAPPROVAL REQUIRED")
        print(f"- approval_id: {e.approval_id}")
        print(f"- tool: {e.tool_name}")
        print(f"- reason: {e.reason}")
        status = _wait_for_approval(e.approval_id)
        print(f"\nApproval status: {status}")
    except cortexhub.PolicyViolationError as e:
        print(f"\nBLOCKED BY CORTEXHUB: {e}")


def main() -> None:
    print("\n" + "=" * 60)
    print("Customer Support Agent (CrewAI)")
    print("Run once without policies, then enable recommendations and rerun.")
    print("=" * 60)
    run_demo()


if __name__ == "__main__":
    main()
