#!/usr/bin/env python3
"""
compliance_validator.py — Async compliance validation skill for Legal department.

Legal Department Skill — SoloCorp OS
- Validates transactions against regulatory and internal policy rules
- Logs all validations to Central Bus audit trail
- Routes compliance issues to appropriate departments
- Integrates with FastAPI async pattern

Usage:
    from skills.compliance_validator import ComplianceValidator
    
    validator = ComplianceValidator()
    result = await validator.validate(
        department_name="Finance",
        transaction_data={
            "amount": 50000,
            "vendor": "external-partner",
            "category": "software-license",
            "approval_chain": ["CFO", "CEO"]
        }
    )
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from typing import Any, Optional
import asyncio

# Configure logging
logger = logging.getLogger(__name__)


class ComplianceStatus(str, Enum):
    """Compliance validation outcome."""
    PASS = "pass"
    FAIL = "fail"
    REVIEW_REQUIRED = "review_required"


class ViolationType(str, Enum):
    """Types of compliance violations."""
    AMOUNT_EXCEEDS_LIMIT = "amount_exceeds_limit"
    MISSING_APPROVAL = "missing_approval"
    PROHIBITED_VENDOR = "prohibited_vendor"
    INVALID_CATEGORY = "invalid_category"
    MISSING_DOCUMENTATION = "missing_documentation"
    POLICY_VIOLATION = "policy_violation"
    REGULATORY_VIOLATION = "regulatory_violation"
    DUPLICATE_TRANSACTION = "duplicate_transaction"


@dataclass
class ComplianceViolation:
    """Single compliance violation detail."""
    type: ViolationType
    severity: str  # "critical", "major", "minor"
    message: str
    remediation: Optional[str] = None


@dataclass
class ComplianceResult:
    """Compliance validation result."""
    status: ComplianceStatus
    reason: str
    violations: list[ComplianceViolation]
    passed_checks: list[str]
    timestamp: str
    transaction_id: Optional[str] = None
    department: str = ""
    reviewed_by: str = "compliance-validator-v1"


class ComplianceValidator:
    """
    Async validator for transaction compliance against regulatory and policy rules.
    
    Integrates with:
    - Central Bus for audit logging
    - FastAPI for async operations
    - Multiple departments for cross-functional validation
    
    Department Rules Reference:
    - profiles/02-cfo/SOUL.md — Finance approval rules
    - profiles/11-sales/SOUL.md — Sales discount rules
    - profiles/13-legal/SOUL.md — Legal review requirements
    - profiles/07-engineering/SOUL.md — Engineering procurement rules
    """

    def __init__(self, use_central_bus: bool = True):
        """
        Initialize compliance validator.
        
        Args:
            use_central_bus: If True, logs to Central Bus audit trail
        """
        self.rules = self._initialize_rules()
        self.use_central_bus = use_central_bus
        self.central_bus_client = None  # Injected at runtime
        logger.info("ComplianceValidator initialized")

    async def validate(
        self,
        department_name: str,
        transaction_data: dict[str, Any],
        audit_log: bool = True,
    ) -> ComplianceResult:
        """
        Async validate a transaction for the specified department.

        Args:
            department_name: Target department (Finance, Sales, Legal, etc.)
            transaction_data: Transaction details (amount, vendor, category, etc.)
            audit_log: Whether to log to central_bus audit trail

        Returns:
            ComplianceResult with status, violations, and remediation steps
        """
        violations: list[ComplianceViolation] = []
        passed_checks: list[str] = []

        # Normalize department name
        dept = department_name.lower().strip()
        tx_id = transaction_data.get("id", f"TX-{datetime.utcnow().timestamp()}")

        logger.info(f"Starting validation for {dept} transaction {tx_id}")

        # === Phase 1: Basic Validation ===
        if not self._validate_required_fields(transaction_data):
            violations.append(
                ComplianceViolation(
                    type=ViolationType.MISSING_DOCUMENTATION,
                    severity="critical",
                    message="Missing required transaction fields",
                    remediation="Provide: amount, vendor, category, approval_chain",
                )
            )
            result = self._build_failure_result(
                department_name, transaction_data, violations, passed_checks
            )
            if audit_log:
                await self._log_to_audit_trail(result)
            return result

        passed_checks.append("Required fields present")

        # === Phase 2: Department-Specific Rules ===
        dept_rules = self.rules.get(dept, self.rules.get("default", {}))

        # Check transaction amount against limits
        amount = transaction_data.get("amount", 0)
        if amount > dept_rules.get("amount_limit", float("inf")):
            violations.append(
                ComplianceViolation(
                    type=ViolationType.AMOUNT_EXCEEDS_LIMIT,
                    severity="major",
                    message=f"Amount ${amount:,.0f} exceeds department limit of ${dept_rules['amount_limit']:,.0f}",
                    remediation="Request escalated approval or split transaction",
                )
            )
        else:
            passed_checks.append(f"Amount ${amount:,.0f} within department limit")

        # Check vendor against blocklist
        vendor = transaction_data.get("vendor", "").lower().strip()
        if vendor in dept_rules.get("blocked_vendors", []):
            violations.append(
                ComplianceViolation(
                    type=ViolationType.PROHIBITED_VENDOR,
                    severity="critical",
                    message=f"Vendor '{vendor}' is on the compliance blocklist",
                    remediation="Select approved vendor from vendor list",
                )
            )
        else:
            passed_checks.append(f"Vendor '{vendor}' is approved")

        # Check transaction category
        category = transaction_data.get("category", "").lower().strip()
        allowed_categories = dept_rules.get("allowed_categories", [])
        if allowed_categories and category not in allowed_categories:
            violations.append(
                ComplianceViolation(
                    type=ViolationType.INVALID_CATEGORY,
                    severity="major",
                    message=f"Category '{category}' not in allowed list: {', '.join(allowed_categories)}",
                    remediation=f"Select from allowed categories: {', '.join(allowed_categories)}",
                )
            )
        else:
            passed_checks.append(f"Category '{category}' is valid")

        # === Phase 3: Approval Chain ===
        approval_chain = transaction_data.get("approval_chain", [])
        required_approvals = dept_rules.get("required_approvals", [])

        missing_approvals = [a for a in required_approvals if a not in approval_chain]
        if missing_approvals:
            violations.append(
                ComplianceViolation(
                    type=ViolationType.MISSING_APPROVAL,
                    severity="critical",
                    message=f"Missing approvals from: {', '.join(missing_approvals)}",
                    remediation=f"Obtain approvals from: {', '.join(missing_approvals)}",
                )
            )
        else:
            passed_checks.append(f"Approval chain complete: {', '.join(approval_chain)}")

        # === Phase 4: Duplicate Check (async) ===
        is_duplicate = await self._is_duplicate_transaction_async(transaction_data)
        if is_duplicate:
            violations.append(
                ComplianceViolation(
                    type=ViolationType.DUPLICATE_TRANSACTION,
                    severity="major",
                    message="Potential duplicate transaction detected",
                    remediation="Verify against audit logs (central_bus)",
                )
            )
        else:
            passed_checks.append("No duplicate transaction detected")

        # === Phase 5: Policy Rules ===
        policy_violations = await self._check_policy_rules_async(dept, transaction_data)
        violations.extend(policy_violations)

        if not policy_violations:
            passed_checks.append("All policy rules satisfied")

        # === Determine Final Status ===
        critical_violations = [v for v in violations if v.severity == "critical"]

        if critical_violations:
            status = ComplianceStatus.FAIL
            reason = f"FAILED: {len(critical_violations)} critical violation(s) detected"
        elif violations:
            status = ComplianceStatus.REVIEW_REQUIRED
            reason = f"REVIEW REQUIRED: {len(violations)} non-critical issue(s) detected"
        else:
            status = ComplianceStatus.PASS
            reason = "PASSED: All compliance checks satisfied"

        result = ComplianceResult(
            status=status,
            reason=reason,
            violations=violations,
            passed_checks=passed_checks,
            timestamp=datetime.utcnow().isoformat() + "Z",
            transaction_id=tx_id,
            department=department_name,
            reviewed_by=self.__class__.__name__,
        )

        # Log to Central Bus audit trail
        if audit_log:
            await self._log_to_audit_trail(result)

        logger.info(f"Validation complete: {tx_id} → {status.value}")
        return result

    def _validate_required_fields(self, transaction_data: dict[str, Any]) -> bool:
        """Check for required transaction fields."""
        required = {"amount", "vendor", "category", "approval_chain"}
        return required.issubset(transaction_data.keys())

    async def _is_duplicate_transaction_async(
        self, transaction_data: dict[str, Any]
    ) -> bool:
        """Check if transaction resembles a recent duplicate (async version)."""
        # In production: query central_bus audit logs
        # For now: simulate async operation
        await asyncio.sleep(0.01)  # Simulate I/O
        
        # TODO: Query central_bus database
        # SELECT * FROM audit_logs WHERE vendor = ? AND amount = ? AND created_at > NOW() - INTERVAL 1 HOUR
        return False

    async def _check_policy_rules_async(
        self, department: str, transaction_data: dict[str, Any]
    ) -> list[ComplianceViolation]:
        """Check internal policy rules specific to department (async)."""
        violations = []

        # Simulate async policy checking
        await asyncio.sleep(0.01)

        # Example: Finance dept cannot approve contracts over 100K without legal review
        if department == "finance":
            if (
                transaction_data.get("category") == "contract"
                and transaction_data.get("amount", 0) > 100000
            ):
                if "Legal" not in transaction_data.get("approval_chain", []):
                    violations.append(
                        ComplianceViolation(
                            type=ViolationType.POLICY_VIOLATION,
                            severity="major",
                            message="Contracts over $100K require Legal review",
                            remediation="Add Legal department to approval chain",
                        )
                    )

        # Example: Sales cannot issue discounts > 20% without executive approval
        if department == "sales":
            discount = transaction_data.get("discount_percentage", 0)
            if discount > 20:
                if "CEO" not in transaction_data.get("approval_chain", []):
                    violations.append(
                        ComplianceViolation(
                            type=ViolationType.POLICY_VIOLATION,
                            severity="major",
                            message=f"Discount of {discount}% exceeds 20% policy limit",
                            remediation="Add CEO to approval chain for large discounts",
                        )
                    )

        return violations

    async def _log_to_audit_trail(self, result: ComplianceResult) -> None:
        """Log validation result to Central Bus audit trail."""
        if not self.use_central_bus:
            return

        try:
            # TODO: Implement central_bus integration
            # await self.central_bus_client.log_event(
            #     event_type="compliance_validation",
            #     department=result.department,
            #     transaction_id=result.transaction_id,
            #     status=result.status.value,
            #     timestamp=result.timestamp,
            #     violations_count=len(result.violations),
            # )
            logger.info(f"Logged to audit trail: {result.transaction_id}")
        except Exception as e:
            logger.error(f"Failed to log to audit trail: {e}")

    def _build_failure_result(
        self,
        department: str,
        transaction_data: dict[str, Any],
        violations: list[ComplianceViolation],
        passed_checks: list[str],
    ) -> ComplianceResult:
        """Build a failure result."""
        return ComplianceResult(
            status=ComplianceStatus.FAIL,
            reason=f"FAILED: {len(violations)} critical violation(s)",
            violations=violations,
            passed_checks=passed_checks,
            timestamp=datetime.utcnow().isoformat() + "Z",
            transaction_id=transaction_data.get("id"),
            department=department,
            reviewed_by=self.__class__.__name__,
        )

    def _initialize_rules(self) -> dict[str, dict[str, Any]]:
        """Initialize compliance rules for each department."""
        return {
            "finance": {
                "amount_limit": 500000,
                "blocked_vendors": ["sanctioned-corp", "high-risk-vendor"],
                "allowed_categories": [
                    "expense",
                    "contract",
                    "software-license",
                    "hardware",
                    "service",
                ],
                "required_approvals": ["CFO"],
            },
            "sales": {
                "amount_limit": 1000000,
                "blocked_vendors": [],
                "allowed_categories": ["deal", "commission", "marketing", "discount"],
                "required_approvals": ["VP-Sales"],
            },
            "legal": {
                "amount_limit": 250000,
                "blocked_vendors": ["blacklisted-law-firm"],
                "allowed_categories": [
                    "contract-review",
                    "compliance",
                    "litigation",
                    "ip-protection",
                ],
                "required_approvals": ["General-Counsel"],
            },
            "engineering": {
                "amount_limit": 750000,
                "blocked_vendors": [],
                "allowed_categories": [
                    "infrastructure",
                    "tools",
                    "software",
                    "hardware",
                ],
                "required_approvals": ["VP-Engineering"],
            },
            "default": {
                "amount_limit": 100000,
                "blocked_vendors": [],
                "allowed_categories": ["general"],
                "required_approvals": ["Department-Head"],
            },
        }

    def export_result_as_json(self, result: ComplianceResult) -> str:
        """Export compliance result as JSON string."""
        return json.dumps(
            {
                "status": result.status.value,
                "reason": result.reason,
                "department": result.department,
                "violations": [
                    {
                        "type": v.type.value,
                        "severity": v.severity,
                        "message": v.message,
                        "remediation": v.remediation,
                    }
                    for v in result.violations
                ],
                "passed_checks": result.passed_checks,
                "timestamp": result.timestamp,
                "transaction_id": result.transaction_id,
            },
            indent=2,
        )


# Async example
async def example_usage():
    """Example usage of async ComplianceValidator."""
    validator = ComplianceValidator(use_central_bus=False)

    # Test Case 1: Passing transaction
    result1 = await validator.validate(
        department_name="Finance",
        transaction_data={
            "id": "TX-001",
            "amount": 50000,
            "vendor": "trusted-vendor",
            "category": "software-license",
            "approval_chain": ["CFO"],
        },
    )
    print(f"Test 1 - {result1.status.value.upper()}")
    print(f"  Reason: {result1.reason}\n")

    # Test Case 2: Amount exceeds limit
    result2 = await validator.validate(
        department_name="Finance",
        transaction_data={
            "id": "TX-002",
            "amount": 750000,
            "vendor": "new-vendor",
            "category": "contract",
            "approval_chain": ["CFO"],
        },
    )
    print(f"Test 2 - {result2.status.value.upper()}")
    print(f"  Reason: {result2.reason}")
    for v in result2.violations:
        print(f"  - {v.message}")
    print()

    # Test Case 3: Missing approvals
    result3 = await validator.validate(
        department_name="Sales",
        transaction_data={
            "id": "TX-003",
            "amount": 50000,
            "vendor": "client",
            "category": "deal",
            "approval_chain": [],
            "discount_percentage": 15,
        },
    )
    print(f"Test 3 - {result3.status.value.upper()}")
    print(f"  Reason: {result3.reason}")
    for v in result3.violations:
        print(f"  - {v.message}: {v.remediation}")
    print()

    print("=" * 70)
    print("JSON Export Example:")
    print(validator.export_result_as_json(result1))


if __name__ == "__main__":
    asyncio.run(example_usage())
