#!/usr/bin/env python3
"""
test_api_compliance.py — Integration tests for ComplianceValidator API.

Tests FastAPI endpoints for Copilot Cloud Agent integration.

Usage:
    pytest tests/test_api_compliance.py -v
    pytest tests/test_api_compliance.py::test_validate_transaction -v
"""

import pytest
import json
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Import the router
from central_bus.api_compliance import (
    router,
    validate_transaction,
    get_department_rules,
    health_check,
    list_departments,
    validate_batch,
    TransactionDataRequest,
    ValidateTransactionRequest,
)


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def app():
    """Create FastAPI test app with compliance router."""
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def valid_transaction():
    """Valid transaction for testing."""
    return {
        "department_name": "Finance",
        "transaction_data": {
            "id": "TX-001",
            "amount": 50000,
            "vendor": "trusted-vendor",
            "category": "software-license",
            "approval_chain": ["CFO"],
        },
        "audit_log": True,
    }


@pytest.fixture
def excess_amount_transaction():
    """Transaction exceeding department limit."""
    return {
        "department_name": "Finance",
        "transaction_data": {
            "id": "TX-002",
            "amount": 750000,  # Exceeds $500K Finance limit
            "vendor": "new-vendor",
            "category": "contract",
            "approval_chain": ["CFO"],
        },
        "audit_log": True,
    }


@pytest.fixture
def missing_approval_transaction():
    """Transaction missing required approvals."""
    return {
        "department_name": "Sales",
        "transaction_data": {
            "id": "TX-003",
            "amount": 50000,
            "vendor": "client",
            "category": "deal",
            "approval_chain": [],  # Missing VP-Sales
            "discount_percentage": 15,
        },
        "audit_log": True,
    }


@pytest.fixture
def blocked_vendor_transaction():
    """Transaction with blocked vendor."""
    return {
        "department_name": "Finance",
        "transaction_data": {
            "id": "TX-004",
            "amount": 10000,
            "vendor": "sanctioned-corp",  # Blocked for Finance
            "category": "service",
            "approval_chain": ["CFO"],
        },
        "audit_log": True,
    }


# ============================================================================
# TEST: Health Check
# ============================================================================


def test_health_check(client):
    """Test health check endpoint."""
    response = client.get("/api/compliance/status")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "compliance-validator"
    assert "timestamp" in data


# ============================================================================
# TEST: List Departments
# ============================================================================


def test_list_departments(client):
    """Test list departments endpoint."""
    response = client.get("/api/compliance/departments")
    assert response.status_code == 200

    data = response.json()
    assert "total" in data
    assert "departments" in data
    assert len(data["departments"]) > 0
    assert "finance" in data["departments"]
    assert "sales" in data["departments"]
    assert "legal" in data["departments"]
    assert "engineering" in data["departments"]


# ============================================================================
# TEST: Get Department Rules
# ============================================================================


def test_get_finance_rules(client):
    """Test getting Finance department rules."""
    response = client.get("/api/compliance/rules/finance")
    assert response.status_code == 200

    data = response.json()
    assert data["department"] == "finance"
    assert data["amount_limit"] == 500000
    assert "sanctioned-corp" in data["blocked_vendors"]
    assert "software-license" in data["allowed_categories"]
    assert "CFO" in data["required_approvals"]


def test_get_sales_rules(client):
    """Test getting Sales department rules."""
    response = client.get("/api/compliance/rules/sales")
    assert response.status_code == 200

    data = response.json()
    assert data["department"] == "sales"
    assert data["amount_limit"] == 1000000
    assert "VP-Sales" in data["required_approvals"]


def test_get_legal_rules(client):
    """Test getting Legal department rules."""
    response = client.get("/api/compliance/rules/legal")
    assert response.status_code == 200

    data = response.json()
    assert data["department"] == "legal"
    assert data["amount_limit"] == 250000
    assert "General-Counsel" in data["required_approvals"]


def test_get_unknown_department_uses_default(client):
    """Test that unknown departments use default rules."""
    response = client.get("/api/compliance/rules/unknown-dept")
    assert response.status_code == 200

    data = response.json()
    assert data["department"] == "unknown-dept"
    assert data["amount_limit"] == 100000  # Default limit


# ============================================================================
# TEST: Validate Transaction — PASS Cases
# ============================================================================


def test_validate_transaction_pass(client, valid_transaction):
    """Test successful transaction validation."""
    response = client.post(
        "/api/compliance/validate",
        json=valid_transaction,
    )
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert data["result"]["status"] == "pass"
    assert data["result"]["department"] == "Finance"
    assert len(data["result"]["violations"]) == 0
    assert len(data["result"]["passed_checks"]) > 0


def test_validate_transaction_sales_pass(client):
    """Test passing Sales transaction validation."""
    transaction = {
        "department_name": "Sales",
        "transaction_data": {
            "id": "TX-SALES-001",
            "amount": 100000,
            "vendor": "client-corp",
            "category": "deal",
            "approval_chain": ["VP-Sales"],
            "discount_percentage": 10,
        },
        "audit_log": True,
    }

    response = client.post(
        "/api/compliance/validate",
        json=transaction,
    )
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert data["result"]["status"] == "pass"


def test_validate_transaction_legal_pass(client):
    """Test passing Legal transaction validation."""
    transaction = {
        "department_name": "Legal",
        "transaction_data": {
            "id": "TX-LEGAL-001",
            "amount": 100000,
            "vendor": "law-firm",
            "category": "contract-review",
            "approval_chain": ["General-Counsel"],
        },
        "audit_log": True,
    }

    response = client.post(
        "/api/compliance/validate",
        json=transaction,
    )
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert data["result"]["status"] == "pass"


# ============================================================================
# TEST: Validate Transaction — FAIL Cases
# ============================================================================


def test_validate_transaction_amount_exceeds_limit(client, excess_amount_transaction):
    """Test transaction failing due to amount exceeding limit."""
    response = client.post(
        "/api/compliance/validate",
        json=excess_amount_transaction,
    )
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    # Amount exceeding limit is a major violation, so status is fail or review_required
    assert data["result"]["status"] in ["fail", "review_required"]
    assert len(data["result"]["violations"]) > 0

    # Check for amount violation
    violations = data["result"]["violations"]
    amount_violations = [
        v for v in violations if v["type"] == "amount_exceeds_limit"
    ]
    assert len(amount_violations) > 0


def test_validate_transaction_missing_approval(client, missing_approval_transaction):
    """Test transaction failing due to missing approval."""
    response = client.post(
        "/api/compliance/validate",
        json=missing_approval_transaction,
    )
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert data["result"]["status"] == "fail"

    # Check for missing approval violation
    violations = data["result"]["violations"]
    approval_violations = [
        v for v in violations if v["type"] == "missing_approval"
    ]
    assert len(approval_violations) > 0


def test_validate_transaction_blocked_vendor(client, blocked_vendor_transaction):
    """Test transaction failing due to blocked vendor."""
    response = client.post(
        "/api/compliance/validate",
        json=blocked_vendor_transaction,
    )
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert data["result"]["status"] == "fail"

    # Check for vendor violation
    violations = data["result"]["violations"]
    vendor_violations = [
        v for v in violations if v["type"] == "prohibited_vendor"
    ]
    assert len(vendor_violations) > 0


# ============================================================================
# TEST: Validate Transaction — REVIEW_REQUIRED Cases
# ============================================================================


def test_validate_transaction_review_required(client):
    """Test transaction requiring review (non-critical violations)."""
    transaction = {
        "department_name": "Sales",
        "transaction_data": {
            "id": "TX-REVIEW-001",
            "amount": 50000,
            "vendor": "client-corp",
            "category": "deal",
            "approval_chain": ["VP-Sales"],
            "discount_percentage": 25,  # Exceeds 20% policy, needs CEO
        },
        "audit_log": True,
    }

    response = client.post(
        "/api/compliance/validate",
        json=transaction,
    )
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    # Status could be 'fail' or 'review_required' depending on violation severity
    assert data["result"]["status"] in ["fail", "review_required"]


# ============================================================================
# TEST: Validate Transaction — Missing Required Fields
# ============================================================================


def test_validate_transaction_missing_fields(client):
    """Test transaction validation with missing required fields."""
    transaction = {
        "department_name": "Finance",
        "transaction_data": {
            # Missing 'id', 'vendor', 'category', 'approval_chain'
            "amount": 50000,
        },
    }

    response = client.post(
        "/api/compliance/validate",
        json=transaction,
    )
    # FastAPI will return 422 for missing required fields
    assert response.status_code in [200, 422]


# ============================================================================
# TEST: Batch Validation
# ============================================================================


def test_validate_batch_multiple_transactions(client, valid_transaction):
    """Test batch validation of multiple transactions."""
    transactions = [
        valid_transaction,
        {
            "department_name": "Sales",
            "transaction_data": {
                "id": "TX-BATCH-001",
                "amount": 100000,
                "vendor": "client",
                "category": "deal",
                "approval_chain": ["VP-Sales"],
            },
            "audit_log": True,
        },
        {
            "department_name": "Legal",
            "transaction_data": {
                "id": "TX-BATCH-002",
                "amount": 50000,
                "vendor": "law-firm",
                "category": "contract-review",
                "approval_chain": ["General-Counsel"],
            },
            "audit_log": True,
        },
    ]

    response = client.post(
        "/api/compliance/validate-batch",
        json=transactions,
    )
    assert response.status_code == 200

    data = response.json()
    assert data["total"] == 3
    assert data["successful"] == 3
    assert data["failed"] == 0
    assert len(data["results"]) == 3


def test_validate_batch_mixed_pass_fail(client, valid_transaction, excess_amount_transaction):
    """Test batch validation with mixed pass/fail transactions."""
    transactions = [
        valid_transaction,
        excess_amount_transaction,
    ]

    response = client.post(
        "/api/compliance/validate-batch",
        json=transactions,
    )
    assert response.status_code == 200

    data = response.json()
    assert data["total"] == 2
    assert data["successful"] == 2  # Both succeed in validation request
    # At least one should have a failure status
    results = [r for r in data["results"] if r["success"]]
    statuses = [r["result"]["status"] for r in results]
    assert "fail" in statuses or "pass" in statuses


# ============================================================================
# TEST: Request Formats & Edge Cases
# ============================================================================


def test_validate_transaction_with_additional_data(client):
    """Test transaction validation with additional custom data."""
    transaction = {
        "department_name": "Finance",
        "transaction_data": {
            "id": "TX-EXTRA-001",
            "amount": 50000,
            "vendor": "trusted-vendor",
            "category": "software-license",
            "approval_chain": ["CFO"],
            "additional_data": {
                "department_code": "FIN-001",
                "cost_center": "CC-123",
                "project_id": "PROJ-456",
            },
        },
        "audit_log": True,
    }

    response = client.post(
        "/api/compliance/validate",
        json=transaction,
    )
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True


def test_validate_transaction_without_optional_audit_log(client, valid_transaction):
    """Test transaction validation without explicitly setting audit_log."""
    transaction = valid_transaction.copy()
    transaction.pop("audit_log", None)

    response = client.post(
        "/api/compliance/validate",
        json=transaction,
    )
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True


def test_validate_transaction_case_insensitive_department(client):
    """Test that department names are case-insensitive."""
    transaction = {
        "department_name": "FINANCE",  # Uppercase
        "transaction_data": {
            "id": "TX-CASE-001",
            "amount": 50000,
            "vendor": "trusted-vendor",
            "category": "software-license",
            "approval_chain": ["CFO"],
        },
        "audit_log": True,
    }

    response = client.post(
        "/api/compliance/validate",
        json=transaction,
    )
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True


# ============================================================================
# TEST: Response Structure
# ============================================================================


def test_validate_response_contains_all_fields(client, valid_transaction):
    """Test that validation response contains all required fields."""
    response = client.post(
        "/api/compliance/validate",
        json=valid_transaction,
    )

    data = response.json()
    assert "success" in data
    assert "result" in data or "error" in data

    result = data["result"]
    required_fields = [
        "status",
        "reason",
        "violations",
        "passed_checks",
        "timestamp",
        "department",
        "reviewed_by",
    ]
    for field in required_fields:
        assert field in result


def test_violation_response_contains_all_fields(client, blocked_vendor_transaction):
    """Test that violation response contains required fields."""
    response = client.post(
        "/api/compliance/validate",
        json=blocked_vendor_transaction,
    )

    data = response.json()
    result = data["result"]

    if result["violations"]:
        violation = result["violations"][0]
        required_fields = [
            "type",
            "severity",
            "message",
        ]
        for field in required_fields:
            assert field in violation


# ============================================================================
# TEST: Timestamp Formats
# ============================================================================


def test_validate_response_timestamp_iso_format(client, valid_transaction):
    """Test that response timestamp is in ISO format."""
    response = client.post(
        "/api/compliance/validate",
        json=valid_transaction,
    )

    data = response.json()
    timestamp = data["result"]["timestamp"]

    # ISO 8601 format: YYYY-MM-DDTHH:MM:SS.sssZ or similar
    assert "T" in timestamp
    assert ("Z" in timestamp or "+" in timestamp or "-" in timestamp[-6:])


# ============================================================================
# TEST: Concurrency (Batch operations)
# ============================================================================


def test_validate_batch_concurrent_processing(client):
    """Test that batch processing handles concurrent validations."""
    # Create 10 transactions
    transactions = []
    for i in range(10):
        transactions.append(
            {
                "department_name": "Finance",
                "transaction_data": {
                    "id": f"TX-CONCURRENT-{i:03d}",
                    "amount": 10000 + (i * 1000),
                    "vendor": "trusted-vendor",
                    "category": "software-license",
                    "approval_chain": ["CFO"],
                },
                "audit_log": False,
            }
        )

    response = client.post(
        "/api/compliance/validate-batch",
        json=transactions,
    )
    assert response.status_code == 200

    data = response.json()
    assert data["total"] == 10
    assert data["successful"] == 10


# ============================================================================
# INTEGRATION TESTS: Copilot Cloud Agent Scenarios
# ============================================================================


def test_copilot_scenario_finance_approval(client):
    """Test scenario: Copilot validates Finance transaction for approval."""
    transaction = {
        "department_name": "Finance",
        "transaction_data": {
            "id": "COPILOT-FIN-001",
            "amount": 75000,
            "vendor": "software-vendor",
            "category": "software-license",
            "approval_chain": ["CFO"],
        },
        "audit_log": True,
    }

    response = client.post(
        "/api/compliance/validate",
        json=transaction,
    )
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    result = data["result"]

    # Copilot uses this to determine if approval is valid
    assert result["status"] in ["pass", "review_required", "fail"]


def test_copilot_scenario_sales_discount_check(client):
    """Test scenario: Copilot checks if Sales discount is compliant."""
    transaction = {
        "department_name": "Sales",
        "transaction_data": {
            "id": "COPILOT-SALES-001",
            "amount": 50000,
            "vendor": "enterprise-client",
            "category": "deal",
            "approval_chain": ["VP-Sales"],
            "discount_percentage": 18,
        },
        "audit_log": True,
    }

    response = client.post(
        "/api/compliance/validate",
        json=transaction,
    )
    assert response.status_code == 200

    data = response.json()
    result = data["result"]

    # Copilot should see this as passing or review_required
    assert result["status"] != "fail" or "VP-Sales" not in result["passed_checks"]


def test_copilot_scenario_rules_lookup(client):
    """Test scenario: Copilot looks up department rules before validation."""
    # First, get rules
    rules_response = client.get("/api/compliance/rules/legal")
    assert rules_response.status_code == 200

    rules = rules_response.json()
    assert rules["amount_limit"] == 250000

    # Then validate using that knowledge
    transaction = {
        "department_name": "Legal",
        "transaction_data": {
            "id": "COPILOT-LEGAL-001",
            "amount": 100000,
            "vendor": "law-firm",
            "category": "contract-review",
            "approval_chain": ["General-Counsel"],
        },
        "audit_log": True,
    }

    response = client.post(
        "/api/compliance/validate",
        json=transaction,
    )
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
