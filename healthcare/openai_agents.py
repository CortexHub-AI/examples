"""Healthcare intake agent (OpenAI Agents) with CortexHub.

Single-run example for governance before/after policies.
Run:
    uv run python healthcare/openai_agents.py
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

cortex = cortexhub.init("healthcare-intake-openai-agents", cortexhub.Framework.OPENAI_AGENTS, privacy=False)

# -----------------------------------------------------------------------------
# OpenAI Agents imports (after CortexHub init)
# -----------------------------------------------------------------------------
from agents import Agent, Runner, function_tool


@function_tool
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


@function_tool
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


async def run_demo() -> None:
    agent = Agent(
        name="HealthcareIntakeAgent",
        instructions=(
            "You are a healthcare intake agent. "
            "First look up the patient, then prescribe the requested medication."
        ),
        tools=[lookup_patient, prescribe_medication],
    )

    query = (
        "Patient ID PT-1001 needs a prescription for oxycodone 10mg, "
        "notes: post-surgery pain management."
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
    print("Healthcare Intake Agent (OpenAI Agents)")
    print("Run once without policies, then enable recommendations and rerun.")
    print("=" * 60)
    asyncio.run(run_demo())


if __name__ == "__main__":
    main()
