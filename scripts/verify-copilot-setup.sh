#!/usr/bin/env bash
# verify-copilot-setup.sh
# 
# Verification script for SoloCorp OS Copilot integration
# Usage: ./scripts/verify-copilot-setup.sh
#
# Checks:
# - Workflow file exists
# - Required Python packages can be imported
# - Project structure is intact
# - GitHub environment is configured

# Don't use `set -e` to prevent single check failure from stopping script
# set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

CHECKS_PASSED=0
CHECKS_FAILED=0

print_header() {
    echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║${NC} $1"
    echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
}

check_pass() {
    echo -e "${GREEN}✓${NC} $1"
    ((CHECKS_PASSED++))
}

check_fail() {
    echo -e "${RED}✗${NC} $1"
    ((CHECKS_FAILED++))
}

check_warn() {
    echo -e "${YELLOW}⚠${NC} $1"
}

check_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

main() {
    print_header "SoloCorp OS — Copilot Setup Verification"
    echo

    # 1. Check workflow file
    print_header "1. Workflow Configuration"
    if [[ -f ".github/workflows/copilot-setup-steps.yml" ]]; then
        check_pass "Workflow file exists"
        if grep -q "copilot-setup-steps" ".github/workflows/copilot-setup-steps.yml" 2>/dev/null; then
            check_pass "Workflow job name is correct"
        else
            check_fail "Workflow job name missing"
        fi
    else
        check_fail "Workflow file not found: .github/workflows/copilot-setup-steps.yml"
    fi
    echo

    # 2. Check Documentation
    print_header "2. Documentation Files"
    if [[ -f "COPILOT-SETUP.md" ]]; then
        check_pass "COPILOT-SETUP.md exists"
    else
        check_fail "COPILOT-SETUP.md not found"
    fi

    if [[ -f "README.md" ]]; then
        if grep -q "copilot" "README.md" 2>/dev/null; then
            check_pass "README.md mentions Copilot"
        else
            check_warn "README.md doesn't mention Copilot"
        fi
    else
        check_fail "README.md not found"
    fi

    if [[ -f "COPILOT-INTEGRATION-COMPLETE.md" ]]; then
        check_pass "COPILOT-INTEGRATION-COMPLETE.md exists"
    else
        check_fail "COPILOT-INTEGRATION-COMPLETE.md not found"
    fi
    echo

    # 3. Check Project Structure
    print_header "3. Project Structure"
    if [[ -d "profiles" ]]; then
        check_pass "profiles/ directory exists"
        PROFILE_COUNT=$(find profiles -name "SOUL.md" 2>/dev/null | wc -l)
        if [[ $PROFILE_COUNT -ge 15 ]]; then
            check_pass "Found $PROFILE_COUNT department profiles"
        else
            check_warn "Found only $PROFILE_COUNT profiles (expected 15+)"
        fi
    else
        check_fail "profiles/ directory not found"
    fi

    if [[ -d "skills" ]]; then
        check_pass "skills/ directory exists"
    else
        check_fail "skills/ directory not found"
    fi

    if [[ -d "central_bus" ]]; then
        check_pass "central_bus/ directory exists"
    else
        check_fail "central_bus/ directory not found"
    fi

    if [[ -d "decisions" ]]; then
        check_pass "decisions/ directory exists"
    else
        check_fail "decisions/ directory not found"
    fi
    echo

    # 4. Check Requirements Files
    print_header "4. Dependencies"
    if [[ -f "requirements-api.txt" ]]; then
        check_pass "requirements-api.txt exists"
    else
        check_fail "requirements-api.txt not found"
    fi

    if [[ -f "central_bus/requirements.txt" ]]; then
        check_pass "central_bus/requirements.txt exists"
    else
        check_fail "central_bus/requirements.txt not found"
    fi
    echo

    # 5. Check Helper Scripts
    print_header "5. Helper Scripts"
    if [[ -f "scripts/setup-copilot-env.sh" ]]; then
        if [[ -x "scripts/setup-copilot-env.sh" ]]; then
            check_pass "scripts/setup-copilot-env.sh is executable"
        else
            check_warn "scripts/setup-copilot-env.sh exists but not executable"
        fi
    else
        check_fail "scripts/setup-copilot-env.sh not found"
    fi
    echo

    # 6. Check Git Status
    print_header "6. Git Configuration"
    if git rev-parse --git-dir > /dev/null 2>&1; then
        check_pass "Git repository detected"
        
        DEFAULT_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
        check_pass "On branch: $DEFAULT_BRANCH"
        
        # Check if workflow is staged/committed
        if git ls-files --stage 2>/dev/null | grep -q "copilot-setup-steps.yml"; then
            check_pass "Workflow file is tracked in git"
        else
            check_warn "Workflow file not tracked. Run: git add .github/workflows/copilot-setup-steps.yml"
        fi
    else
        check_fail "Not a git repository"
    fi
    echo

    # 7. Test Python Environment (if available)
    print_header "7. Python Environment"
    if command -v python3 &> /dev/null; then
        check_pass "Python 3 is available"
        
        # Try importing required packages
        if python3 -c "import fastapi" 2>/dev/null; then
            check_pass "FastAPI can be imported"
        else
            check_warn "FastAPI not installed locally (will be installed by Copilot)"
        fi
        
        if python3 -c "import uvicorn" 2>/dev/null; then
            check_pass "uvicorn can be imported"
        else
            check_warn "uvicorn not installed locally (will be installed by Copilot)"
        fi
    else
        check_info "Python 3 not available (Copilot will set it up)"
    fi
    echo

    # 8. GitHub CLI Check
    print_header "8. GitHub Integration"
    if command -v gh &> /dev/null; then
        check_pass "GitHub CLI (gh) is installed"
        
        if gh auth status &>/dev/null 2>&1; then
            check_pass "GitHub CLI is authenticated"
        else
            check_warn "GitHub CLI not authenticated. Run: gh auth login"
        fi
    else
        check_info "GitHub CLI not installed. Optional but recommended for setup-copilot-env.sh"
    fi
    echo

    # Summary
    print_header "Summary"
    TOTAL=$((CHECKS_PASSED + CHECKS_FAILED))
    echo "Results: ${GREEN}$CHECKS_PASSED passed${NC} | ${RED}$CHECKS_FAILED failed${NC} (Total: $TOTAL)"
    echo

    if [[ $CHECKS_FAILED -eq 0 ]]; then
        echo -e "${GREEN}✅ All checks passed! Copilot integration is ready.${NC}"
        echo
        echo "Next steps:"
        echo "  1. Push to GitHub: git push origin main"
        echo "  2. Run workflow: GitHub → Actions → Copilot Setup Steps → Run workflow"
        echo "  3. Use Copilot: Ask your first question to Copilot cloud agent"
        echo
        return 0
    else
        echo -e "${YELLOW}⚠ Some checks failed or warnings detected.${NC}"
        echo
        echo "Next steps:"
        echo "  1. Fix any failed checks above"
        echo "  2. Re-run this script: ./scripts/verify-copilot-setup.sh"
        echo "  3. Push to GitHub and test workflow"
        echo
        return 1
    fi
}

# Run verification
main "$@"
