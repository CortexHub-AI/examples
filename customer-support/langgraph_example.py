"""Customer support agent (LangGraph) with CortexHub.

Single-run example for governance before/after policies.
Run:
    uv run python customer-support/langgraph_example.py
"""

import os
import time
import json
import urllib.request
from typing import TypedDict, Annotated, Literal
from operator import add

from dotenv import load_dotenv

load_dotenv()

# -----------------------------------------------------------------------------
# CortexHub: 2-line integration
# -----------------------------------------------------------------------------
import cortexhub

cortex = cortexhub.init(
    "customer-support-langgraph",
    framework=cortexhub.Framework.LANGGRAPH,
    privacy=False,
)

# -----------------------------------------------------------------------------
# LangGraph imports (after CortexHub init)
# -----------------------------------------------------------------------------
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, BaseMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode


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


class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add]


llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
support_llm = llm.bind_tools([lookup_customer, cancel_subscription])


def support_agent(state: AgentState) -> AgentState:
    system = (
        "You are a customer support agent. "
        "Look up the customer, then cancel the subscription if requested."
    )
    response = support_llm.invoke([HumanMessage(content=system)] + state["messages"])
    return {"messages": [response]}


def should_continue(state: AgentState) -> Literal["tools", "end"]:
    last = state["messages"][-1]
    if hasattr(last, "tool_calls") and last.tool_calls:
        return "tools"
    return "end"


def build_workflow():
    workflow = StateGraph(AgentState)
    workflow.add_node("support_agent", support_agent)
    try:
        tool_node = ToolNode([lookup_customer, cancel_subscription], handle_tool_errors=False)
    except TypeError:
        tool_node = ToolNode([lookup_customer, cancel_subscription])
    workflow.add_node("support_tools", tool_node)
    workflow.set_entry_point("support_agent")
    workflow.add_conditional_edges(
        "support_agent",
        should_continue,
        {"tools": "support_tools", "end": END},
    )
    workflow.add_edge("support_tools", "support_agent")
    return workflow.compile()


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


def run_demo(query: str) -> None:
    app = build_workflow()
    state = {"messages": [HumanMessage(content=query)]}
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
        print(f"\nApproval status: {status}")
        return
    except cortexhub.PolicyViolationError as e:
        print(f"\nBLOCKED BY CORTEXHUB: {e}")
        return


def main() -> None:
    print("\n" + "=" * 60)
    print("Customer Support Agent (LangGraph)")
    print("Run once without policies, then enable recommendations and rerun.")
    print("=" * 60)
    run_demo(
        "Please cancel subscription for customer cust_123 because they are moving. "
        "Customer email is jamie.lee@example.com."
    )


if __name__ == "__main__":
    main()
