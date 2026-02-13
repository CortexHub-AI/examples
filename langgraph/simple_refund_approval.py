"""
Realistic LangGraph refund + approval flow.

Demonstrates a proper multi-step agent workflow:
1. Look up the customer
2. Retrieve order details
3. Check refund eligibility
4. Issue the refund (policy-governed — may require approval)

This produces a rich evidence timeline in CortexHub so the approval UI
can show meaningful verification steps and the evidence assessment has
real data to analyse.

Tip: Configure a policy like "Require approval for issue_refund when
amount > 500" in the CortexHub dashboard to see the full approval flow.
"""

import os
import time
import json
import urllib.request
from decimal import Decimal, InvalidOperation
from typing import TypedDict, Annotated, Literal
from operator import add

from dotenv import load_dotenv

load_dotenv(override=not os.getenv("CORTEXHUB_E2E_RUN_ID"))
print(f"[env] CORTEXHUB_PRIVACY={os.getenv('CORTEXHUB_PRIVACY')}")

# -----------------------------------------------------------------------------
# CortexHub: 2-line integration
# -----------------------------------------------------------------------------
import cortexhub

cortex = cortexhub.init(
    "refund-approval-demo",
    framework=cortexhub.Framework.LANGGRAPH,
    log_level="INFO",
    log_file="./cortexhub.log",
    log_to_console=True,
)

# -----------------------------------------------------------------------------
# LangGraph imports (after CortexHub init)
# -----------------------------------------------------------------------------
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, BaseMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver


# =============================================================================
# Tools — simulate a realistic customer-service backend
# =============================================================================

@tool
def lookup_customer(customer_email: str) -> dict:
    """Look up a customer by email address. Returns customer profile."""
    # Simulated customer database
    customers = {
        "john.doe@example.com": {
            "customer_id": "cust_12345",
            "name": "John Doe",
            "email": "john.doe@example.com",
            "account_status": "active",
            "loyalty_tier": "gold",
            "total_orders": 23,
            "member_since": "2022-03-15",
        },
        "jane.smith@example.com": {
            "customer_id": "cust_67890",
            "name": "Jane Smith",
            "email": "jane.smith@example.com",
            "account_status": "active",
            "loyalty_tier": "silver",
            "total_orders": 8,
            "member_since": "2023-09-01",
        },
    }
    customer = customers.get(customer_email.lower())
    if not customer:
        return {"found": False, "error": f"No customer found with email {customer_email}"}
    return {"found": True, **customer}


@tool
def get_order_details(order_id: str) -> dict:
    """Retrieve full details for an order by order ID."""
    # Simulated order database
    orders = {
        "ord_67890": {
            "order_id": "ord_67890",
            "customer_id": "cust_12345",
            "status": "delivered",
            "items": [
                {"name": "Wireless Headphones Pro", "sku": "WHP-001", "qty": 1, "price": 599.99},
                {"name": "USB-C Cable", "sku": "USB-C-3M", "qty": 2, "price": 14.99},
            ],
            "subtotal": 629.97,
            "tax": 50.40,
            "total": 680.37,
            "payment_method": "credit_card_ending_4242",
            "ordered_at": "2026-01-28T14:22:00Z",
            "delivered_at": "2026-02-01T09:15:00Z",
            "shipping_address_city": "San Francisco",
        },
        "ord_11111": {
            "order_id": "ord_11111",
            "customer_id": "cust_67890",
            "status": "delivered",
            "items": [
                {"name": "Laptop Stand", "sku": "LS-100", "qty": 1, "price": 89.99},
            ],
            "subtotal": 89.99,
            "tax": 7.20,
            "total": 97.19,
            "payment_method": "credit_card_ending_1234",
            "ordered_at": "2026-02-05T10:00:00Z",
            "delivered_at": "2026-02-08T16:30:00Z",
            "shipping_address_city": "Austin",
        },
    }
    order = orders.get(order_id)
    if not order:
        return {"found": False, "error": f"Order {order_id} not found"}
    return {"found": True, **order}


@tool
def check_refund_eligibility(order_id: str, customer_id: str, reason: str) -> dict:
    """Check whether a refund is eligible based on order, customer, and reason.

    Returns eligibility status and any conditions.
    """
    # Simulated eligibility rules
    eligible_orders = {"ord_67890", "ord_11111"}

    if order_id not in eligible_orders:
        return {
            "eligible": False,
            "reason": "Order not found or outside refund window",
        }

    # Simulate checking conditions
    return {
        "eligible": True,
        "order_id": order_id,
        "customer_id": customer_id,
        "refund_reason": reason,
        "refund_window_days": 30,
        "days_since_delivery": 12,
        "within_window": True,
        "max_refund_amount": 750.00,
        "notes": "Product damage claims are eligible for full refund within 30 days of delivery.",
    }


@tool
def issue_refund(order_id: str, amount: int, reason: str) -> dict:
    """Issue a refund for an order. This is the final step after verification.

    Only call this after you have:
    1. Verified the customer exists
    2. Retrieved and confirmed the order details
    3. Checked refund eligibility
    """
    try:
        decimal_amount = Decimal(str(amount))
    except InvalidOperation:
        return {"success": False, "error": f"Invalid amount: {amount}"}

    quantized = decimal_amount.quantize(Decimal("0.01"))
    amount_str = f"{quantized:.2f}"

    return {
        "success": True,
        "refund_id": "ref_98765",
        "order_id": order_id,
        "amount": amount_str,
        "reason": reason,
        "message": f"Refund of ${amount_str} processed for order {order_id}",
        "estimated_processing_days": 3,
    }


# =============================================================================
# LangGraph State
# =============================================================================
ALL_TOOLS = [lookup_customer, get_order_details, check_refund_eligibility, issue_refund]


class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add]


# =============================================================================
# LLM + Agent
# =============================================================================
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
agent_llm = llm.bind_tools(ALL_TOOLS)

SYSTEM_PROMPT = """\
You are a customer service refund agent. You MUST follow this workflow \
before issuing any refund:

1. **Look up the customer** — use lookup_customer with the customer's email \
   to verify they exist and their account is active.
2. **Retrieve order details** — use get_order_details with the order ID to \
   confirm the order exists, belongs to this customer, and see the items/total.
3. **Check refund eligibility** — use check_refund_eligibility with the \
   order ID, customer ID, and reason to verify the refund is allowed.
4. **Issue the refund** — only after all three checks pass, use issue_refund \
   with the verified order ID, the eligible amount, and the reason.

NEVER skip steps. NEVER issue a refund without verifying the customer, \
the order, and eligibility first. If any step fails, explain to the user \
why the refund cannot be processed.

Be concise in your reasoning. State which step you are performing and why.
"""


def refund_agent(state: AgentState) -> AgentState:
    response = agent_llm.invoke(
        [HumanMessage(content=SYSTEM_PROMPT)] + state["messages"]
    )
    return {"messages": [response]}


def should_continue(state: AgentState) -> Literal["tools", "end"]:
    last = state["messages"][-1]
    if hasattr(last, "tool_calls") and last.tool_calls:
        return "tools"
    return "end"


# =============================================================================
# Workflow
# =============================================================================
def build_workflow():
    workflow = StateGraph(AgentState)

    workflow.add_node("refund_agent", refund_agent)

    try:
        tool_node = ToolNode(ALL_TOOLS, handle_tool_errors=False)
    except TypeError:
        tool_node = ToolNode(ALL_TOOLS)

    workflow.add_node("refund_tools", tool_node)
    workflow.set_entry_point("refund_agent")

    workflow.add_conditional_edges(
        "refund_agent",
        should_continue,
        {"tools": "refund_tools", "end": END},
    )
    workflow.add_edge("refund_tools", "refund_agent")

    memory = MemorySaver()
    return workflow.compile(checkpointer=memory)


# =============================================================================
# Approval polling (demo-friendly)
# =============================================================================
def wait_for_approval(approval_id: str) -> str | None:
    if not approval_id:
        return None

    api_key = os.getenv("CORTEXHUB_API_KEY", "")
    url = f"{cortex.api_url.rstrip('/')}/v1/approvals/{approval_id}"
    headers = {"X-API-Key": api_key}

    print("Waiting for approval decision (check CortexHub dashboard)...")
    while True:
        req = urllib.request.Request(url, headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        status = data.get("status")
        if status and status.lower() != "pending":
            return status.lower()

        time.sleep(2)


# =============================================================================
# Demo runner
# =============================================================================
def run_refund_demo(query: str) -> None:
    app = build_workflow()

    thread_id = "refund_demo_thread"
    config = {"configurable": {"thread_id": thread_id}}

    state = {"messages": [HumanMessage(content=query)]}

    try:
        result = app.invoke(state, config)
        final = result["messages"][-1]
        print("\n=== FINAL RESPONSE ===")
        print(final.content)
        return

    except cortexhub.ApprovalRequiredError as e:
        print("\n=== APPROVAL REQUIRED ===")
        print(f"  Tool:        {e.tool_name}")
        print(f"  Arguments:   {e.tool_args}")
        print(f"  Reason:      {e.reason}")
        print(f"  Approval ID: {e.approval_id}")

        status = wait_for_approval(e.approval_id)

        if status == "approved":
            print("\n=== APPROVED — RESUMING AGENT ===")
            if e.context_hash:
                cortex.mark_approval_granted(e.approval_id, e.context_hash)

            try:
                result = app.invoke(None, config)
                final = result["messages"][-1]
                print("\n=== FINAL RESPONSE (AFTER APPROVAL) ===")
                print(final.content)
                return
            except Exception as resume_error:
                print(f"\nError resuming after approval: {resume_error}")
                import traceback
                traceback.print_exc()
                return

        print("\n=== NOT APPROVED — EXECUTION CANCELLED ===")
        return

    except cortexhub.PolicyViolationError as e:
        print(f"\n=== BLOCKED BY POLICY ===")
        print(f"  Reason: {e}")
        return


# =============================================================================
# Entry point
# =============================================================================
def main() -> None:
    run_refund_demo(
        "Hi, I need a refund for order ord_67890. The wireless headphones "
        "arrived damaged — the left ear cup is cracked. My email is "
        "john.doe@example.com. Please process a full refund of 750."
    )


if __name__ == "__main__":
    main()
