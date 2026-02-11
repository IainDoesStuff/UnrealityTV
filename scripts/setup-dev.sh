#!/bin/bash

# UnrealityTV Developer Setup Script
# This script sets up your local development environment

set -e  # Exit on error

echo "🚀 UnrealityTV Developer Setup"
echo "==============================="
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check Python version
echo -e "${BLUE}Checking Python version...${NC}"
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "✓ Python $PYTHON_VERSION"

if ! python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then
    echo "❌ Python 3.10 or higher required"
    exit 1
fi

# Create virtual environment
echo ""
echo -e "${BLUE}Setting up virtual environment...${NC}"
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment already exists"
fi

# Activate virtual environment
source venv/bin/activate
echo "✓ Virtual environment activated"

# Upgrade pip
echo ""
echo -e "${BLUE}Upgrading pip...${NC}"
python -m pip install --upgrade pip --quiet
echo "✓ pip upgraded"

# Install dependencies
echo ""
echo -e "${BLUE}Installing project dependencies...${NC}"
pip install -e ".[dev]" --quiet
echo "✓ Project installed in editable mode"

# Install pre-commit hooks (optional)
echo ""
echo -e "${BLUE}Setting up pre-commit hooks...${NC}"
if command -v pre-commit &> /dev/null; then
    pre-commit install
    echo "✓ Pre-commit hooks installed"
else
    echo "⚠️  Pre-commit not installed. Installing..."
    pip install pre-commit --quiet
    pre-commit install
    echo "✓ Pre-commit installed and hooks configured"
fi

# Run initial checks
echo ""
echo -e "${BLUE}Running initial quality checks...${NC}"

# Run tests
echo "Running tests..."
pytest tests/ -q
echo "✓ Tests passed"

# Run linting
echo "Running linting..."
ruff check src/ tests/ > /dev/null 2>&1
echo "✓ Linting passed"

# Verify package
echo "Verifying package installation..."
unrealitytv --version > /dev/null
echo "✓ Package works"

# Success
echo ""
echo -e "${GREEN}✅ Developer environment setup complete!${NC}"
echo ""
echo "Next steps:"
echo "1. Read DEVELOPER_WORKFLOW.md for development guidelines"
echo "2. Create a feature branch: git checkout -b feature/my-feature"
echo "3. Make your changes"
echo "4. Run tests: pytest tests/ -v"
echo "5. Check code: ruff check src/ tests/"
echo "6. Push and create a PR"
echo ""
echo -e "${YELLOW}Remember: Never commit directly to main!${NC}"
echo "Always create a PR and let CI/CD verify your changes."
echo ""
