"""
Minimal LangGraph refund + approval flow (demo-safe, single approval).

Key properties:
- One approval only
- No replay of tool calls
- Clean interception → approve → resume narrative
"""

import os
import time
import json
import urllib.request
from decimal import Decimal, InvalidOperation
from typing import TypedDict, Annotated, Literal
from operator import add

from dotenv import load_dotenv

load_dotenv(override=True)
print(f"[env] CORTEXHUB_PRIVACY={os.getenv('CORTEXHUB_PRIVACY')}")

# -----------------------------------------------------------------------------
# CortexHub: 2-line integration
# -----------------------------------------------------------------------------
import cortexhub

cortex = cortexhub.init(
    "refund-approval-demo",
    framework=cortexhub.Framework.LANGGRAPH,
)

# -----------------------------------------------------------------------------
# LangGraph imports (after CortexHub init)
# -----------------------------------------------------------------------------
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, BaseMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode


# -----------------------------------------------------------------------------
# Tool: Refund
# -----------------------------------------------------------------------------
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
        "message": f"Refund of ${amount_str} processed for order {order_id}",
    }


# -----------------------------------------------------------------------------
# LangGraph State
# -----------------------------------------------------------------------------
class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add]


# -----------------------------------------------------------------------------
# LLM + Agent
# -----------------------------------------------------------------------------
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
refund_llm = llm.bind_tools([issue_refund])


def refund_agent(state: AgentState) -> AgentState:
    system = (
        "You are a refund agent. "
        "If the user asks for a refund, call the issue_refund tool."
    )

    response = refund_llm.invoke(
        [HumanMessage(content=system)] + state["messages"]
    )

    return {"messages": [response]}


def should_continue(state: AgentState) -> Literal["tools", "end"]:
    last = state["messages"][-1]
    if hasattr(last, "tool_calls") and last.tool_calls:
        return "tools"
    return "end"


# -----------------------------------------------------------------------------
# Workflow
# -----------------------------------------------------------------------------
def build_workflow():
    workflow = StateGraph(AgentState)

    workflow.add_node("refund_agent", refund_agent)

    try:
        tool_node = ToolNode([issue_refund], handle_tool_errors=False)
    except TypeError:
        tool_node = ToolNode([issue_refund])

    workflow.add_node("refund_tools", tool_node)

    workflow.set_entry_point("refund_agent")

    workflow.add_conditional_edges(
        "refund_agent",
        should_continue,
        {"tools": "refund_tools", "end": END},
    )

    workflow.add_edge("refund_tools", "refund_agent")

    return workflow.compile()


# -----------------------------------------------------------------------------
# Approval polling (demo-friendly)
# -----------------------------------------------------------------------------
def wait_for_approval(approval_id: str) -> str | None:
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


# -----------------------------------------------------------------------------
# Demo runner (IMPORTANT PART)
# -----------------------------------------------------------------------------
def run_refund_demo(query: str) -> None:
    app = build_workflow()

    state = {
        "messages": [HumanMessage(content=query)]
    }

    try:
        result = app.invoke(state)
        final = result["messages"][-1]
        print(final.content)
        return

    except cortexhub.ApprovalRequiredError as e:
        print("\nAPPROVAL REQUIRED")
        print(f"- approval_id: {e.approval_id}")
        print(f"- tool: {e.tool_name}")
        print(f"- reason: {e.reason}")

        status = wait_for_approval(e.approval_id)

        if status == "approved":
            print("\nAPPROVED — execution will resume once")
            # IMPORTANT:
            # For demo clarity, we DO NOT replay the graph.
            # CortexHub has already recorded the approval.
            # In real systems, you would resume from a checkpoint.
            return

        print("\nNOT APPROVED — execution cancelled")
        return

    except cortexhub.PolicyViolationError as e:
        print(f"\nBLOCKED BY CORTEXHUB: {e}")
        return


# -----------------------------------------------------------------------------
# Entry point
# -----------------------------------------------------------------------------
def main() -> None:
    run_refund_demo(
        "Please refund order ord_67890 for 750 due to damage. "
        "My name is John Doe and my email is john.doe@example.com."
    )


if __name__ == "__main__":
    main()
