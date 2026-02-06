"""Customer support agent (OpenAI Agents) with CortexHub.

Single-run example for governance before/after policies.
Run:
    uv run python customer-support/openai_agents.py
"""

import os
import asyncio
import json
import time
import urllib.request

from dotenv import load_dotenv

load_dotenv(override=True)

# -----------------------------------------------------------------------------
# CortexHub: 2-line integration
# -----------------------------------------------------------------------------
import cortexhub

cortex = cortexhub.init("customer-support-openai-agents", cortexhub.Framework.OPENAI_AGENTS, privacy=False)

# -----------------------------------------------------------------------------
# OpenAI Agents imports (after CortexHub init)
# -----------------------------------------------------------------------------
from agents import Agent, Runner, function_tool


@function_tool
def lookup_customer(customer_id: str) -> dict:
    """Look up customer information by ID."""
    return {
        "id": customer_id,
        "name": "Jamie Lee",
        "email": "jamie.lee@example.com",
        "status": "active",
        "plan": "premium",
    }


@function_tool
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


async def run_demo() -> None:
    agent = Agent(
        name="CustomerSupportAgent",
        instructions=(
            "You are a customer support agent. "
            "Look up the customer, then cancel the subscription if requested."
        ),
        tools=[lookup_customer, cancel_subscription],
    )

    query = (
        "Please cancel subscription for customer cust_123 because they are moving. "
        "Customer email is jamie.lee@example.com."
    )

    try:
        result = await Runner.run(agent, query)
        print("\n[RESPONSE]")
        print(result.final_output)
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
    print("Customer Support Agent (OpenAI Agents)")
    print("Run once without policies, then enable recommendations and rerun.")
    print("=" * 60)
    asyncio.run(run_demo())


if __name__ == "__main__":
    main()
