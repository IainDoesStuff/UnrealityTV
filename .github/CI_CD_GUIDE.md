# CI/CD Pipeline Guide

## Overview

The UnrealityTV project uses GitHub Actions for continuous integration and continuous deployment. This ensures code quality, test coverage, and compatibility across all supported Python versions.

## Automated Workflows

### Main CI Workflow (`ci.yml`)

**Triggered on:**
- Push to `main` branch
- Pull requests to `main` branch

**Jobs:**

#### 1. **test-and-lint** (Matrix: Python 3.10, 3.11, 3.12)
- **Install dependencies**: Installs project in editable mode with dev dependencies
- **Ruff linting**: Checks code style and finds issues
- **Ruff format check**: Ensures consistent code formatting
- **Pytest**: Runs all tests with verbose output
- **Coverage reporting**: Generates coverage metrics and uploads to Codecov
- **Caching**: Uses GitHub cache to speed up pip installations

**Success criteria:**
- ✅ All tests pass on all Python versions
- ✅ Ruff linting passes with no errors
- ✅ Code coverage is reported

#### 2. **package-check**
- Verifies the package can be installed correctly
- Runs `unrealitytv --version` to ensure CLI works
- Checks package metadata with `pip show`

**Success criteria:**
- ✅ Package installs without errors
- ✅ CLI entry point is functional

#### 3. **security-check**
- Runs Bandit for basic security vulnerability scanning
- Generates JSON report (continues even if issues found)

**Success criteria:**
- ✅ No critical security issues identified

#### 4. **summary**
- Aggregates results from all jobs
- Fails if any critical job failed
- Provides clear pass/fail status

## Dependency Management

### Dependabot Configuration

**Automated features:**
- Weekly dependency updates (Monday 03:00 UTC)
- Automatic PRs for outdated pip packages
- Automatic PRs for GitHub Action updates
- Limit of 5 open PRs at once
- Auto-assigned to repository owner
- Labeled as "dependencies" or "ci"

**Benefits:**
- Keeps dependencies current and secure
- Automated patch version updates
- Early detection of breaking changes
- Reduced maintenance burden

## Local Development

### Pre-commit Hooks

Optional but recommended for local development:

```bash
pip install pre-commit
pre-commit install
```

**Hooks included:**
- **ruff**: Automatic code formatting and linting
- **ruff-format**: Code formatting enforcement
- **trailing-whitespace**: Remove trailing spaces
- **end-of-file-fixer**: Ensure files end with newline
- **check-yaml**: Validate YAML files
- **check-added-large-files**: Prevent large file commits
- **check-merge-conflict**: Detect merge conflicts
- **debug-statements**: Find debug code (pdb, breakpoint)
- **mypy**: Static type checking (optional)

## PR Template

All pull requests use a standard template (`.github/pull_request_template.md`) that includes:
- Description section
- Type of change checkboxes
- Related issue link
- Testing checklist
- Code quality checklist

## Monitoring & Status

### View CI Status

1. **In GitHub UI:**
   - Check the "Checks" tab on pull requests
   - View workflow runs in the "Actions" tab
   - See badges on README

2. **Locally:**
   ```bash
   # View recent workflow runs
   gh run list
   ```

### Coverage Reports

Coverage reports are uploaded to Codecov:
- View at: https://codecov.io/gh/iainswarts/UnrealityTV
- Badge available for README
- Historical coverage tracking
- Per-file coverage breakdown

## Troubleshooting

### CI Failed: Linting Errors

**Fix locally:**
```bash
ruff check --fix src/ tests/
ruff format src/ tests/
```

### CI Failed: Test Failures

**Debug locally:**
```bash
pytest tests/ -v          # Verbose output
pytest tests/ -s           # Show print statements
pytest tests/ -k "test_name"  # Run specific test
```

### CI Failed: Python Version Specific

Check which Python version failed and test locally:
```bash
python3.10 -m pytest tests/
python3.11 -m pytest tests/
python3.12 -m pytest tests/
```

## Best Practices

### Before Pushing

Always run locally:
```bash
# Full test suite
pytest tests/ -v

# Linting
ruff check src/ tests/

# Format code
ruff format src/ tests/

# Verify installation
pip install -e ".[dev]"
```

### Commit Messages

Include relevant context:
```
Fix: Handle edge case in episode parser

- Add test for filenames with multiple dots
- Update parser regex to be more precise
- Fixes #123

Closes #123
```

### PR Reviews

- Ensure all CI checks pass
- Request review from maintainers
- Address feedback promptly
- Keep commits logical and clean

## Workflow File Locations

```
.github/
├── workflows/
│   └── ci.yml              # Main CI workflow
├── dependabot.yml          # Dependency management config
└── pull_request_template.md # PR template
```

## Adding New Checks

To add new checks to the CI pipeline:

1. Edit `.github/workflows/ci.yml`
2. Add step to appropriate job or create new job
3. Test locally if possible
4. Commit and push (workflow will run immediately)
5. Monitor "Actions" tab in GitHub

Example new step:
```yaml
- name: Run new check
  run: |
    new-tool --check
```

## Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [pytest Documentation](https://docs.pytest.org/)
- [Codecov Documentation](https://docs.codecov.io/)

## Getting Help

1. Check workflow logs in GitHub Actions tab
2. See `.github/CI_CD_GUIDE.md` (this file)
3. Review `CONTRIBUTING.md` for development guidelines
4. Open an issue on GitHub
