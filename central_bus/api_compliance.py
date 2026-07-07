#!/usr/bin/env python3
"""
api_compliance.py — FastAPI endpoint for ComplianceValidator skill.

Exposes ComplianceValidator to Central Bus and external services.
Integrates with Copilot Cloud Agent for automated compliance checking.

Endpoints:
  POST /api/compliance/validate — Validate transaction
  GET /api/compliance/rules/{department} — Get department rules
  GET /api/compliance/status — Health check
"""

from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel, Field
from typing import Optional, List
import logging
import asyncio

from skills.compliance_validator import (
    ComplianceValidator,
    ComplianceStatus,
    ViolationType,
    ComplianceResult,
    ComplianceViolation,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/compliance", tags=["compliance"])

# Global validator instance
_validator: Optional[ComplianceValidator] = None


def get_validator() -> ComplianceValidator:
    """Get or create ComplianceValidator instance."""
    global _validator
    if _validator is None:
        _validator = ComplianceValidator(use_central_bus=True)
        logger.info("ComplianceValidator initialized")
    return _validator


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================


class TransactionDataRequest(BaseModel):
    """Transaction data for compliance validation."""
    id: Optional[str] = Field(None, description="Transaction ID")
    amount: float = Field(..., description="Transaction amount", gt=0)
    vendor: str = Field(..., description="Vendor name", min_length=1)
    category: str = Field(..., description="Transaction category", min_length=1)
    approval_chain: List[str] = Field(..., description="List of approvals")
    discount_percentage: Optional[float] = Field(None, description="Discount percentage")
    additional_data: Optional[dict] = Field(None, description="Additional transaction data")


class ComplianceViolationResponse(BaseModel):
    """Compliance violation response."""
    type: str
    severity: str
    message: str
    remediation: Optional[str] = None


class ComplianceResultResponse(BaseModel):
    """Compliance validation result response."""
    status: str
    reason: str
    violations: List[ComplianceViolationResponse]
    passed_checks: List[str]
    timestamp: str
    transaction_id: Optional[str] = None
    department: str
    reviewed_by: str


class ValidateTransactionRequest(BaseModel):
    """Request to validate transaction."""
    department_name: str = Field(..., description="Department name")
    transaction_data: TransactionDataRequest = Field(..., description="Transaction data")
    audit_log: bool = Field(True, description="Whether to log to audit trail")


class ValidateTransactionResponse(BaseModel):
    """Response from transaction validation."""
    success: bool
    result: Optional[ComplianceResultResponse] = None
    error: Optional[str] = None


class RulesResponse(BaseModel):
    """Department compliance rules response."""
    department: str
    amount_limit: float
    blocked_vendors: List[str]
    allowed_categories: List[str]
    required_approvals: List[str]


# ============================================================================
# ENDPOINTS
# ============================================================================


@router.post(
    "/validate",
    response_model=ValidateTransactionResponse,
    summary="Validate transaction compliance",
    description="Validate a transaction against compliance rules for a department",
)
async def validate_transaction(
    request: ValidateTransactionRequest,
) -> ValidateTransactionResponse:
    """
    Validate a transaction for compliance.

    Args:
        request: Transaction validation request with department and transaction data

    Returns:
        ComplianceResultResponse with validation status, violations, and recommendations

    Example:
        POST /api/compliance/validate
        {
            "department_name": "Finance",
            "transaction_data": {
                "amount": 50000,
                "vendor": "trusted-vendor",
                "category": "software-license",
                "approval_chain": ["CFO"]
            }
        }

        Response:
        {
            "success": true,
            "result": {
                "status": "pass",
                "reason": "PASSED: All compliance checks satisfied",
                "violations": [],
                "passed_checks": [
                    "Required fields present",
                    "Amount $50,000 within department limit",
                    ...
                ],
                "timestamp": "2026-07-07T15:30:00.000Z",
                "department": "Finance"
            }
        }
    """
    try:
        validator = get_validator()

        # Convert request to transaction data
        tx_data = {
            "id": request.transaction_data.id,
            "amount": request.transaction_data.amount,
            "vendor": request.transaction_data.vendor,
            "category": request.transaction_data.category,
            "approval_chain": request.transaction_data.approval_chain,
        }

        # Add optional fields
        if request.transaction_data.discount_percentage is not None:
            tx_data["discount_percentage"] = request.transaction_data.discount_percentage

        if request.transaction_data.additional_data:
            tx_data.update(request.transaction_data.additional_data)

        # Validate
        result = await validator.validate(
            department_name=request.department_name,
            transaction_data=tx_data,
            audit_log=request.audit_log,
        )

        # Convert result to response
        violations_response = [
            ComplianceViolationResponse(
                type=v.type.value,
                severity=v.severity,
                message=v.message,
                remediation=v.remediation,
            )
            for v in result.violations
        ]

        result_response = ComplianceResultResponse(
            status=result.status.value,
            reason=result.reason,
            violations=violations_response,
            passed_checks=result.passed_checks,
            timestamp=result.timestamp,
            transaction_id=result.transaction_id,
            department=result.department,
            reviewed_by=result.reviewed_by,
        )

        logger.info(
            f"Validation completed: {request.department_name} → {result.status.value}"
        )

        return ValidateTransactionResponse(success=True, result=result_response)

    except Exception as e:
        logger.error(f"Validation error: {str(e)}", exc_info=True)
        return ValidateTransactionResponse(
            success=False, error=f"Validation failed: {str(e)}"
        )


@router.get(
    "/rules/{department}",
    response_model=RulesResponse,
    summary="Get department compliance rules",
    description="Retrieve compliance rules for a specific department",
)
async def get_department_rules(department: str) -> RulesResponse:
    """
    Get compliance rules for a department.

    Args:
        department: Department name (finance, sales, legal, engineering, etc.)

    Returns:
        Department compliance rules (amount limit, blocked vendors, etc.)

    Example:
        GET /api/compliance/rules/finance

        Response:
        {
            "department": "finance",
            "amount_limit": 500000,
            "blocked_vendors": ["sanctioned-corp", "high-risk-vendor"],
            "allowed_categories": ["expense", "contract", "software-license", ...],
            "required_approvals": ["CFO"]
        }
    """
    try:
        validator = get_validator()
        dept = department.lower().strip()

        # Get rules (default if unknown)
        rules = validator.rules.get(dept, validator.rules.get("default", {}))

        if not rules:
            raise HTTPException(
                status_code=404, detail=f"Rules not found for department: {department}"
            )

        return RulesResponse(
            department=dept,
            amount_limit=rules.get("amount_limit", 0),
            blocked_vendors=rules.get("blocked_vendors", []),
            allowed_categories=rules.get("allowed_categories", []),
            required_approvals=rules.get("required_approvals", []),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving rules: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error retrieving rules: {str(e)}")


@router.get(
    "/status",
    summary="Health check",
    description="Check if compliance validator is running",
)
async def health_check() -> dict:
    """
    Health check endpoint.

    Returns:
        Status and version information
    """
    return {
        "status": "healthy",
        "service": "compliance-validator",
        "version": "1.0",
        "timestamp": __import__("datetime").datetime.utcnow().isoformat() + "Z",
    }


@router.get(
    "/departments",
    summary="List supported departments",
    description="Get list of departments with configured compliance rules",
)
async def list_departments() -> dict:
    """
    List all supported departments.

    Returns:
        List of departments and their status
    """
    try:
        validator = get_validator()
        departments = list(validator.rules.keys())

        return {
            "total": len(departments),
            "departments": departments,
            "default": "default" in departments,
        }

    except Exception as e:
        logger.error(f"Error listing departments: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Error listing departments: {str(e)}"
        )


@router.post(
    "/validate-batch",
    response_model=dict,
    summary="Validate multiple transactions",
    description="Validate multiple transactions in parallel",
)
async def validate_batch(
    requests: List[ValidateTransactionRequest] = Body(
        ..., description="List of validation requests"
    ),
) -> dict:
    """
    Validate multiple transactions in parallel.

    Args:
        requests: List of transaction validation requests

    Returns:
        Results for each transaction

    Example:
        POST /api/compliance/validate-batch
        [
            {
                "department_name": "Finance",
                "transaction_data": {...}
            },
            {
                "department_name": "Sales",
                "transaction_data": {...}
            }
        ]

        Response:
        {
            "total": 2,
            "successful": 2,
            "failed": 0,
            "results": [...]
        }
    """
    try:
        validator = get_validator()
        tasks = []

        # Create validation tasks
        for req in requests:
            tx_data = {
                "id": req.transaction_data.id,
                "amount": req.transaction_data.amount,
                "vendor": req.transaction_data.vendor,
                "category": req.transaction_data.category,
                "approval_chain": req.transaction_data.approval_chain,
            }

            if req.transaction_data.discount_percentage is not None:
                tx_data["discount_percentage"] = (
                    req.transaction_data.discount_percentage
                )

            if req.transaction_data.additional_data:
                tx_data.update(req.transaction_data.additional_data)

            tasks.append(
                validator.validate(
                    department_name=req.department_name,
                    transaction_data=tx_data,
                    audit_log=req.audit_log,
                )
            )

        # Execute all in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        processed_results = []
        successful = 0
        failed = 0

        for result in results:
            if isinstance(result, Exception):
                processed_results.append(
                    {"success": False, "error": str(result)}
                )
                failed += 1
            else:
                violations_response = [
                    ComplianceViolationResponse(
                        type=v.type.value,
                        severity=v.severity,
                        message=v.message,
                        remediation=v.remediation,
                    )
                    for v in result.violations
                ]

                result_response = ComplianceResultResponse(
                    status=result.status.value,
                    reason=result.reason,
                    violations=violations_response,
                    passed_checks=result.passed_checks,
                    timestamp=result.timestamp,
                    transaction_id=result.transaction_id,
                    department=result.department,
                    reviewed_by=result.reviewed_by,
                )

                processed_results.append(
                    {"success": True, "result": result_response}
                )
                successful += 1

        logger.info(f"Batch validation completed: {successful} success, {failed} failed")

        return {
            "total": len(requests),
            "successful": successful,
            "failed": failed,
            "results": processed_results,
        }

    except Exception as e:
        logger.error(f"Batch validation error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Batch validation failed: {str(e)}"
        )


# ============================================================================
# INTEGRATION WITH COPILOT
# ============================================================================


async def initialize_compliance_api():
    """Initialize compliance API for Copilot Cloud Agent."""
    validator = get_validator()
    logger.info("ComplianceValidator API initialized for Copilot Cloud Agent")


__all__ = [
    "router",
    "validate_transaction",
    "get_department_rules",
    "health_check",
    "list_departments",
    "validate_batch",
    "initialize_compliance_api",
]
