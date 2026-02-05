"""Healthcare intake agent (CrewAI) with CortexHub.

Single-run example for governance before/after policies.
Run:
    uv run python healthcare/crewai.py
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

cortex = cortexhub.init("healthcare-intake-crewai", cortexhub.Framework.CREWAI, privacy=False)

# -----------------------------------------------------------------------------
# CrewAI imports (after CortexHub init)
# -----------------------------------------------------------------------------
from crewai import Agent, Task, Crew, Process
from crewai.tools import tool


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
        role="Healthcare Intake Agent",
        goal="Review patient info and create safe prescriptions.",
        backstory="You assist clinicians and must follow governance rules.",
        tools=[lookup_patient, prescribe_medication],
        verbose=True,
    )

    task = Task(
        description=(
            "Look up patient PT-1001, then prescribe oxycodone 10mg for "
            "post-surgery pain management. Include notes on usage."
        ),
        expected_output="Prescription confirmation or a governance block/approval.",
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
    print("Healthcare Intake Agent (CrewAI)")
    print("Run once without policies, then enable recommendations and rerun.")
    print("=" * 60)
    run_demo()


if __name__ == "__main__":
    main()
