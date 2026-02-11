# Branch Protection & PR Workflow Setup

This guide explains how to set up GitHub branch protection rules to enforce a PR-based workflow where all changes require CI to pass before merging.

## Why Branch Protection?

Branch protection ensures:
- ✅ **No direct commits to main** - All changes go through PRs
- ✅ **CI must pass** - Tests, linting, and security checks required
- ✅ **Code review required** - At least one approval before merge
- ✅ **Up-to-date with main** - PR must be rebased before merging
- ✅ **No force pushes** - Prevents accidental history rewrites

## Setup Instructions

### Option 1: Via GitHub Web UI (Easiest)

1. **Go to repository settings**
   - Navigate to: https://github.com/iainswarts/UnrealityTV/settings/branches

2. **Add branch protection rule for `main`**
   - Click "Add rule"
   - Pattern: `main`

3. **Configure protections**

   **Status Checks:**
   - ✅ "Require status checks to pass before merging"
   - ✅ Select these required checks:
     - `test-and-lint (3.10)`
     - `test-and-lint (3.11)`
     - `test-and-lint (3.12)`
     - `package-check`
   - ✅ "Require branches to be up to date before merging"

   **Pull Request Reviews:**
   - ✅ "Require a pull request before merging"
   - ✅ "Require approvals": Set to 1
   - ✅ "Require review from Code Owners"
   - ✅ "Require status checks to pass before merging"
   - ✅ "Include administrators"

   **Other:**
   - ✅ "Restrict who can push to matching branches" (optional)
   - ✅ "Allow auto-merge"
   - ✅ "Allow force pushes" - **UNCHECKED** (protection)

4. **Save**
   - Click "Create" button

### Option 2: Via GitHub CLI

If you have `gh` CLI installed:

```bash
# Install gh CLI if needed:
# macOS: brew install gh
# Ubuntu: sudo apt install gh
# Windows: choco install gh

# Authenticate
gh auth login

# Set branch protection
gh api repos/iainswarts/UnrealityTV/branches/main/protection \
  -X PUT \
  -f required_pull_request_reviews='{"required_approving_review_count":1,"dismiss_stale_reviews":true}' \
  -f required_status_checks='{"strict":true,"contexts":["test-and-lint (3.10)","test-and-lint (3.11)","test-and-lint (3.12)","package-check"]}' \
  -f enforce_admins=true \
  -f allow_force_pushes=false \
  -f allow_deletions=false
```

### Option 3: Via Terraform/Infrastructure as Code

See section below for IaC setup.

## Development Workflow

### Standard PR Workflow

1. **Create feature branch** (never commit to main)
   ```bash
   git checkout main
   git pull origin main
   git checkout -b feature/my-feature
   ```

2. **Make changes and commit**
   ```bash
   # Make your changes
   git add src/unrealitytv/new_file.py
   git commit -m "Add new feature"

   # Test locally
   pytest tests/ -v
   ruff check src/ tests/
   ```

3. **Push to remote**
   ```bash
   git push origin feature/my-feature
   ```

4. **Create Pull Request**
   ```bash
   # Via GitHub web UI, or:
   gh pr create --title "Add new feature" --body "Description"
   ```

5. **Wait for CI to pass**
   - GitHub Actions will automatically run
   - Check status in PR "Checks" tab
   - All checks must be green ✅

6. **Request review**
   - Add reviewers via PR interface
   - Wait for approval

7. **Merge**
   - Once approved and CI passes, click "Squash and merge" or "Merge"
   - Delete branch after merge

### Quick PR Creation Script

Create `scripts/create-pr.sh`:

```bash
#!/bin/bash
set -e

# Check if on main
BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "$BRANCH" = "main" ]; then
    echo "❌ Cannot create PR from main branch"
    exit 1
fi

# Ensure branch is pushed
echo "📤 Pushing branch..."
git push -u origin $(git rev-parse --abbrev-ref HEAD)

# Get branch name and create PR
BRANCH_NAME=$(git rev-parse --abbrev-ref HEAD)
echo "📝 Creating PR for $BRANCH_NAME..."

if command -v gh &> /dev/null; then
    gh pr create --title "WIP: $BRANCH_NAME" --body "Awaiting description" --draft
else
    echo "ℹ️  Install 'gh' CLI for automated PR creation"
    echo "   macOS: brew install gh"
    echo "   Ubuntu: sudo apt install gh"
fi
```

Use it:
```bash
chmod +x scripts/create-pr.sh
./scripts/create-pr.sh
```

## Checking CI Status

### In GitHub UI
1. Go to PR page
2. Click "Checks" tab at top
3. See all job statuses
4. Click job to see details

### From Command Line
```bash
# List PRs
gh pr list

# View specific PR checks
gh pr checks <PR_NUMBER>

# View workflow runs
gh run list

# View specific run details
gh run view <RUN_ID>
```

## Common Scenarios

### "CI Failed - What do I do?"

1. **Check the error**
   - Go to PR → Checks tab
   - Click failed job for details

2. **Fix locally**
   ```bash
   # Make fixes
   git add .
   git commit -m "Fix CI issues"
   git push origin feature/my-feature
   ```

3. **CI automatically re-runs**
   - GitHub re-runs all checks on new commits
   - No need to manually trigger

### "Merge Button is Disabled"

**Possible reasons:**
- ❌ CI hasn't finished - Wait for checks to complete
- ❌ CI failed - Fix the issues
- ❌ No approvals - Request a reviewer and wait for approval
- ❌ Branch is outdated - Update with main branch:
  ```bash
  git fetch origin
  git rebase origin/main
  git push origin feature/my-feature --force
  ```

### "I accidentally committed to main"

1. **Identify the commit**
   ```bash
   git log --oneline main | head -5
   ```

2. **Create PR from main to feature branch**
   ```bash
   git checkout -b hotfix/fix-direct-commit
   git reset --soft main~1  # Undo commit
   git stash
   git checkout main
   git reset --hard origin/main
   git checkout -b feature/proper-branch
   git stash pop
   git commit -m "Restore changes"
   git push origin feature/proper-branch
   ```

3. **Request PR review** as normal

## Configuring Code Owners

Add file: `.github/CODEOWNERS`

```
# Default owners for everything
* @iainswarts

# Specific owners for paths
/src/unrealitytv/cli.py @iainswarts
/tests/ @iainswarts
/.github/ @iainswarts
```

When someone creates a PR, code owners are automatically requested for review.

## Auto-merge Configuration

You can enable auto-merge to automatically merge PRs once all requirements are met:

1. In PR, click "Enable auto-merge"
2. Choose merge method:
   - **Squash and merge** (recommended for this project)
   - Merge commit
   - Rebase and merge
3. PR merges automatically when:
   - ✅ CI passes
   - ✅ Review approved
   - ✅ Branch is up-to-date

## CI Status Badge

Add to `README.md`:

```markdown
[![CI Status](https://github.com/iainswarts/UnrealityTV/actions/workflows/ci.yml/badge.svg)](https://github.com/iainswarts/UnrealityTV/actions/workflows/ci.yml)
```

## Troubleshooting

### "Squash and merge" removes my commits

This is intentional! It:
- ✅ Keeps main history clean
- ✅ Groups related changes together
- ✅ Makes bisecting easier

### My PR shows "Some checks haven't completed yet"

- Wait for GitHub Actions to finish
- Usually takes 2-5 minutes
- Cannot merge until all checks complete

### Force push is blocked

This is the protection working! Instead:
```bash
# Don't do this (blocked):
# git push --force

# Do this instead:
git pull origin main
git rebase origin/main
git push  # No --force needed
```

## Resources

- [GitHub Branch Protection Docs](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches)
- [GitHub Actions Docs](https://docs.github.com/en/actions)
- [GitHub CLI Docs](https://cli.github.com/manual/)

## Getting Help

1. Check this guide for your scenario
2. Review CONTRIBUTING.md
3. Check CI workflow logs
4. Open an issue on GitHub
