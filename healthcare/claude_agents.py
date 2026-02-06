"""Healthcare intake agent (Claude Agents) with CortexHub.

Single-run example for governance before/after policies.
Run:
    uv run python healthcare/claude_agents.py
"""

import os
import asyncio
import json
import time
import urllib.request
from typing import Any

from dotenv import load_dotenv

load_dotenv(override=True)

# -----------------------------------------------------------------------------
# CortexHub: 2-line integration
# -----------------------------------------------------------------------------
import cortexhub

cortex = cortexhub.init("healthcare-intake-claude-agents", cortexhub.Framework.CLAUDE_AGENTS, privacy=False)

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


@tool("lookup_patient", "Look up a patient record by ID", {"patient_id": str})
async def lookup_patient(args: dict[str, Any]) -> dict[str, Any]:
    patient_id = args.get("patient_id", "")
    return {
        "content": [{
            "type": "text",
            "text": (
                f"Patient {patient_id}: Alex Johnson, DOB 1988-04-12, "
                "allergies: penicillin, current meds: metformin"
            ),
        }]
    }


@tool(
    "prescribe_medication",
    "Prescribe a medication for a patient",
    {"patient_id": str, "medication": str, "dosage": str, "notes": str},
)
async def prescribe_medication(args: dict[str, Any]) -> dict[str, Any]:
    patient_id = args.get("patient_id", "")
    medication = args.get("medication", "")
    dosage = args.get("dosage", "")
    notes = args.get("notes", "")
    return {
        "content": [{
            "type": "text",
            "text": (
                f"Prescription created for {patient_id}: {medication} {dosage}. "
                f"Notes: {notes}"
            ),
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


def create_healthcare_server():
    return create_sdk_mcp_server(
        name="healthcare",
        version="1.0.0",
        tools=[lookup_patient, prescribe_medication],
    )


async def run_demo() -> None:
    server = create_healthcare_server()

    from cortexhub.adapters.claude_agents import ClaudeAgentsAdapter

    adapter = ClaudeAgentsAdapter(cortex)
    hooks = adapter.create_governance_hooks()

    options = ClaudeAgentOptions(
        system_prompt=(
            "You are a healthcare intake agent. "
            "First look up the patient, then prescribe the requested medication."
        ),
        mcp_servers={"healthcare": server},
        allowed_tools=["mcp__healthcare__lookup_patient", "mcp__healthcare__prescribe_medication"],
        hooks=hooks,
        permission_mode="default",
    )

    task = (
        "Patient ID PT-1001 needs a prescription for oxycodone 10mg, "
        "notes: post-surgery pain management."
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
    print("Healthcare Intake Agent (Claude Agents)")
    print("Run once without policies, then enable recommendations and rerun.")
    print("=" * 60)
    asyncio.run(run_demo())


if __name__ == "__main__":
    main()
