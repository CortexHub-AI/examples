"""Customer support agent (Claude Agents) with CortexHub.

Single-run example for governance before/after policies.
Run:
    uv run python customer-support/claude_agents.py
"""

import os
import asyncio
import json
import time
import urllib.request
from typing import Any

from dotenv import load_dotenv

load_dotenv()

# -----------------------------------------------------------------------------
# CortexHub: 2-line integration
# -----------------------------------------------------------------------------
import cortexhub

cortex = cortexhub.init("customer-support-claude-agents", cortexhub.Framework.CLAUDE_AGENTS, privacy=False)

# -----------------------------------------------------------------------------
# Claude Agent SDK imports (after CortexHub init)
# -----------------------------------------------------------------------------
from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    tool,
    create_sdk_mcp_server,
    AssistantMessage,
    TextBlock,
    ToolUseBlock,
    ResultMessage,
)


@tool("lookup_customer", "Look up customer information by ID", {"customer_id": str})
async def lookup_customer(args: dict[str, Any]) -> dict[str, Any]:
    customer_id = args.get("customer_id", "")
    return {
        "content": [{
            "type": "text",
            "text": (
                f"Customer {customer_id}: Jamie Lee, email jamie.lee@example.com, "
                "status active, plan premium"
            ),
        }]
    }


@tool(
    "cancel_subscription",
    "Cancel a customer's subscription",
    {"customer_id": str, "reason": str, "immediate": bool},
)
async def cancel_subscription(args: dict[str, Any]) -> dict[str, Any]:
    customer_id = args.get("customer_id", "")
    reason = args.get("reason", "")
    immediate = bool(args.get("immediate", False))
    effective = "immediately" if immediate else "end_of_billing_period"
    return {
        "content": [{
            "type": "text",
            "text": f"Cancellation scheduled for {customer_id} ({effective}). Reason: {reason}",
        }]
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


def create_support_server():
    return create_sdk_mcp_server(
        name="support",
        version="1.0.0",
        tools=[lookup_customer, cancel_subscription],
    )


async def run_demo() -> None:
    server = create_support_server()

    from cortexhub.adapters.claude_agents import ClaudeAgentsAdapter

    adapter = ClaudeAgentsAdapter(cortex)
    hooks = adapter.create_governance_hooks()

    options = ClaudeAgentOptions(
        system_prompt=(
            "You are a customer support agent. "
            "Look up the customer, then cancel the subscription if requested."
        ),
        mcp_servers={"support": server},
        allowed_tools=["mcp__support__lookup_customer", "mcp__support__cancel_subscription"],
        hooks=hooks,
        permission_mode="default",
    )

    task = (
        "Cancel subscription for customer cust_123 because they are moving. "
        "Customer email is jamie.lee@example.com."
    )

    async with ClaudeSDKClient(options=options) as client:
        try:
            await client.query(task)
            async for message in client.receive_response():
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            print(f"\nAssistant: {block.text}")
                        elif isinstance(block, ToolUseBlock):
                            print(f"\nTool call: {block.name} input={block.input}")
                elif isinstance(message, ResultMessage):
                    if message.is_error:
                        print(f"\nError: {message.result}")
            return
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
    print("Customer Support Agent (Claude Agents)")
    print("Run once without policies, then enable recommendations and rerun.")
    print("=" * 60)
    asyncio.run(run_demo())


if __name__ == "__main__":
    main()
