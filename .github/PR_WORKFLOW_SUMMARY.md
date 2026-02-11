# Pull Request Workflow - Complete Setup

✅ **PR-based development is now enabled for UnrealityTV**

This document summarizes everything that's been set up to ensure all code changes go through pull requests with CI/CD verification.

## What's Changed

### 🚀 Automated Workflow
- ✅ GitHub Actions CI runs on every push and PR
- ✅ Tests on Python 3.10, 3.11, 3.12
- ✅ Linting and code style checks
- ✅ Security scanning
- ✅ Coverage reporting

### 📋 Documentation
- ✅ **BRANCH_PROTECTION_SETUP.md** - How to enable branch protection (prevents direct commits to main)
- ✅ **DEVELOPER_WORKFLOW.md** - Daily development guide for creating PRs
- ✅ **scripts/README.md** - Helper scripts for streamlined workflow
- ✅ **CONTRIBUTING.md** - Contribution guidelines
- ✅ **CI_CD_GUIDE.md** - CI/CD pipeline details

### 🛠️ Helper Scripts
- ✅ **scripts/setup-dev.sh** - One-command dev environment setup
- ✅ **scripts/create-pr.sh** - Interactive PR creation with validation

### 🔒 Safety Features
- ✅ Pull request template (auto-loads on new PRs)
- ✅ Pre-commit hooks config (local code quality enforcement)
- ✅ Dependabot config (automatic dependency updates)

## Next Steps for Setup

### Step 1: Enable Branch Protection on GitHub

**Go to:** https://github.com/IainDoesStuff/UnrealityTV/settings/branches

1. Click "Add rule"
2. Pattern: `main`
3. Enable these protections:
   - ✅ Require pull request reviews (1 approval)
   - ✅ Require status checks to pass:
     - test-and-lint (3.10)
     - test-and-lint (3.11)
     - test-and-lint (3.12)
     - package-check
   - ✅ Require up-to-date branches
   - ✅ Include administrators
   - ✅ Allow auto-merge
   - ✅ Block force pushes

See `.github/BRANCH_PROTECTION_SETUP.md` for detailed instructions.

### Step 2: New Developers: Run Setup Script

```bash
./scripts/setup-dev.sh
```

This:
- Creates virtual environment
- Installs dependencies
- Sets up pre-commit hooks
- Runs initial checks
- Verifies everything works

### Step 3: Start Developing with PR Workflow

```bash
# Create feature branch (never commit to main!)
git checkout -b feature/my-feature

# Make changes
vim src/unrealitytv/my_changes.py
git commit -m "Add my feature"

# Create PR with validation
./scripts/create-pr.sh

# Wait for CI to pass ✅
# Request review
# Address feedback
# Merge when approved ✅
```

## Daily Workflow

### Creating a PR

```bash
# 1. Create feature branch
git checkout -b feature/descriptive-name

# 2. Make changes
git add .
git commit -m "Clear message"

# 3. Test locally
pytest tests/ -v
ruff check src/ tests/

# 4. Push
git push origin feature/descriptive-name

# 5. Create PR (via GitHub web UI or script)
./scripts/create-pr.sh

# 6. Wait for CI ✅
# 7. Request review 👀
# 8. Address feedback if needed
# 9. Merge when approved ✅
```

### What CI Checks

```
✓ Tests on Python 3.10, 3.11, 3.12
✓ Ruff linting
✓ Code formatting
✓ Package installation
✓ Security scanning
✓ Coverage reporting
```

All must pass before merging.

### Code Review Expectations

Reviewers check for:
- ✅ Tests included
- ✅ Readable code
- ✅ Follows project style
- ✅ No obvious bugs
- ✅ Docstrings present
- ✅ Error handling included

## Common Commands

```bash
# View PRs
gh pr list

# View specific PR
gh pr view <NUMBER>

# Check PR status
gh pr checks <NUMBER>

# View workflow runs
gh run list

# View run details
gh run view <RUN_ID>

# Merge PR
gh pr merge <NUMBER> --squash

# Create PR
gh pr create --title "..." --body "..."
```

## Benefits of This Setup

| Benefit | How |
|---------|-----|
| No broken code on main | CI must pass before merge |
| Code quality enforced | Linting & tests mandatory |
| Multiple Python versions tested | Matrix testing on 3.10/3.11/3.12 |
| Reviewable changes | PRs provide diff + discussion |
| Automated dependency updates | Dependabot creates PRs weekly |
| Clear history | Squash & merge keeps main clean |
| Reversible mistakes | Revert commits if needed |
| Security scanning | Bandit scans for vulnerabilities |

## Troubleshooting

### "I can't push to main"

✅ This is correct! Branch protection is working.

**Solution:** Create a feature branch:
```bash
git checkout -b feature/my-feature
git push origin feature/my-feature
```

### "CI failed on my PR"

1. Check the "Checks" tab in your PR
2. Click the failed job
3. Read the error
4. Fix locally: `pytest -v` or `ruff check --fix src/`
5. Commit and push (CI runs automatically)

### "I need to update my PR"

Just keep committing and pushing:
```bash
git commit -m "Fix review feedback"
git push origin feature/my-feature
```

GitHub updates your PR automatically and re-runs CI.

### "I accidentally committed to main"

Don't panic! See DEVELOPER_WORKFLOW.md "I accidentally committed to main" section.

## Files & Locations

```
.github/
├── workflows/ci.yml              # Main CI workflow
├── BRANCH_PROTECTION_SETUP.md     # How to enable protection
├── PR_WORKFLOW_SUMMARY.md         # This file
└── CI_CD_GUIDE.md                 # CI/CD details

DEVELOPER_WORKFLOW.md              # Daily development guide
CONTRIBUTING.md                    # Contribution standards
.pre-commit-config.yaml            # Local code quality hooks

scripts/
├── setup-dev.sh                   # Dev environment setup
├── create-pr.sh                   # PR creation helper
└── README.md                       # Scripts documentation
```

## Learning Resources

1. **First time?** Start with: `DEVELOPER_WORKFLOW.md`
2. **Setting up branch protection?** See: `.github/BRANCH_PROTECTION_SETUP.md`
3. **How does CI work?** See: `.github/CI_CD_GUIDE.md`
4. **Coding standards?** See: `CONTRIBUTING.md`
5. **Using helper scripts?** See: `scripts/README.md`

## Key Principles

✅ **Never commit to main**
- All changes through PRs
- Branch protection prevents accidents

✅ **CI must pass**
- Tests run automatically
- Linting enforced
- No merge until green ✅

✅ **Code review required**
- Prevents bugs
- Shares knowledge
- Improves code quality

✅ **Automated dependencies**
- Dependabot keeps packages current
- Automatic PRs weekly
- Reduces security risks

✅ **Clear history**
- Squash & merge to main
- One commit per feature
- Easy to bisect and revert

## Enforcement

```yaml
Branch Protection Rules (main):
├── Require PR reviews: 1 approval
├── Require CI to pass: All checks
├── Require up-to-date: Yes
├── Dismiss stale reviews: Yes
├── Include administrators: Yes
├── Allow force pushes: NO
├── Allow deletions: NO
└── Allow auto-merge: Yes
```

## Getting Help

1. **Workflow questions?** → Read `DEVELOPER_WORKFLOW.md`
2. **CI failures?** → Check `.github/CI_CD_GUIDE.md`
3. **Branch protection setup?** → See `.github/BRANCH_PROTECTION_SETUP.md`
4. **Script issues?** → Check `scripts/README.md`
5. **Code standards?** → Review `CONTRIBUTING.md`

## Summary

You now have:

✅ **Automated CI/CD** - Every PR tested on 3 Python versions
✅ **Branch Protection** - Prevents direct commits to main
✅ **Helper Scripts** - Streamline PR creation
✅ **Clear Documentation** - Guides for every scenario
✅ **Code Quality Enforcement** - Linting and tests required
✅ **Security Scanning** - Vulnerability detection
✅ **Dependency Management** - Automatic updates
✅ **Pre-commit Hooks** - Local code quality checks

**Result:** High-quality, well-tested code that's safe to merge.

---

Ready to start developing? See `DEVELOPER_WORKFLOW.md`! 🚀
