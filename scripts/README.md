# Helper Scripts

This directory contains utility scripts to simplify development workflow for UnrealityTV.

## setup-dev.sh

Automated developer environment setup script.

**What it does:**
- ✅ Checks Python 3.10+ is installed
- ✅ Creates virtual environment
- ✅ Installs project in editable mode with dev dependencies
- ✅ Sets up pre-commit hooks
- ✅ Runs initial quality checks (tests, linting, package verification)

**Usage:**
```bash
./scripts/setup-dev.sh
```

**One-time setup from scratch:**
```bash
# Clone repo
git clone https://github.com/IainDoesStuff/UnrealityTV.git
cd UnrealityTV

# Run setup
./scripts/setup-dev.sh

# Start developing!
git checkout -b feature/my-feature
```

## create-pr.sh

Helper script to create pull requests with validation.

**What it does:**
- ✅ Verifies you're not on main branch
- ✅ Pushes branch to remote if needed
- ✅ Runs local tests
- ✅ Checks code style
- ✅ Creates PR via GitHub CLI (if installed)
- ✅ Falls back to manual instructions if `gh` not available

**Usage:**
```bash
./scripts/create-pr.sh
```

**When to use:**
After you've finished making changes:

```bash
# Make your changes
git add src/unrealitytv/my_changes.py
git commit -m "My changes"

# Create the PR
./scripts/create-pr.sh
```

**Interactive prompts:**
- PR Title (defaults to branch name if empty)
- PR Description (optional)
- Optionally creates PR via `gh` CLI

## Requirements

### For setup-dev.sh
- Python 3.10+
- pip and venv (usually included with Python)
- Git

### For create-pr.sh
- Same as setup-dev.sh
- (Optional) GitHub CLI (`gh`) for automated PR creation
  - macOS: `brew install gh`
  - Ubuntu: `sudo apt install gh`
  - Windows: `choco install gh`

## Common Workflows

### First Time Setup
```bash
git clone https://github.com/IainDoesStuff/UnrealityTV.git
cd UnrealityTV
./scripts/setup-dev.sh
source venv/bin/activate
```

### Daily Development
```bash
# Start work
git checkout -b feature/my-feature

# Make changes
vim src/unrealitytv/my_file.py

# Commit
git add .
git commit -m "My changes"

# Create PR
./scripts/create-pr.sh
```

### Handling CI Failures
```bash
# Check what failed
# (Go to GitHub PR page → Checks tab)

# Fix locally
vim src/unrealitytv/my_file.py

# Run checks
pytest tests/ -v
ruff check --fix src/ tests/

# Commit and push (CI runs automatically)
git add .
git commit -m "Fix CI issues"
git push origin feature/my-feature
```

## Troubleshooting

### "Permission denied: ./scripts/setup-dev.sh"

```bash
chmod +x scripts/setup-dev.sh
./scripts/setup-dev.sh
```

### "Command not found: pytest"

```bash
# Make sure venv is activated
source venv/bin/activate

# Then run setup
./scripts/setup-dev.sh
```

### "Cannot create PR from main branch"

```bash
# You need to create a feature branch first
git checkout -b feature/my-feature
# Make your changes
./scripts/create-pr.sh
```

### "Tests failed before creating PR"

Fix the failing tests before creating the PR:

```bash
# See what's failing
pytest tests/ -v

# Fix the issue
vim src/unrealitytv/my_file.py

# Run tests again
pytest tests/ -v

# Once passing, create PR
./scripts/create-pr.sh
```

### "GitHub CLI not installed"

The script will fallback to manual instructions. To enable automated PR creation:

**macOS:**
```bash
brew install gh
gh auth login  # One-time authentication
```

**Ubuntu/Debian:**
```bash
sudo apt install gh
gh auth login  # One-time authentication
```

**Windows:**
```bash
choco install gh
gh auth login  # One-time authentication
```

## Advanced Usage

### Customizing setup-dev.sh

Edit the script to add additional setup steps:
```bash
# Add after "Running initial quality checks"
echo "Installing additional tools..."
pip install mypy isort
```

### Customizing create-pr.sh

Add pre-PR checks by editing the script. For example, add type checking:
```bash
# Add after linting check
echo "Running type checks..."
mypy src/ --ignore-missing-imports
```

## Tips & Tricks

### Make it easier to run
```bash
# Add scripts directory to PATH
export PATH="$PATH:$(pwd)/scripts"

# Now you can run from anywhere in the repo
setup-dev.sh
create-pr.sh
```

### Alias for quick access
```bash
# Add to ~/.bashrc or ~/.zshrc
alias setup-unreality='~/UnrealityTV/scripts/setup-dev.sh'
alias pr-unreality='~/UnrealityTV/scripts/create-pr.sh'

# Then use:
setup-unreality
pr-unreality
```

### Combine with other tools
```bash
# Create PR and open it in browser
./scripts/create-pr.sh
gh pr view --web  # Opens PR in browser

# See what changed
git diff origin/main

# See commits
git log origin/main..HEAD
```

## Contributing to Scripts

If you improve these scripts:

1. Test them thoroughly
2. Add comments for complex logic
3. Update this README with new usage
4. Create a PR like any other change

## Support

- Check DEVELOPER_WORKFLOW.md for workflow guidance
- Check CI_CD_GUIDE.md for CI/CD details
- Check CONTRIBUTING.md for coding standards
- Open an issue if scripts don't work as expected
