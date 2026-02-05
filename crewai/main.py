"""CrewAI Financial Operations Team with CortexHub

A multi-agent financial operations system demonstrating:
- Analyst agent that reviews transactions
- Compliance officer that checks regulations
- Processor agent that executes transfers
- Tool tracing via CortexHub

Run:
    uv run python main.py
"""

import os
import json
import time
import urllib.request
from dotenv import load_dotenv

load_dotenv()

# =============================================================================
# CORTEXHUB: 2-line integration
# =============================================================================
import cortexhub
cortex = cortexhub.init("financial-ops", cortexhub.Framework.CREWAI)

# =============================================================================
# CrewAI imports (after CortexHub init to enable auto-patching)
# =============================================================================
from crewai import Agent, Task, Crew, Process
from crewai.tools import tool


# =============================================================================
# Financial Tools
# =============================================================================

@tool
def lookup_account(account_id: str) -> dict:
    """Look up account details by account ID.
    
    Args:
        account_id: The account identifier (e.g., "ACCT-1234")
    
    Returns:
        Account details including holder name, balance, and status
    """
    accounts = {
        "ACCT-1234": {
            "id": "ACCT-1234",
            "holder": "John Smith",
            "ssn_last4": "1234",
            "balance": 50000.00,
            "status": "active",
            "type": "checking",
        },
        "ACCT-5678": {
            "id": "ACCT-5678",
            "holder": "Jane Doe",
            "ssn_last4": "5678",
            "balance": 125000.00,
            "status": "active",
            "type": "savings",
        },
        "ACCT-7890": {
            "id": "ACCT-7890",
            "holder": "Acme Corp",
            "ein": "12-3456789",
            "balance": 500000.00,
            "status": "active",
            "type": "business",
        },
    }
    
    if account_id in accounts:
        return accounts[account_id]
    return {"error": f"Account {account_id} not found"}


@tool
def check_transaction_history(account_id: str, days: int = 30) -> dict:
    """Get recent transaction history for an account.
    
    Args:
        account_id: The account identifier
        days: Number of days of history (default: 30)
    
    Returns:
        List of recent transactions
    """
    # Simulated transaction history
    return {
        "account_id": account_id,
        "period_days": days,
        "transactions": [
            {"date": "2026-01-20", "type": "credit", "amount": 5000.00, "description": "Wire transfer in"},
            {"date": "2026-01-18", "type": "debit", "amount": 1500.00, "description": "Vendor payment"},
            {"date": "2026-01-15", "type": "credit", "amount": 25000.00, "description": "Client payment"},
        ],
        "total_credits": 30000.00,
        "total_debits": 1500.00,
    }


@tool
def verify_compliance(
    source_account: str,
    destination_account: str,
    amount: float,
    purpose: str
) -> dict:
    """Run compliance checks for a proposed transfer.
    
    Args:
        source_account: Source account ID
        destination_account: Destination account ID
        amount: Transfer amount
        purpose: Purpose of the transfer
    
    Returns:
        Compliance check results
    """
    checks = {
        "kyc_verified": True,
        "aml_cleared": True,
        "sanctions_check": "passed",
        "daily_limit_check": amount <= 50000,
        "risk_score": "low" if amount < 10000 else "medium" if amount < 50000 else "high",
    }
    
    all_passed = all([
        checks["kyc_verified"],
        checks["aml_cleared"],
        checks["sanctions_check"] == "passed",
        checks["daily_limit_check"],
    ])
    
    return {
        "status": "passed" if all_passed else "review_required",
        "checks": checks,
        "amount": amount,
        "risk_assessment": checks["risk_score"],
    }


@tool
def initiate_transfer(
    source_account: str,
    destination_account: str,
    amount: float,
    purpose: str,
    reference: str | None = None
) -> dict:
    """Initiate a money transfer between accounts.
    
    Args:
        source_account: Source account ID
        destination_account: Destination account ID
        amount: Transfer amount in dollars
        purpose: Purpose/description of transfer
        reference: Optional reference number
    
    Returns:
        Transfer initiation result with transaction ID
    
    Note: Transfers over $10,000 may require approval.
    """
    import random
    txn_id = f"TXN-{random.randint(100000, 999999)}"
    
    return {
        "success": True,
        "transaction_id": txn_id,
        "source": source_account,
        "destination": destination_account,
        "amount": amount,
        "purpose": purpose,
        "status": "pending" if amount > 10000 else "completed",
        "message": f"Transfer of ${amount:,.2f} initiated",
    }


@tool
def approve_transfer(transaction_id: str, approver_id: str, notes: str = "") -> dict:
    """Approve a pending transfer (for high-value transactions).
    
    Args:
        transaction_id: The transaction ID to approve
        approver_id: ID of the approver
        notes: Optional approval notes
    
    Returns:
        Approval confirmation
    """
    return {
        "success": True,
        "transaction_id": transaction_id,
        "approved_by": approver_id,
        "status": "approved",
        "message": f"Transfer {transaction_id} approved by {approver_id}",
    }


@tool
def flag_suspicious_activity(
    account_id: str,
    reason: str,
    severity: str = "medium"
) -> dict:
    """Flag an account for suspicious activity review.
    
    Args:
        account_id: The account to flag
        reason: Reason for flagging
        severity: Severity level (low, medium, high)
    
    Returns:
        Flag confirmation with case ID
    """
    import random
    case_id = f"SAR-{random.randint(10000, 99999)}"
    
    return {
        "success": True,
        "case_id": case_id,
        "account_id": account_id,
        "reason": reason,
        "severity": severity,
        "status": "under_review",
        "message": f"Suspicious activity report {case_id} created",
    }


# =============================================================================
# Agents
# =============================================================================

financial_analyst = Agent(
    role="Financial Analyst",
    goal="Review transaction requests and analyze account data for risk assessment",
    backstory="""You are an experienced financial analyst with expertise in 
    transaction monitoring and risk assessment. You review accounts and 
    transactions to ensure they meet regulatory requirements and don't 
    show signs of suspicious activity.""",
    tools=[lookup_account, check_transaction_history],
    verbose=True,
)

compliance_officer = Agent(
    role="Compliance Officer",
    goal="Ensure all transactions comply with regulations and internal requirements",
    backstory="""You are a compliance officer responsible for ensuring all 
    financial transactions meet regulatory requirements including KYC, AML, 
    and sanctions screening. You have authority to flag suspicious activity.""",
    tools=[verify_compliance, flag_suspicious_activity],
    verbose=True,
)

transaction_processor = Agent(
    role="Transaction Processor",
    goal="Execute approved financial transactions accurately and securely",
    backstory="""You are a transaction processor responsible for executing 
    financial transfers after they have been reviewed by the analyst and 
    cleared by compliance. You ensure accurate execution and proper documentation.""",
    tools=[initiate_transfer, approve_transfer],
    verbose=True,
)


# =============================================================================
# Tasks
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


def create_analysis_task(source_account: str, destination_account: str, amount: float):
    """Create the analysis task for reviewing a transfer request."""
    return Task(
        description=f"""Review the transfer request:
        - Source Account: {source_account}
        - Destination Account: {destination_account}
        - Amount: ${amount:,.2f}
        
        Steps:
        1. Look up the source account details
        2. Check recent transaction history
        3. Verify the account has sufficient balance
        4. Assess any unusual patterns
        
        Provide a summary of findings and recommendation.""",
        expected_output="Analysis report with recommendation to proceed, review, or reject",
        agent=financial_analyst,
    )


def create_compliance_task(source_account: str, destination_account: str, amount: float, purpose: str):
    """Create the compliance check task."""
    return Task(
        description=f"""Run compliance checks for the proposed transfer:
        - Source: {source_account}
        - Destination: {destination_account}
        - Amount: ${amount:,.2f}
        - Purpose: {purpose}
        
        Steps:
        1. Verify compliance requirements
        2. Assess risk level
        3. If any red flags, flag for suspicious activity review
        
        Provide compliance decision.""",
        expected_output="Compliance decision (approved/rejected) with detailed reasoning",
        agent=compliance_officer,
    )


def create_processing_task(source_account: str, destination_account: str, amount: float, purpose: str):
    """Create the transaction processing task."""
    return Task(
        description=f"""Process the approved transfer:
        - Source: {source_account}
        - Destination: {destination_account}
        - Amount: ${amount:,.2f}
        - Purpose: {purpose}
        
        Steps:
        1. Initiate the transfer
        2. If amount > $10,000, handle approval workflow
        3. Confirm completion
        
        Provide transaction confirmation.""",
        expected_output="Transaction confirmation with transaction ID and status",
        agent=transaction_processor,
    )


# =============================================================================
# Main
# =============================================================================

def process_transfer_request(
    source_account: str,
    destination_account: str,
    amount: float,
    purpose: str,
    *,
    max_retries: int = 1,
):
    """Process a transfer request through the financial operations crew."""
    
    print("\n" + "=" * 60)
    print("TRANSFER REQUEST")
    print("=" * 60)
    print(f"From:    {source_account}")
    print(f"To:      {destination_account}")
    print(f"Amount:  ${amount:,.2f}")
    print(f"Purpose: {purpose}")
    print("=" * 60)
    
    # Create tasks
    analysis_task = create_analysis_task(source_account, destination_account, amount)
    compliance_task = create_compliance_task(source_account, destination_account, amount, purpose)
    processing_task = create_processing_task(source_account, destination_account, amount, purpose)
    
    # Create crew
    crew = Crew(
        agents=[financial_analyst, compliance_officer, transaction_processor],
        tasks=[analysis_task, compliance_task, processing_task],
        process=Process.sequential,  # Tasks run in order
        verbose=True,
    )
    
    attempts = 0
    while True:
        try:
            result = crew.kickoff()
            print("\n" + "=" * 60)
            print("FINAL RESULT")
            print("=" * 60)
            print(result)
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
                if attempts <= max_retries:
                    print("\nRe-running the transfer after approval...")
                    continue
                print("\nApproval received, but max retries reached. Re-run to continue.")
                break
            if status in {"denied", "expired"}:
                print(f"\nApproval {status}. Skipping this transfer.")
                break
            break


def main():
    """Run example financial operations scenarios."""
    
    print("\n" + "=" * 60)
    print("CrewAI Financial Operations Team")
    print("with CortexHub")
    print("=" * 60)
    
    # Scenario 1: Standard transfer (under $10k - should be allowed)
    process_transfer_request(
        source_account="ACCT-1234",
        destination_account="ACCT-7890",
        amount=5000.00,
        purpose="Vendor payment for consulting services"
    )
    
    # Scenario 2: Large transfer (over $10k - may require approval)
    # Uncomment to test a high-value transfer scenario
    # process_transfer_request(
    #     source_account="ACCT-5678",
    #     destination_account="ACCT-7890",
    #     amount=25000.00,
    #     purpose="Investment capital transfer"
    # )
    
    print("\n" + "=" * 60)
    print("Session Complete")
    print("=" * 60)
    print("\nCheck your CortexHub dashboard to see:")
    print("- All tool invocations logged")
    print("- PII detected (account numbers, SSNs)")
    print("- Compliance checks and risk assessments")
    print("- Telemetry recorded")
    print("=" * 60)


if __name__ == "__main__":
    main()
