from __future__ import annotations

from .models import SupportTaskSpec, TaskDifficulty, TicketSnapshot


def get_task_specs() -> dict[str, SupportTaskSpec]:
    return {
        "refund_routing": SupportTaskSpec(
            task_id="refund_routing",
            name="Refund request triage",
            difficulty=TaskDifficulty.EASY,
            ticket=TicketSnapshot(
                ticket_id="SUP-1024",
                subject="Need refund for accidental renewal",
                customer_name="Ava Patel",
                customer_tier="pro",
                channel="email",
                product="Billing",
                body=(
                    "Hi team, I was charged for an annual renewal yesterday even though I meant to cancel. "
                    "Please refund the payment and confirm when it will hit my card. Order ID 77841."
                ),
                account_age_days=418,
                sentiment="frustrated",
            ),
            required_classification="billing_refund",
            required_priority="high",
            required_assignee="billing-team",
            response_must_include=["sorry", "refund", "24-48 hours"],
            response_must_avoid=["cannot help"],
            required_notes=["order id 77841"],
            closing_required=True,
        ),
        "outage_coordination": SupportTaskSpec(
            task_id="outage_coordination",
            name="Outage escalation and customer update",
            difficulty=TaskDifficulty.MEDIUM,
            ticket=TicketSnapshot(
                ticket_id="SUP-2048",
                subject="Dashboard timing out for APAC users",
                customer_name="Jordan Lee",
                customer_tier="enterprise",
                channel="chat",
                product="Analytics",
                body=(
                    "We are seeing repeated timeouts in the dashboard for APAC accounts after the 02:10 UTC deploy. "
                    "Please escalate and share a customer-facing update with the incident ETA and workaround."
                ),
                account_age_days=913,
                sentiment="urgent",
            ),
            required_classification="incident_status",
            required_priority="urgent",
            required_assignee="oncall-sre",
            response_must_include=["incident", "workaround", "eta"],
            response_must_avoid=["resolved", "all clear"],
            required_notes=["apac", "02:10 utc deploy"],
            required_escalated_to="incident-manager",
            required_followup_days=1,
            closing_required=True,
        ),
        "access_review": SupportTaskSpec(
            task_id="access_review",
            name="Access request with identity verification",
            difficulty=TaskDifficulty.HARD,
            ticket=TicketSnapshot(
                ticket_id="SUP-4096",
                subject="Need admin access restored",
                customer_name="Morgan Chen",
                customer_tier="enterprise",
                channel="email",
                product="Workspace Admin",
                body=(
                    "I lost access after a password reset and need my admin role restored today. "
                    "My account number is 552193 and I can verify the request if needed."
                ),
                account_age_days=1294,
                sentiment="angry",
            ),
            required_classification="account_access",
            required_priority="medium",
            required_assignee="security-review",
            response_must_include=["verify", "identity", "security"],
            response_must_avoid=["account number 552193", "password reset"],
            required_notes=["do not disclose pii", "request verification"],
            required_escalated_to=None,
            required_followup_days=2,
            closing_required=False,
        ),
    }
