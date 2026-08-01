#!/usr/bin/env bash
# =============================================================================
# setup.sh — One-command local development environment setup
# =============================================================================
# Usage: ./scripts/setup.sh
# Prerequisites: Python 3.12+, Node 20+, Docker, pip
# =============================================================================

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
RESET='\033[0m'

# Repo root (script can be called from any directory)
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

info()    { echo -e "${BLUE}[INFO]${RESET}  $*"; }
success() { echo -e "${GREEN}[OK]${RESET}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${RESET}  $*"; }
error()   { echo -e "${RED}[ERROR]${RESET} $*"; exit 1; }

echo -e "\n${BOLD}Enterprise AI Knowledge Platform — Dev Setup${RESET}\n"

# ── Prerequisite checks ───────────────────────────────────────────────────────

command -v python3 >/dev/null 2>&1 || error "Python 3.12+ is required. Install from python.org."
command -v node    >/dev/null 2>&1 || error "Node 20+ is required. Install from nodejs.org."
command -v docker  >/dev/null 2>&1 || error "Docker is required. Install from docker.com."
command -v npm     >/dev/null 2>&1 || error "npm is required (ships with Node.js)."

PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
info "Python version: $PYTHON_VERSION"

NODE_VERSION=$(node --version)
info "Node version:   $NODE_VERSION"

# ── Environment file ──────────────────────────────────────────────────────────

if [[ ! -f "$REPO_ROOT/.env" ]]; then
    info "Creating .env from .env.example..."
    cp "$REPO_ROOT/.env.example" "$REPO_ROOT/.env"
    warn ".env created. Please set SECRET_KEY before starting the backend."
else
    info ".env already exists — skipping."
fi

# ── Backend setup ─────────────────────────────────────────────────────────────

info "Setting up Python virtual environment..."
cd "$REPO_ROOT/backend"

if [[ ! -d ".venv" ]]; then
    python3 -m venv .venv
    success "Virtual environment created at backend/.venv"
else
    info "Virtual environment already exists — skipping creation."
fi

info "Installing backend dependencies (including dev extras)..."
.venv/bin/pip install --upgrade pip --quiet
.venv/bin/pip install -e ".[dev]" --quiet
success "Backend dependencies installed."

# ── Frontend setup ────────────────────────────────────────────────────────────

info "Installing frontend dependencies..."
cd "$REPO_ROOT/frontend"
npm ci --prefer-offline --quiet
success "Frontend dependencies installed."

# ── Summary ───────────────────────────────────────────────────────────────────

echo ""
echo -e "${BOLD}✓ Setup complete!${RESET}"
echo ""
echo "Next steps:"
echo "  1. Edit .env and set a proper SECRET_KEY"
echo "     (run: openssl rand -hex 32)"
echo ""
echo "  2. Start all services with Docker:"
echo "     docker compose up --build"
echo ""
echo "  3. Or start services individually:"
echo "     cd backend && .venv/bin/uvicorn app.main:app --reload"
echo "     cd frontend && npm run dev"
echo ""
echo "  API docs:  http://localhost:8000/api/docs"
echo "  Frontend:  http://localhost:5173"
echo ""
