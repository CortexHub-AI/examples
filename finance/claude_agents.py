"""Finance refund agent (Claude Agents) with CortexHub.

Single-run example for governance before/after policies.
Run:
    uv run python finance/claude_agents.py
"""

import os
import asyncio
import json
import time
import urllib.request
from decimal import Decimal, InvalidOperation
from typing import Any

from dotenv import load_dotenv

load_dotenv(override=True)

# -----------------------------------------------------------------------------
# CortexHub: 2-line integration
# -----------------------------------------------------------------------------
import cortexhub

cortex = cortexhub.init("finance-refund-claude-agents", cortexhub.Framework.CLAUDE_AGENTS, privacy=False)

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


@tool("issue_refund", "Issue a refund for an order", {"order_id": str, "amount": int, "reason": str})
async def issue_refund(args: dict[str, Any]) -> dict[str, Any]:
    order_id = args.get("order_id", "")
    amount = args.get("amount", 0)
    reason = args.get("reason", "")
    try:
        decimal_amount = Decimal(str(amount))
    except InvalidOperation:
        return {"content": [{"type": "text", "text": f"Invalid amount: {amount}"}]}
    quantized = decimal_amount.quantize(Decimal("0.01"))
    amount_str = f"{quantized:.2f}"
    message = f"Refund of ${amount_str} processed for order {order_id}. Reason: {reason}"
    return {"content": [{"type": "text", "text": message}]}


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


def create_finance_server():
    return create_sdk_mcp_server(
        name="finance",
        version="1.0.0",
        tools=[issue_refund],
    )


async def run_demo() -> None:
    finance_server = create_finance_server()

    from cortexhub.adapters.claude_agents import ClaudeAgentsAdapter

    adapter = ClaudeAgentsAdapter(cortex)
    hooks = adapter.create_governance_hooks()

    options = ClaudeAgentOptions(
        system_prompt=(
            "You are a finance refund agent. "
            "When asked for a refund, call issue_refund with order_id, amount, reason."
        ),
        mcp_servers={"finance": finance_server},
        allowed_tools=["mcp__finance__issue_refund"],
        hooks=hooks,
        permission_mode="default",
    )

    task = (
        "Process a refund for order ord_67890 for $750 due to damage. "
        "Customer name Jane Doe, email jane.doe@company.com."
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
    print("Finance Refund Agent (Claude Agents)")
    print("Run once without policies, then enable recommendations and rerun.")
    print("=" * 60)
    asyncio.run(run_demo())


if __name__ == "__main__":
    main()
