"""Finance refund agent (CrewAI) with CortexHub.

Single-run example for governance before/after policies.
Run:
    uv run python finance/crewai_example.py
"""

import os
import time
import json
import urllib.request
from decimal import Decimal, InvalidOperation

from dotenv import load_dotenv

load_dotenv(override=True)

# -----------------------------------------------------------------------------
# CortexHub: 2-line integration
# -----------------------------------------------------------------------------
import cortexhub

cortex = cortexhub.init("finance-refund-crewai", cortexhub.Framework.CREWAI, privacy=False)

# -----------------------------------------------------------------------------
# CrewAI imports (after CortexHub init)
# -----------------------------------------------------------------------------
from crewai import Agent, Task, Crew, Process
from crewai.agents.parser import OutputParserException
from crewai.tools import tool


@tool
def issue_refund(order_id: str, amount: int, reason: str) -> dict:
    """Issue a refund for an order."""
    try:
        decimal_amount = Decimal(str(amount))
    except InvalidOperation:
        return {"success": False, "error": f"Invalid amount: {amount}"}
    quantized = decimal_amount.quantize(Decimal("0.01"))
    amount_str = f"{quantized:.2f}"
    return {
        "success": True,
        "order_id": order_id,
        "amount": amount_str,
        "reason": reason,
        "transaction_id": f"ref_{order_id}_{int(quantized * 100)}",
        "message": f"Refund of ${amount_str} processed for order {order_id}",
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
        role="Refund Agent",
        goal="Process refund requests accurately and safely.",
        backstory="You handle refunds and must follow governance rules.",
        tools=[issue_refund],
        verbose=True,
    )

    task = Task(
        description=(
            "Process a refund for order ord_67890 amount $750 due to damage. "
            "Customer name Jane Doe, email jane.doe@company.com. "
            "Call issue_refund with the order_id, amount, and reason."
        ),
        expected_output="Refund confirmation or a governance block/approval.",
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
    except cortexhub.CircuitBreakError as e:
        print(f"\nCIRCUIT BREAKER: {e}")
    except OutputParserException as e:
        print(f"\nCREWAI PARSER ERROR: {e}")


def main() -> None:
    print("\n" + "=" * 60)
    print("Finance Refund Agent (CrewAI)")
    print("Run once without policies, then enable recommendations and rerun.")
    print("=" * 60)
    run_demo()


if __name__ == "__main__":
    main()
