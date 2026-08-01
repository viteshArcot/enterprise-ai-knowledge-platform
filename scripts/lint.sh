#!/usr/bin/env bash
# =============================================================================
# lint.sh — Run all linters across the monorepo
# =============================================================================
# Usage:
#   ./scripts/lint.sh           # Check only (no auto-fix)
#   ./scripts/lint.sh --fix     # Auto-fix where possible
# =============================================================================

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FIX_MODE=false

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
BOLD='\033[1m'
RESET='\033[0m'

info()    { echo -e "${BLUE}[INFO]${RESET}  $*"; }
success() { echo -e "${GREEN}[OK]${RESET}    $*"; }
error()   { echo -e "${RED}[ERROR]${RESET} $*"; }

# Parse arguments
for arg in "$@"; do
    [[ "$arg" == "--fix" ]] && FIX_MODE=true
done

echo -e "\n${BOLD}Running linters${RESET} (fix=${FIX_MODE})\n"

ERRORS=0

# ── Backend: Ruff ─────────────────────────────────────────────────────────────
info "Ruff — Python linting..."
cd "$REPO_ROOT/backend"

if [[ "$FIX_MODE" == true ]]; then
    .venv/bin/ruff check . --fix && success "Ruff: passed" || { error "Ruff: failed"; ERRORS=$((ERRORS+1)); }
else
    .venv/bin/ruff check . && success "Ruff: passed" || { error "Ruff: failed"; ERRORS=$((ERRORS+1)); }
fi

# ── Backend: Black ────────────────────────────────────────────────────────────
info "Black — Python formatting..."

if [[ "$FIX_MODE" == true ]]; then
    .venv/bin/black . && success "Black: passed" || { error "Black: failed"; ERRORS=$((ERRORS+1)); }
else
    .venv/bin/black --check . && success "Black: passed" || { error "Black: failed"; ERRORS=$((ERRORS+1)); }
fi

# ── Frontend: oxlint ──────────────────────────────────────────────────────────
info "oxlint — TypeScript/React linting..."
cd "$REPO_ROOT/frontend"

if [[ "$FIX_MODE" == true ]]; then
    npm run lint -- --fix && success "oxlint: passed" || { error "oxlint: failed"; ERRORS=$((ERRORS+1)); }
else
    npm run lint && success "oxlint: passed" || { error "oxlint: failed"; ERRORS=$((ERRORS+1)); }
fi

# ── Frontend: Prettier ────────────────────────────────────────────────────────
info "Prettier — TypeScript/CSS formatting..."

if [[ "$FIX_MODE" == true ]]; then
    npx prettier --write "src/**/*.{ts,tsx,css}" && success "Prettier: passed" || { error "Prettier: failed"; ERRORS=$((ERRORS+1)); }
else
    npx prettier --check "src/**/*.{ts,tsx,css}" && success "Prettier: passed" || { error "Prettier: failed"; ERRORS=$((ERRORS+1)); }
fi

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
if [[ $ERRORS -eq 0 ]]; then
    echo -e "${GREEN}${BOLD}All linters passed.${RESET}"
else
    echo -e "${RED}${BOLD}$ERRORS linter(s) failed.${RESET}"
    exit 1
fi
