"""Healthcare intake agent (LangGraph) with CortexHub.

Single-run example for governance before/after policies.
Run:
    uv run python healthcare/langgraph_example.py
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
    "healthcare-intake-langgraph",
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
def lookup_patient(patient_id: str) -> dict:
    """Look up a patient record by ID."""
    return {
        "patient_id": patient_id,
        "name": "Alex Johnson",
        "dob": "1988-04-12",
        "phone": "+1-555-0101",
        "allergies": ["penicillin"],
        "current_medications": ["metformin"],
    }


@tool
def prescribe_medication(patient_id: str, medication: str, dosage: str, notes: str) -> dict:
    """Prescribe a medication for a patient."""
    return {
        "patient_id": patient_id,
        "medication": medication,
        "dosage": dosage,
        "notes": notes,
        "status": "prescribed",
    }


class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add]


llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
intake_llm = llm.bind_tools([lookup_patient, prescribe_medication])


def intake_agent(state: AgentState) -> AgentState:
    system = (
        "You are a healthcare intake agent. "
        "First look up the patient, then prescribe the requested medication."
    )
    response = intake_llm.invoke([HumanMessage(content=system)] + state["messages"])
    return {"messages": [response]}


def should_continue(state: AgentState) -> Literal["tools", "end"]:
    last = state["messages"][-1]
    if hasattr(last, "tool_calls") and last.tool_calls:
        return "tools"
    return "end"


def build_workflow():
    workflow = StateGraph(AgentState)
    workflow.add_node("intake_agent", intake_agent)
    try:
        tool_node = ToolNode([lookup_patient, prescribe_medication], handle_tool_errors=False)
    except TypeError:
        tool_node = ToolNode([lookup_patient, prescribe_medication])
    workflow.add_node("intake_tools", tool_node)
    workflow.set_entry_point("intake_agent")
    workflow.add_conditional_edges(
        "intake_agent",
        should_continue,
        {"tools": "intake_tools", "end": END},
    )
    workflow.add_edge("intake_tools", "intake_agent")
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
    print("Healthcare Intake Agent (LangGraph)")
    print("Run once without policies, then enable recommendations and rerun.")
    print("=" * 60)
    run_demo(
        "Patient ID PT-1001 needs a prescription for oxycodone 10mg, "
        "notes: post-surgery pain management."
    )


if __name__ == "__main__":
    main()
