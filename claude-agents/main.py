"""Claude Agent SDK DevOps Assistant with CortexHub

A DevOps assistant demonstrating:
- Custom MCP tools for DevOps operations
- Built-in tool hooks via CortexHub
- Approval workflows for production deployments
- Security scanning integration

Run:
    uv run python main.py
"""

import os
import asyncio
import json
import time
import urllib.request
from typing import Any

from dotenv import load_dotenv

load_dotenv(override=True)

# =============================================================================
# CORTEXHUB: 2-line integration
# =============================================================================
import cortexhub
cortex = cortexhub.init("devops-assistant", cortexhub.Framework.CLAUDE_AGENTS)

# =============================================================================
# Claude Agent SDK imports (after CortexHub init to enable auto-patching)
# =============================================================================
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


# =============================================================================
# DevOps Tools (Custom MCP Tools)
# =============================================================================

@tool("check_security", "Scan a file or directory for security vulnerabilities", {"path": str})
async def check_security(args: dict[str, Any]) -> dict[str, Any]:
    """Scan for common security issues in files."""
    path = args.get("path", ".")
    
    findings = [
        {"severity": "high", "issue": "Hardcoded API key detected", "file": f"{path}/config.py"},
        {"severity": "medium", "issue": "Insecure file permissions", "file": f"{path}/secrets/"},
        {"severity": "low", "issue": "Outdated dependency version", "file": f"{path}/requirements.txt"},
    ]
    
    return {
        "content": [{
            "type": "text",
            "text": f"Security scan complete for {path}:\n" + 
                    "\n".join(f"- [{f['severity'].upper()}] {f['issue']} in {f['file']}" 
                              for f in findings)
        }]
    }


@tool("deploy_service", "Deploy a service to the specified environment", {
    "service": str,
    "environment": str,
    "version": str,
})
async def deploy_service(args: dict[str, Any]) -> dict[str, Any]:
    """Deploy a service - HIGH RISK operation for production."""
    service = args.get("service", "unknown")
    environment = args.get("environment", "dev")
    version = args.get("version", "latest")
    
    # High-risk deployments may require approval for production
    return {
        "content": [{
            "type": "text",
            "text": f"Deployment initiated:\n"
                    f"- Service: {service}\n"
                    f"- Environment: {environment}\n"
                    f"- Version: {version}\n"
                    f"- Status: SUCCESS\n"
                    f"- Deploy ID: deploy-{service}-{environment}-001"
        }]
    }


@tool("get_service_status", "Get the status of a deployed service", {"service": str})
async def get_service_status(args: dict[str, Any]) -> dict[str, Any]:
    """Check service health and status."""
    service = args.get("service", "unknown")
    
    return {
        "content": [{
            "type": "text",
            "text": f"Service: {service}\n"
                    f"- Status: RUNNING\n"
                    f"- Health: HEALTHY\n"
                    f"- Uptime: 99.99%\n"
                    f"- Instances: 3/3\n"
                    f"- Last deploy: 2026-01-24T10:30:00Z"
        }]
    }


@tool("rollback_deployment", "Rollback a service to the previous version", {
    "service": str,
    "environment": str,
})
async def rollback_deployment(args: dict[str, Any]) -> dict[str, Any]:
    """Rollback deployment - HIGH RISK operation."""
    service = args.get("service", "unknown")
    environment = args.get("environment", "dev")
    
    return {
        "content": [{
            "type": "text",
            "text": f"Rollback initiated:\n"
                    f"- Service: {service}\n"
                    f"- Environment: {environment}\n"
                    f"- Rolling back to previous version...\n"
                    f"- Status: SUCCESS"
        }]
    }


@tool("list_services", "List all deployed services in an environment", {"environment": str})
async def list_services(args: dict[str, Any]) -> dict[str, Any]:
    """List services in an environment."""
    environment = args.get("environment", "production")
    
    services = [
        {"name": "api-gateway", "status": "running", "version": "3.2.1"},
        {"name": "payment-service", "status": "running", "version": "2.0.0"},
        {"name": "user-service", "status": "running", "version": "1.5.3"},
        {"name": "notification-service", "status": "degraded", "version": "1.2.0"},
    ]
    
    return {
        "content": [{
            "type": "text",
            "text": f"Services in {environment}:\n" +
                    "\n".join(f"- {s['name']}: {s['status']} (v{s['version']})" 
                              for s in services)
        }]
    }


# =============================================================================
# Agent Setup
# =============================================================================

def _get_api_url() -> str:
    return os.getenv("CORTEXHUB_API_URL") or getattr(cortex, "api_url", "")


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


def create_devops_server():
    """Create MCP server with DevOps tools."""
    return create_sdk_mcp_server(
        name="devops",
        version="1.0.0",
        tools=[
            check_security,
            deploy_service,
            get_service_status,
            rollback_deployment,
            list_services,
        ]
    )


async def run_devops_assistant():
    """Run the DevOps assistant with CortexHub."""
    
    # Create MCP server with custom tools
    devops_server = create_devops_server()
    
    # Get CortexHub hooks from adapter
    from cortexhub.adapters.claude_agents import ClaudeAgentsAdapter
    adapter = ClaudeAgentsAdapter(cortex)
    cortexhub_hooks = adapter.create_governance_hooks()
    
    # Configure Claude Agent options
    options = ClaudeAgentOptions(
        system_prompt="""You are a DevOps assistant that helps with:
- Checking service status and health
- Scanning for security vulnerabilities
- Managing deployments (with caution)
- Listing services across environments

Always:
1. Check service status before making changes
2. Run security scans before deployments
3. Confirm high-risk operations with the user
4. Log all actions for audit purposes

For production deployments, note that approval may be required.""",
        
        mcp_servers={"devops": devops_server},
        
        allowed_tools=[
            "mcp__devops__check_security",
            "mcp__devops__deploy_service",
            "mcp__devops__get_service_status",
            "mcp__devops__rollback_deployment",
            "mcp__devops__list_services",
        ],
        
        hooks=cortexhub_hooks,
        permission_mode="default",
    )
    
    # DevOps tasks
    tasks = [
        "List all services in the production environment",
        "Check the status of the api-gateway service",
        "Run a security scan on the /app directory",
        "Deploy the payment-service to staging environment, version 2.1.0",
    ]
    
    print("\n" + "=" * 60)
    print("DevOps Assistant - Claude Agent SDK + CortexHub")
    print("=" * 60)
    print("\n→ CortexHub integration active")
    print("  All tool calls will be logged by CortexHub")
    
    async with ClaudeSDKClient(options=options) as client:
        for i, task in enumerate(tasks, 1):
            print(f"\n{'=' * 60}")
            print(f"TASK {i}: {task}")
            print("=" * 60)

            attempts = 0
            while True:
                try:
                    await client.query(task)
                    
                    async for message in client.receive_response():
                        if isinstance(message, AssistantMessage):
                            for block in message.content:
                                if isinstance(block, TextBlock):
                                    print(f"\nAssistant: {block.text}")
                                elif isinstance(block, ToolUseBlock):
                                    print(f"\n🔧 Using tool: {block.name}")
                                    print(f"   Input: {block.input}")
                        
                        elif isinstance(message, ResultMessage):
                            if message.is_error:
                                print(f"\n❌ Error: {message.result}")
                            else:
                                print(f"\n✅ Task completed")
                    break
                    
                except cortexhub.PolicyViolationError as e:
                    print(f"\n❌ BLOCKED BY CORTEXHUB")
                    print(f"   Reason: {e}")
                    break
                    
                except cortexhub.ApprovalRequiredError as e:
                    print(f"\n⏸️  APPROVAL REQUIRED")
                    print(f"   Approval ID: {e.approval_id}")
                    print(f"   Tool: {e.tool_name}")
                    print(f"   Reason: {e.reason}")
                    print(f"   Expires: {e.expires_at}")
                    print(f"\n   Decision endpoint: {e.decision_endpoint}")
                    print(f"   Configure a webhook to receive approval.decisioned event")

                    api_key = os.getenv("CORTEXHUB_API_KEY", "")
                    api_url = _get_api_url()
                    if not api_key or not e.approval_id or not api_url:
                        break

                    status, _decision = _wait_for_approval(e.approval_id, api_url, api_key)
                    if status == "approved":
                        attempts += 1
                        if attempts <= 1:
                            print("\nRe-running the task after approval...")
                            continue
                        print("\nApproval received, but max retries reached. Re-run to continue.")
                        break
                    if status in {"denied", "expired"}:
                        print(f"\nApproval {status}. Skipping this task.")
                        break
                    break
    
    print("\n" + "=" * 60)
    print("Session Complete")
    print("=" * 60)
    print("\nCheck your CortexHub dashboard to see:")
    print("- All tool invocations logged")
    print("- Security scan findings")
    print("- Deployment attempts and approvals")
    print("=" * 60)


async def main():
    """Main entry point."""
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("Error: ANTHROPIC_API_KEY required")
        print("Set it in .env or environment")
        return
    
    await run_devops_assistant()


if __name__ == "__main__":
    asyncio.run(main())
