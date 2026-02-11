#!/bin/bash

# UnrealityTV PR Creation Helper
# Creates a PR from current branch to main

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}UnrealityTV PR Creator${NC}"
echo "======================="
echo ""

# Check if on main (shouldn't be)
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "$CURRENT_BRANCH" = "main" ]; then
    echo -e "${RED}❌ Cannot create PR from main branch${NC}"
    echo "Create a feature branch first:"
    echo "  git checkout -b feature/my-feature"
    exit 1
fi

# Check if branch exists on remote
git fetch origin --quiet
if ! git rev-parse origin/$CURRENT_BRANCH &> /dev/null; then
    echo -e "${YELLOW}Branch not on remote. Pushing...${NC}"
    git push -u origin $CURRENT_BRANCH
    echo -e "${GREEN}✓ Branch pushed${NC}"
else
    echo -e "${GREEN}✓ Branch exists on remote${NC}"
fi

echo ""
echo -e "${BLUE}Running local checks before PR...${NC}"

# Check for uncommitted changes
if ! git diff-index --quiet HEAD --; then
    echo -e "${RED}❌ Uncommitted changes detected${NC}"
    echo "Commit or stash changes first"
    git status
    exit 1
fi

# Run tests
echo "Running tests..."
if pytest tests/ -q 2>/dev/null; then
    echo -e "${GREEN}✓ Tests passed${NC}"
else
    echo -e "${RED}❌ Tests failed${NC}"
    echo "Fix test failures before creating PR"
    pytest tests/ -v
    exit 1
fi

# Run linting
echo "Checking code style..."
if ruff check src/ tests/ > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Code style OK${NC}"
else
    echo -e "${RED}❌ Linting errors${NC}"
    echo "Run: ruff check --fix src/ tests/"
    exit 1
fi

echo ""
echo -e "${BLUE}PR Details:${NC}"
echo "Branch: $CURRENT_BRANCH"
echo "Target: main"
echo ""

# Get PR title
read -p "PR Title: " -r PR_TITLE
if [ -z "$PR_TITLE" ]; then
    PR_TITLE="WIP: $CURRENT_BRANCH"
fi

# Get PR description (optional)
echo "Description (optional, press Enter to skip):"
read -p "> " -r PR_DESCRIPTION

# Create PR
echo ""
if command -v gh &> /dev/null; then
    echo -e "${BLUE}Creating PR with GitHub CLI...${NC}"

    if [ -z "$PR_DESCRIPTION" ]; then
        gh pr create \
            --title "$PR_TITLE" \
            --body "Branch: $CURRENT_BRANCH" \
            --head $CURRENT_BRANCH \
            --base main
    else
        gh pr create \
            --title "$PR_TITLE" \
            --body "$PR_DESCRIPTION" \
            --head $CURRENT_BRANCH \
            --base main
    fi

    echo ""
    echo -e "${GREEN}✅ PR created!${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Go to: https://github.com/iainswarts/UnrealityTV/pulls"
    echo "2. Your PR should appear at the top"
    echo "3. Add a description if needed"
    echo "4. Request reviewers"
    echo "5. Wait for CI to pass"
    echo "6. Address any feedback"
else
    echo -e "${YELLOW}⚠️  GitHub CLI (gh) not installed${NC}"
    echo "Install with:"
    echo "  - macOS: brew install gh"
    echo "  - Ubuntu: sudo apt install gh"
    echo "  - Windows: choco install gh"
    echo ""
    echo "Or create PR manually:"
    echo "1. Push branch: git push origin $CURRENT_BRANCH"
    echo "2. Go to: https://github.com/iainswarts/UnrealityTV"
    echo "3. Click 'Compare & pull request' banner"
    echo "4. Fill in title and description"
fi

echo ""
