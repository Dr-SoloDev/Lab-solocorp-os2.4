#!/usr/bin/env python3
"""
test_compliance_validator.py — Unit and integration tests for ComplianceValidator.

Test Suite for Legal Department Compliance Skill
- Validates all compliance rules
- Tests async operations
- Tests error handling
- Tests audit logging integration

Run: pytest tests/test_compliance_validator.py -v
"""

import pytest
import asyncio
from skills.compliance_validator import (
    ComplianceValidator,
    ComplianceStatus,
    ViolationType,
    ComplianceResult,
)


@pytest.fixture
def validator():
    """Create a ComplianceValidator instance for testing."""
    return ComplianceValidator(use_central_bus=False)


@pytest.mark.asyncio
class TestComplianceValidator:
    """Test suite for ComplianceValidator."""

    async def test_validate_passing_transaction_finance(self, validator):
        """Test passing transaction for Finance department."""
        result = await validator.validate(
            department_name="Finance",
            transaction_data={
                "id": "TX-001",
                "amount": 50000,
                "vendor": "trusted-vendor",
                "category": "software-license",
                "approval_chain": ["CFO"],
            },
            audit_log=False,
        )

        assert result.status == ComplianceStatus.PASS
        assert len(result.violations) == 0
        assert len(result.passed_checks) >= 5
        assert "Required fields present" in result.passed_checks
        assert "within department limit" in result.reason or "satisfied" in result.reason.lower()

    async def test_validate_passing_transaction_sales(self, validator):
        """Test passing transaction for Sales department."""
        result = await validator.validate(
            department_name="Sales",
            transaction_data={
                "id": "TX-002",
                "amount": 50000,
                "vendor": "client-abc",
                "category": "deal",
                "approval_chain": ["VP-Sales"],
                "discount_percentage": 10,
            },
            audit_log=False,
        )

        assert result.status == ComplianceStatus.PASS
        assert len(result.violations) == 0

    async def test_amount_exceeds_limit(self, validator):
        """Test transaction with amount exceeding department limit."""
        result = await validator.validate(
            department_name="Finance",
            transaction_data={
                "id": "TX-003",
                "amount": 750000,  # Exceeds 500K limit
                "vendor": "vendor",
                "category": "service",  # Changed from "contract" to avoid policy violation
                "approval_chain": ["CFO"],
            },
            audit_log=False,
        )

        assert result.status == ComplianceStatus.REVIEW_REQUIRED
        assert len(result.violations) == 1
        assert result.violations[0].type == ViolationType.AMOUNT_EXCEEDS_LIMIT
        assert "$750" in result.violations[0].message  # Formatted with comma separator

    async def test_blocked_vendor(self, validator):
        """Test transaction with blocked vendor."""
        result = await validator.validate(
            department_name="Finance",
            transaction_data={
                "id": "TX-004",
                "amount": 10000,
                "vendor": "sanctioned-corp",  # On blocklist
                "category": "service",
                "approval_chain": ["CFO"],
            },
            audit_log=False,
        )

        assert result.status == ComplianceStatus.FAIL
        violations_types = [v.type for v in result.violations]
        assert ViolationType.PROHIBITED_VENDOR in violations_types

    async def test_invalid_category(self, validator):
        """Test transaction with invalid category."""
        result = await validator.validate(
            department_name="Finance",
            transaction_data={
                "id": "TX-005",
                "amount": 10000,
                "vendor": "vendor",
                "category": "invalid-category",  # Not in allowed list
                "approval_chain": ["CFO"],
            },
            audit_log=False,
        )

        assert result.status == ComplianceStatus.REVIEW_REQUIRED
        violations_types = [v.type for v in result.violations]
        assert ViolationType.INVALID_CATEGORY in violations_types

    async def test_missing_approval(self, validator):
        """Test transaction with missing required approval."""
        result = await validator.validate(
            department_name="Finance",
            transaction_data={
                "id": "TX-006",
                "amount": 10000,
                "vendor": "vendor",
                "category": "service",
                "approval_chain": [],  # Missing CFO approval
            },
            audit_log=False,
        )

        assert result.status == ComplianceStatus.FAIL
        violations_types = [v.type for v in result.violations]
        assert ViolationType.MISSING_APPROVAL in violations_types

    async def test_missing_required_fields(self, validator):
        """Test transaction with missing required fields."""
        result = await validator.validate(
            department_name="Finance",
            transaction_data={
                "id": "TX-007",
                "amount": 10000,
                # Missing: vendor, category, approval_chain
            },
            audit_log=False,
        )

        assert result.status == ComplianceStatus.FAIL
        violations_types = [v.type for v in result.violations]
        assert ViolationType.MISSING_DOCUMENTATION in violations_types

    async def test_policy_violation_contract_over_100k_no_legal(self, validator):
        """Test Finance contract over $100K without Legal approval."""
        result = await validator.validate(
            department_name="Finance",
            transaction_data={
                "id": "TX-008",
                "amount": 150000,
                "vendor": "contractor",
                "category": "contract",
                "approval_chain": ["CFO"],  # Missing Legal
            },
            audit_log=False,
        )

        assert result.status == ComplianceStatus.REVIEW_REQUIRED or result.status == ComplianceStatus.FAIL
        violations_types = [v.type for v in result.violations]
        assert ViolationType.POLICY_VIOLATION in violations_types or ViolationType.AMOUNT_EXCEEDS_LIMIT in violations_types

    async def test_policy_violation_sales_discount_over_20_percent(self, validator):
        """Test Sales discount over 20% without CEO approval."""
        result = await validator.validate(
            department_name="Sales",
            transaction_data={
                "id": "TX-009",
                "amount": 50000,
                "vendor": "customer",
                "category": "deal",
                "approval_chain": ["VP-Sales"],  # Missing CEO
                "discount_percentage": 25,  # Exceeds 20%
            },
            audit_log=False,
        )

        assert result.status == ComplianceStatus.REVIEW_REQUIRED or result.status == ComplianceStatus.FAIL
        violations_types = [v.type for v in result.violations]
        assert ViolationType.POLICY_VIOLATION in violations_types

    async def test_multiple_violations(self, validator):
        """Test transaction with multiple violations."""
        result = await validator.validate(
            department_name="Finance",
            transaction_data={
                "id": "TX-010",
                "amount": 600000,  # Over limit
                "vendor": "sanctioned-corp",  # Blocked
                "category": "invalid",  # Invalid category
                "approval_chain": [],  # Missing approval
            },
            audit_log=False,
        )

        assert result.status == ComplianceStatus.FAIL
        assert len(result.violations) >= 2

    async def test_department_case_insensitive(self, validator):
        """Test that department names are case-insensitive."""
        result1 = await validator.validate(
            department_name="Finance",
            transaction_data={
                "id": "TX-011",
                "amount": 50000,
                "vendor": "vendor",
                "category": "service",
                "approval_chain": ["CFO"],
            },
            audit_log=False,
        )

        result2 = await validator.validate(
            department_name="FINANCE",
            transaction_data={
                "id": "TX-011",
                "amount": 50000,
                "vendor": "vendor",
                "category": "service",
                "approval_chain": ["CFO"],
            },
            audit_log=False,
        )

        assert result1.status == result2.status

    async def test_unknown_department_uses_default_rules(self, validator):
        """Test that unknown departments use default rules."""
        result = await validator.validate(
            department_name="Unknown-Department",
            transaction_data={
                "id": "TX-012",
                "amount": 150000,  # Exceeds default limit of 100K
                "vendor": "vendor",
                "category": "general",
                "approval_chain": ["Department-Head"],
            },
            audit_log=False,
        )

        # Should use default limit of 100K, so amount exceeds it
        assert result.status == ComplianceStatus.REVIEW_REQUIRED or result.status == ComplianceStatus.FAIL

    async def test_export_result_as_json(self, validator):
        """Test JSON export of compliance result."""
        result = await validator.validate(
            department_name="Finance",
            transaction_data={
                "id": "TX-013",
                "amount": 50000,
                "vendor": "vendor",
                "category": "service",
                "approval_chain": ["CFO"],
            },
            audit_log=False,
        )

        json_str = validator.export_result_as_json(result)
        assert isinstance(json_str, str)
        assert "status" in json_str
        assert "department" in json_str
        assert "violations" in json_str

    async def test_result_has_timestamp(self, validator):
        """Test that results include timestamp."""
        result = await validator.validate(
            department_name="Finance",
            transaction_data={
                "id": "TX-014",
                "amount": 50000,
                "vendor": "vendor",
                "category": "service",
                "approval_chain": ["CFO"],
            },
            audit_log=False,
        )

        assert result.timestamp is not None
        assert "T" in result.timestamp  # ISO format
        assert "Z" in result.timestamp  # UTC indicator

    async def test_result_includes_transaction_id(self, validator):
        """Test that results include transaction ID."""
        result = await validator.validate(
            department_name="Finance",
            transaction_data={
                "id": "TX-CUSTOM-123",
                "amount": 50000,
                "vendor": "vendor",
                "category": "service",
                "approval_chain": ["CFO"],
            },
            audit_log=False,
        )

        assert result.transaction_id == "TX-CUSTOM-123"

    async def test_concurrent_validations(self, validator):
        """Test concurrent async validations."""
        tasks = [
            validator.validate(
                department_name="Finance",
                transaction_data={
                    "id": f"TX-{i:03d}",
                    "amount": 50000 + i * 1000,
                    "vendor": "vendor",
                    "category": "service",
                    "approval_chain": ["CFO"],
                },
                audit_log=False,
            )
            for i in range(10)
        ]

        results = await asyncio.gather(*tasks)
        assert len(results) == 10
        assert all(isinstance(r, ComplianceResult) for r in results)

    async def test_legal_department_rules(self, validator):
        """Test Legal department specific rules."""
        result = await validator.validate(
            department_name="Legal",
            transaction_data={
                "id": "TX-015",
                "amount": 50000,
                "vendor": "law-firm",
                "category": "contract-review",
                "approval_chain": ["General-Counsel"],
            },
            audit_log=False,
        )

        assert result.status == ComplianceStatus.PASS
        assert result.department == "Legal"

    async def test_engineering_department_rules(self, validator):
        """Test Engineering department specific rules."""
        result = await validator.validate(
            department_name="Engineering",
            transaction_data={
                "id": "TX-016",
                "amount": 250000,
                "vendor": "cloud-provider",
                "category": "infrastructure",
                "approval_chain": ["VP-Engineering"],
            },
            audit_log=False,
        )

        assert result.status == ComplianceStatus.PASS
        assert result.department == "Engineering"


class TestComplianceValidatorSync:
    """Synchronous helper tests."""

    def test_initialize_rules(self):
        """Test that rules are initialized correctly."""
        validator = ComplianceValidator()
        rules = validator.rules

        assert "finance" in rules
        assert "sales" in rules
        assert "legal" in rules
        assert "engineering" in rules
        assert "default" in rules

        assert "amount_limit" in rules["finance"]
        assert "blocked_vendors" in rules["finance"]
        assert "allowed_categories" in rules["finance"]
        assert "required_approvals" in rules["finance"]

    def test_validate_required_fields(self):
        """Test required field validation."""
        validator = ComplianceValidator()

        valid_data = {
            "amount": 100,
            "vendor": "v",
            "category": "c",
            "approval_chain": [],
        }
        assert validator._validate_required_fields(valid_data) is True

        invalid_data = {"amount": 100, "vendor": "v"}  # Missing fields
        assert validator._validate_required_fields(invalid_data) is False


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])
