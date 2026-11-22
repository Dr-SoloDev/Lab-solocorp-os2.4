#!/usr/bin/env bash
# setup-copilot-env.sh
# 
# Helper script to set up GitHub environment variables and secrets for Copilot
# Usage: ./scripts/setup-copilot-env.sh [--repo OWNER/REPO]
# 
# This script uses GitHub CLI (gh) to configure the `copilot` environment
# with necessary variables and secrets for SoloCorp OS operations.

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Configuration
REPO="${1#--repo }"
REPO="${REPO#}" # Remove first element if using --repo flag
ENVIRONMENT="copilot"
DRY_RUN=${DRY_RUN:-0}

# Functions
print_header() {
    echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║${NC} $1"
    echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

confirm() {
    local prompt="$1"
    local response
    read -p "$(echo -e ${YELLOW}$prompt${NC})" -n 1 -r response
    echo
    [[ $response =~ ^[Yy]$ ]]
}

check_gh_cli() {
    if ! command -v gh &> /dev/null; then
        print_error "GitHub CLI (gh) is not installed. Install it from: https://cli.github.com"
        exit 1
    fi
    print_success "GitHub CLI found"
}

get_repo() {
    if [[ -z "$REPO" ]]; then
        print_info "Detecting GitHub repository..."
        if git rev-parse --git-dir > /dev/null 2>&1; then
            REPO=$(git remote get-url origin | sed 's/.*:\([^/]*\/[^.]*\).*/\1/' | sed 's|https://github.com/||')
            print_success "Found repository: $REPO"
        else
            print_error "Not a git repository. Please specify: --repo OWNER/REPO"
            exit 1
        fi
    else
        print_success "Using repository: $REPO"
    fi
}

set_variable() {
    local var_name=$1
    local var_value=$2
    local description=$3

    if [[ $DRY_RUN -eq 1 ]]; then
        print_info "[DRY RUN] Would set variable: $var_name = $var_value"
        return
    fi

    print_info "Setting: $var_name"
    if echo "$var_value" | gh variable set "$var_name" --repo "$REPO" --env "$ENVIRONMENT"; then
        print_success "$description"
    else
        print_error "Failed to set $var_name"
        return 1
    fi
}

set_secret() {
    local secret_name=$1
    local secret_value=$2
    local description=$3

    if [[ -z "$secret_value" ]]; then
        print_warning "Skipping $secret_name (empty value)"
        return
    fi

    if [[ $DRY_RUN -eq 1 ]]; then
        print_info "[DRY RUN] Would set secret: $secret_name = [REDACTED]"
        return
    fi

    print_info "Setting: $secret_name"
    if echo "$secret_value" | gh secret set "$secret_name" --repo "$REPO" --env "$ENVIRONMENT"; then
        print_success "$description"
    else
        print_error "Failed to set $secret_name"
        return 1
    fi
}

main() {
    print_header "SoloCorp OS — Copilot Environment Setup"

    check_gh_cli
    get_repo

    print_info "Target Environment: $ENVIRONMENT"
    print_info "Target Repository: $REPO"
    echo

    if [[ $DRY_RUN -eq 1 ]]; then
        print_warning "Running in DRY RUN mode. No changes will be made."
    fi
    echo

    # Confirm before proceeding
    if ! confirm "Continue with setup? (y/n) "; then
        print_info "Setup cancelled."
        exit 0
    fi
    echo

    print_header "Setting Up Variables"

    # Core Configuration
    set_variable "FASTAPI_ENV" "test" "FastAPI environment: test/production"
    set_variable "LOG_LEVEL" "INFO" "Logging level: DEBUG/INFO/WARNING/ERROR"
    set_variable "CENTRAL_BUS_HOST" "http://localhost:8000" "Central Bus endpoint"
    set_variable "SOLANA_NETWORK" "mainnet-beta" "Solana network: devnet/testnet/mainnet-beta"

    echo

    print_header "Setting Up Secrets (Optional)"

    print_info "Leave empty to skip any secrets you don't have"
    echo

    # Optional Secrets
    read -p "$(echo -e ${BLUE}Solana RPC URL${NC}) (leave empty to skip): " SOLANA_RPC
    set_secret "SOLANA_RPC" "$SOLANA_RPC" "Solana RPC endpoint configured"

    read -p "$(echo -e ${BLUE}GitHub Token for Private Repos${NC}) (leave empty to skip): " GH_TOKEN
    set_secret "GH_TOKEN" "$GH_TOKEN" "GitHub token for private repository access"

    echo

    print_header "Verification"

    if [[ $DRY_RUN -ne 1 ]]; then
        print_info "Listing configured variables and secrets:"
        echo
        print_info "Variables:"
        gh variable list --repo "$REPO" --env "$ENVIRONMENT" 2>/dev/null || print_warning "No variables found"
        echo
        print_info "Secrets (names only):"
        gh secret list --repo "$REPO" --env "$ENVIRONMENT" 2>/dev/null || print_warning "No secrets found"
    fi

    echo
    print_success "Setup complete!"
    print_info "Next steps:"
    print_info "1. Go to: https://github.com/$REPO/settings/environments/$ENVIRONMENT"
    print_info "2. Verify all variables and secrets are configured"
    print_info "3. Merge .github/workflows/copilot-setup-steps.yml to default branch"
    print_info "4. Run workflow from Actions tab"
    print_info "5. Check COPILOT-SETUP.md for usage guide"
    echo
}

# Run main function
main "$@"
