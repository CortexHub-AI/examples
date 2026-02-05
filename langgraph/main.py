"""LangGraph Customer Support Agent with CortexHub

A multi-agent customer support system demonstrating:
- Router agent that classifies customer intent
- Specialized agents for support, billing, and refunds
- Tool tracing via CortexHub
- PII detection in customer data

Run:
    uv run python main.py
"""

import os
import time
import json
import urllib.request
from decimal import Decimal, InvalidOperation
from typing import TypedDict, Literal, Annotated
from operator import add

from dotenv import load_dotenv

load_dotenv()

# =============================================================================
# CORTEXHUB: 2-line integration
# =============================================================================
import cortexhub
cortex = cortexhub.init("customer-support", cortexhub.Framework.LANGGRAPH)

# =============================================================================
# LangGraph imports (after CortexHub init to enable auto-patching)
# =============================================================================
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode


# =============================================================================
# Customer Support Tools
# =============================================================================

@tool
def lookup_customer(customer_id: str | None = None, order_id: str | None = None) -> dict:
    """Look up customer information by customer ID or order ID.
    
    Args:
        customer_id: Customer ID (e.g., "cust_123")
        order_id: Order ID (e.g., "ord_456")
    
    Returns:
        Customer details including name, email, and account status
    """
    # Simulated customer database
    customers = {
        "cust_123": {
            "id": "cust_123",
            "name": "John Smith",
            "email": "john.smith@email.com",
            "phone": "+1-555-123-4567",
            "status": "active",
            "tier": "gold",
        },
        "cust_456": {
            "id": "cust_456", 
            "name": "Jane Doe",
            "email": "jane.doe@company.com",
            "phone": "+1-555-987-6543",
            "status": "active",
            "tier": "platinum",
        },
    }
    
    # Order to customer mapping
    orders = {
        "ord_12345": "cust_123",
        "ord_67890": "cust_456",
    }
    
    if order_id and order_id in orders:
        customer_id = orders[order_id]
    
    if customer_id and customer_id in customers:
        return customers[customer_id]
    
    return {"error": "Customer not found"}


@tool
def update_customer_email(customer_id: str, new_email: str) -> dict:
    """Update a customer's email address.
    
    Args:
        customer_id: The customer ID
        new_email: The new email address
    
    Returns:
        Confirmation of the update
    """
    # PII is automatically detected by CortexHub
    return {
        "success": True,
        "customer_id": customer_id,
        "new_email": new_email,
        "message": f"Email updated to {new_email}",
    }


@tool
def get_account_balance(customer_id: str) -> dict:
    """Get the billing balance for a customer account.
    
    Args:
        customer_id: The customer ID
    
    Returns:
        Account balance and recent charges
    """
    balances = {
        "cust_123": {"balance": 150.00, "currency": "USD", "due_date": "2026-02-15"},
        "cust_456": {"balance": 0.00, "currency": "USD", "due_date": None},
    }
    
    if customer_id in balances:
        return balances[customer_id]
    return {"error": "Account not found"}


@tool
def issue_refund(order_id: str, amount: str, reason: str) -> dict:
    """Issue a refund for an order.
    
    Args:
        order_id: The order ID to refund
        amount: Refund amount in dollars (decimal string)
        reason: Reason for the refund
    
    Returns:
        Refund confirmation with transaction ID
    
    Note: Refunds over $500 may require approval.
    """
    # This tool may require approval for high amounts
    try:
        decimal_amount = Decimal(str(amount))
    except InvalidOperation:
        return {"success": False, "error": f"Invalid amount: {amount}"}

    quantized = decimal_amount.quantize(Decimal("0.01"))
    cents = int((quantized * 100).to_integral_value())
    amount_str = f"{quantized:.2f}"
    return {
        "success": True,
        "order_id": order_id,
        "amount": amount_str,
        "reason": reason,
        "transaction_id": f"ref_{order_id}_{cents}",
        "message": f"Refund of ${amount_str} processed for order {order_id}",
    }


@tool
def create_support_ticket(
    customer_id: str,
    subject: str,
    description: str,
    priority: Literal["low", "medium", "high"] = "medium"
) -> dict:
    """Create a support ticket for a customer issue.
    
    Args:
        customer_id: The customer ID
        subject: Ticket subject line
        description: Detailed description of the issue
        priority: Ticket priority level
    
    Returns:
        Ticket creation confirmation with ticket ID
    """
    import random
    ticket_id = f"TKT-{random.randint(10000, 99999)}"
    
    return {
        "success": True,
        "ticket_id": ticket_id,
        "customer_id": customer_id,
        "subject": subject,
        "priority": priority,
        "status": "open",
        "message": f"Support ticket {ticket_id} created",
    }


@tool  
def cancel_subscription(customer_id: str, reason: str, immediate: bool = False) -> dict:
    """Cancel a customer's subscription.
    
    Args:
        customer_id: The customer ID
        reason: Reason for cancellation
        immediate: If True, cancel immediately. If False, cancel at end of billing period.
    
    Returns:
        Cancellation confirmation
    
    Note: This is a high-risk operation that may require approval.
    """
    return {
        "success": True,
        "customer_id": customer_id,
        "reason": reason,
        "effective": "immediately" if immediate else "end of billing period",
        "message": f"Subscription cancellation scheduled for customer {customer_id}",
    }


@tool
def get_subscription_status(customer_id: str) -> dict:
    """Get subscription status for a customer.
    
    Args:
        customer_id: The customer ID
    
    Returns:
        Subscription status and renewal date
    """
    statuses = {
        "cust_123": {"status": "active", "renews_on": "2026-03-01"},
        "cust_456": {"status": "active", "renews_on": "2026-02-20"},
    }
    return statuses.get(customer_id, {"error": "Customer not found"})


@tool
def update_billing_address(customer_id: str, address: str) -> dict:
    """Update billing address for a customer.
    
    Args:
        customer_id: The customer ID
        address: New billing address
    
    Returns:
        Confirmation of the update
    """
    return {
        "success": True,
        "customer_id": customer_id,
        "address": address,
        "message": "Billing address updated",
    }


@tool
def apply_discount_code(customer_id: str, code: str) -> dict:
    """Apply a discount code to a customer account.
    
    Args:
        customer_id: The customer ID
        code: Discount code string
    
    Returns:
        Discount application result
    """
    return {
        "success": True,
        "customer_id": customer_id,
        "code": code,
        "message": f"Discount {code} applied",
    }


# =============================================================================
# Agent State
# =============================================================================

class AgentState(TypedDict):
    """State for the customer support workflow."""
    messages: Annotated[list[BaseMessage], add]
    customer_intent: str | None
    current_agent: str


# =============================================================================
# LLM Setup
# =============================================================================

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# Bind tools to LLM for each agent type
support_tools = [lookup_customer, create_support_ticket, update_customer_email]
billing_tools = [lookup_customer, get_account_balance, issue_refund]
refund_tools = [lookup_customer, issue_refund]
cancellation_tools = [lookup_customer, cancel_subscription]

# Extra tools for inventory discovery (not bound to any agent by default)
inventory_only_tools = [
    get_subscription_status,
    update_billing_address,
    apply_discount_code,
]

support_llm = llm.bind_tools(support_tools)
billing_llm = llm.bind_tools(billing_tools)
refund_llm = llm.bind_tools(refund_tools)


# =============================================================================
# Workflow Nodes
# =============================================================================

def router(state: AgentState) -> AgentState:
    """Router node - classifies customer intent and routes to specialist."""
    
    last_message = state["messages"][-1]
    
    # Use LLM to classify intent
    classification_prompt = f"""Classify this customer support request into one of these categories:
- support: General product questions, technical issues, account help
- billing: Payment issues, invoices, account balance questions  
- refund: Refund requests, order cancellations
- cancellation: Subscription cancellations

Customer message: {last_message.content}

Respond with just the category name."""

    response = llm.invoke([HumanMessage(content=classification_prompt)])
    intent = response.content.strip().lower()
    
    # Validate intent
    valid_intents = ["support", "billing", "refund", "cancellation"]
    if intent not in valid_intents:
        intent = "support"  # Default to support
    
    print(f"\n[ROUTER] Classified intent: {intent}")
    
    return {
        "messages": [],
        "customer_intent": intent,
        "current_agent": intent,
    }


def support_agent(state: AgentState) -> AgentState:
    """Support specialist agent."""
    print(f"\n[SUPPORT AGENT] Handling request...")
    
    system = """You are a helpful customer support agent. You can:
- Look up customer information
- Create support tickets
- Update customer email addresses

Be friendly and professional. Use the available tools to help the customer."""

    messages = [HumanMessage(content=system)] + state["messages"]
    response = support_llm.invoke(messages)
    
    return {"messages": [response], "customer_intent": state["customer_intent"], "current_agent": "support"}


def billing_agent(state: AgentState) -> AgentState:
    """Billing specialist agent."""
    print(f"\n[BILLING AGENT] Handling request...")
    
    system = """You are a billing specialist. You can:
- Look up customer information
- Check account balances
- Process refunds (may require approval for high amounts)

Be clear about billing details. Use tools to verify information."""

    messages = [HumanMessage(content=system)] + state["messages"]
    response = billing_llm.invoke(messages)
    
    return {"messages": [response], "customer_intent": state["customer_intent"], "current_agent": "billing"}


def refund_agent(state: AgentState) -> AgentState:
    """Refund specialist agent."""
    print(f"\n[REFUND AGENT] Handling request...")
    
    system = """You are a refund specialist. You can:
- Look up customer and order information
- Process refunds

Note: Refunds over $500 may require manager approval. Always verify the order 
before processing a refund."""

    messages = [HumanMessage(content=system)] + state["messages"]
    response = refund_llm.invoke(messages)
    
    return {"messages": [response], "customer_intent": state["customer_intent"], "current_agent": "refund"}


def should_continue(state: AgentState) -> Literal["tools", "end"]:
    """Check if the agent needs to call tools or is done."""
    last_message = state["messages"][-1]
    
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    return "end"


def route_by_intent(state: AgentState) -> str:
    """Route to the appropriate specialist based on intent."""
    intent = state.get("customer_intent", "support")
    
    if intent == "billing":
        return "billing_agent"
    elif intent == "refund":
        return "refund_agent"
    else:
        return "support_agent"


# =============================================================================
# Build the Graph
# =============================================================================

def build_workflow():
    """Build the customer support workflow graph."""

    def _build_tool_node(tools):
        """Prefer raising tool errors to allow approval flow to pause."""
        try:
            return ToolNode(tools, handle_tool_errors=False)
        except TypeError:
            # Older LangGraph versions don't support handle_tool_errors
            return ToolNode(tools)
    
    # Create tool nodes (include extra tools for inventory discovery)
    support_tool_node = _build_tool_node(support_tools + inventory_only_tools)
    billing_tool_node = _build_tool_node(billing_tools + inventory_only_tools)
    refund_tool_node = _build_tool_node(refund_tools + inventory_only_tools)
    
    # Build graph
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("router", router)
    workflow.add_node("support_agent", support_agent)
    workflow.add_node("billing_agent", billing_agent)
    workflow.add_node("refund_agent", refund_agent)
    workflow.add_node("support_tools", support_tool_node)
    workflow.add_node("billing_tools", billing_tool_node)
    workflow.add_node("refund_tools", refund_tool_node)
    
    # Set entry point
    workflow.set_entry_point("router")
    
    # Router to specialist
    workflow.add_conditional_edges(
        "router",
        route_by_intent,
        {
            "support_agent": "support_agent",
            "billing_agent": "billing_agent",
            "refund_agent": "refund_agent",
        }
    )
    
    # Support agent loop
    workflow.add_conditional_edges(
        "support_agent",
        should_continue,
        {"tools": "support_tools", "end": END}
    )
    workflow.add_edge("support_tools", "support_agent")
    
    # Billing agent loop
    workflow.add_conditional_edges(
        "billing_agent",
        should_continue,
        {"tools": "billing_tools", "end": END}
    )
    workflow.add_edge("billing_tools", "billing_agent")
    
    # Refund agent loop  
    workflow.add_conditional_edges(
        "refund_agent",
        should_continue,
        {"tools": "refund_tools", "end": END}
    )
    workflow.add_edge("refund_tools", "refund_agent")
    
    return workflow.compile()


# =============================================================================
# Main
# =============================================================================

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


def run_customer_support(query: str, *, max_retries: int = 1) -> bool:
    """Run the customer support workflow for a query."""
    
    print("\n" + "=" * 60)
    print(f"CUSTOMER: {query}")
    print("=" * 60)
    
    app = build_workflow()
    
    initial_state = {
        "messages": [HumanMessage(content=query)],
        "customer_intent": None,
        "current_agent": "router",
    }

    attempts = 0
    while True:
        try:
            result = app.invoke(initial_state)

            # Get final response
            final_message = result["messages"][-1]
            if hasattr(final_message, "content"):
                print(f"\n[RESPONSE]\n{final_message.content}")
            return True
        except cortexhub.PolicyViolationError as e:
            print(f"\n❌ BLOCKED BY CORTEXHUB: {e}")
            return True
        except cortexhub.ApprovalRequiredError as e:
            print(f"\n⏸️  APPROVAL REQUIRED")
            print(f"   Approval ID: {e.approval_id}")
            print(f"   Tool: {e.tool_name}")
            print(f"   Reason: {e.reason}")
            print(f"   Expires: {e.expires_at}")
            print(f"\n   Decision endpoint: {e.decision_endpoint}")
            print(f"   Configure a webhook to receive approval.decisioned event")
            api_key = os.getenv("CORTEXHUB_API_KEY", "")
            if not api_key or not e.approval_id:
                return False

            status, _decision = _wait_for_approval(e.approval_id, cortex.api_url, api_key)
            if status == "approved":
                attempts += 1
                if attempts <= max_retries:
                    print("\nRe-running the scenario after approval...")
                    continue
                print("\nApproval received, but max retries reached. Re-run to continue.")
                return True
            if status in {"denied", "expired"}:
                print(f"\nApproval {status}. Skipping this scenario.")
                return True
            return False


def main():
    """Run example customer support scenarios."""
    
    print("\n" + "=" * 60)
    print("LangGraph Customer Support Agent")
    print("with CortexHub")
    print("=" * 60)
    
    scenarios = [
        # Support query - will use lookup_customer
        "Hi, I'm customer cust_123. Can you help me update my email to newemail@example.com?",
        
        # Billing query - will check balance
        "What's my current account balance? My customer ID is cust_456.",
        
        # Refund query - may require approval if amount > $500
        "I need a refund for order ord_12345. I was charged $299 but I returned the item.",
        
        # High-value refund - likely requires approval
        "I need a refund for order ord_67890 for $750. The product was defective.",
    ]
    
    for scenario in scenarios:
        if not run_customer_support(scenario):
            break
        print()
    
    print("\n" + "=" * 60)
    print("Session Complete")
    print("=" * 60)
    print("\nCheck your CortexHub dashboard to see:")
    print("- All tool invocations logged")
    print("- PII detected (emails, phone numbers, names)")
    print("- Telemetry recorded")
    print("=" * 60)


if __name__ == "__main__":
    main()
