# Developer Workflow Guide

This guide explains the daily workflow for developing UnrealityTV using pull requests and CI/CD.

## Core Principles

✅ **Never commit directly to main**
✅ **All changes go through PRs**
✅ **CI must pass before merging**
✅ **Require code review**
✅ **Keep commits organized and logical**

## Daily Workflow

### 1️⃣ Starting a New Feature

```bash
# Update local main with latest
git checkout main
git pull origin main

# Create feature branch (use descriptive names)
git checkout -b feature/add-audio-extraction
# or for fixes:
git checkout -b fix/parser-regex-bug
# or for docs:
git checkout -b docs/update-readme
```

**Branch naming convention:**
- `feature/` - New functionality
- `fix/` - Bug fixes
- `docs/` - Documentation updates
- `refactor/` - Code improvements
- `test/` - Test additions

### 2️⃣ Making Changes

```bash
# Make your changes
vim src/unrealitytv/audio/extract.py
vim tests/test_audio_extract.py

# Commit frequently with clear messages
git add src/unrealitytv/audio/extract.py
git commit -m "Add audio extraction with FFmpeg

- Extract mono WAV at 16kHz for Whisper
- Handle missing FFmpeg gracefully
- Add duration detection helper"

git add tests/test_audio_extract.py
git commit -m "Add tests for audio extraction

- Test successful extraction
- Test missing FFmpeg error handling
- Test temporary file cleanup"
```

**Commit message format:**
```
Short title (50 chars max)

Longer explanation of what changed and why.
- Bullet point for each major change
- Reference related issues: Closes #123
- Include Co-Authored-By if pair programming
```

### 3️⃣ Local Testing Before Push

```bash
# Run tests
pytest tests/ -v

# Check code style
ruff check src/ tests/

# Format code
ruff format src/ tests/

# Verify installation still works
pip install -e ".[dev]"
```

**All must pass before pushing!**

### 4️⃣ Push to Remote

```bash
# Push your branch
git push origin feature/add-audio-extraction

# If first time pushing:
git push -u origin feature/add-audio-extraction
```

### 5️⃣ Create Pull Request

**Option A: Via GitHub Web UI (Recommended)**
1. Go to repo: https://github.com/iainswarts/UnrealityTV
2. You'll see a banner: "feature/add-audio-extraction had recent pushes"
3. Click "Compare & pull request"
4. Fill in PR template
5. Click "Create pull request"

**Option B: Via GitHub CLI**
```bash
gh pr create \
  --title "Add audio extraction with FFmpeg" \
  --body "Implements audio extraction for Whisper transcription

  ## Changes
  - Add extract_audio() function
  - Add get_duration_ms() helper
  - Comprehensive error handling

  Closes #123"
```

### 6️⃣ Wait for CI to Pass

The workflow runs automatically:
- 🔄 Tests on Python 3.10, 3.11, 3.12
- 🔄 Ruff linting and formatting
- 🔄 Security scanning
- 🔄 Package installation check

**Check status in PR:**
1. Click "Checks" tab
2. See each job status
3. If any fail, click job for details

**Expected time:** 2-5 minutes

### 7️⃣ Request Code Review

1. Scroll to "Reviewers" section in PR
2. Click gear icon
3. Select @iainswarts (or whoever)
4. Reviewer gets notified automatically

### 8️⃣ Address Review Feedback

When reviewer requests changes:

```bash
# Make the changes
vim src/unrealitytv/audio/extract.py

# Commit as normal
git add src/unrealitytv/audio/extract.py
git commit -m "Address review feedback

- Add docstring to extract_audio()
- Handle edge case for empty videos"

# Push (CI runs again automatically)
git push origin feature/add-audio-extraction

# Mark conversation as resolved in PR
# (Reply to reviewer comment and click "Resolve conversation")
```

### 9️⃣ Merge

Once approved ✅ and CI passes ✅:

**Option A: Via GitHub Web UI**
1. Click "Squash and merge" button
2. Review the squashed commit message
3. Click "Confirm squash and merge"

**Option B: Via GitHub CLI**
```bash
gh pr merge <PR_NUMBER> --squash --auto
```

**After merge:**
1. GitHub offers to delete your branch - do it!
2. Or delete locally:
   ```bash
   git checkout main
   git branch -D feature/add-audio-extraction
   ```

## Handling Common Situations

### "CI Failed - How do I fix it?"

1. **Check what failed**
   - Go to PR → Checks tab
   - Click failed job name
   - Read the error message

2. **Common failures:**

   **Linting error:**
   ```bash
   ruff check --fix src/ tests/
   git add .
   git commit -m "Fix linting errors"
   git push
   ```

   **Test failure:**
   ```bash
   # Run locally to debug
   pytest tests/test_audio_extract.py -v -s
   # Fix the issue
   git add .
   git commit -m "Fix test failure"
   git push
   ```

   **CI passes on your machine but fails on GitHub:**
   ```bash
   # Check Python version mismatch
   python --version

   # Test on other versions if possible
   python3.10 -m pytest tests/
   python3.11 -m pytest tests/
   ```

### "My branch is out of date with main"

```bash
# Fetch latest
git fetch origin

# Rebase your work on top of main
git rebase origin/main

# Push (this is safe after rebase)
git push origin feature/my-feature --force-with-lease

# Or if there are conflicts:
git rebase --abort  # Start over
git merge origin/main  # Merge instead
git push origin feature/my-feature
```

### "I need to update my PR with new commits"

Just keep committing and pushing - GitHub automatically updates the PR:

```bash
git commit -m "Add missing test case"
git push origin feature/my-feature

# CI runs automatically
# PR updates automatically
# No need to create a new PR!
```

### "Reviewer wants me to squash commits"

```bash
# Get the number of commits to squash
git log origin/main..HEAD --oneline

# Rebase and squash (example: 3 commits)
git rebase -i origin/main

# In the editor:
# pick commit1
# squash commit2  (change 'pick' to 'squash')
# squash commit3

# Save and resolve any conflicts
git push origin feature/my-feature --force-with-lease
```

### "I accidentally committed to main"

```bash
# Get latest main
git fetch origin

# Undo the commit
git reset --soft origin/main

# Stash the changes
git stash

# Go back to origin/main
git reset --hard origin/main

# Create a proper branch
git checkout -b feature/my-feature

# Apply the changes
git stash pop

# Commit and push normally
git commit -m "My feature"
git push -u origin feature/my-feature
```

## Pro Tips

### 💡 Use draft PRs for work in progress

```bash
gh pr create --draft --title "WIP: Audio extraction"
```

This signals the PR isn't ready for review but shows progress.

### 💡 Keep commits focused

Each commit should be one logical change:
```bash
❌ Bad: "Add audio extraction and fix parser bug and update docs"
✅ Good: Three separate commits/PRs
```

### 💡 Use conventional commits

```
feat: Add audio extraction for Whisper
fix: Handle missing FFmpeg gracefully
docs: Update README with setup instructions
test: Add coverage for parser edge cases
refactor: Simplify episode filename regex
```

### 💡 Link related issues

```bash
git commit -m "Fix episode parser regex

Closes #45
Related to #42"
```

### 💡 Pre-commit hooks catch issues early

```bash
pip install pre-commit
pre-commit install

# Now runs automatically before every commit
# Prevents pushing broken code
```

### 💡 Create milestones for phases

Group related PRs under Phase 0, Phase 1, etc.
- Go to Issues → Milestones
- Create "Phase 1: MVP"
- Add PRs to milestone when created

## Review Expectations

### What reviewers look for:

✅ Tests included
✅ Code is readable
✅ Follows project style
✅ No obvious bugs
✅ Docstrings present
✅ No hardcoded values
✅ Error handling included

### How to speed up review:

1. **Clear PR description** - Explain what and why
2. **Small PRs** - Easier to review (< 400 lines ideal)
3. **Good commit messages** - Tells the story
4. **Tests included** - Shows you tested it
5. **Self-review first** - Check your own code before requesting review

## Emergency: Revert a Merged PR

If a bad PR got merged:

```bash
# Revert the commit
git revert <COMMIT_HASH>

# Create a new PR with the revert
git push origin revert-branch
gh pr create --title "Revert: PR #123"
```

Or manually undo via new PR.

## Branch Protection Reminders

⚠️ **You cannot:**
- Force push to main
- Commit directly to main
- Merge without approval
- Merge with failing CI

✅ **You can:**
- Create unlimited feature branches
- Push to your feature branches
- Request reviews from maintainers
- Use auto-merge after approval

## Resources

- [BRANCH_PROTECTION_SETUP.md](.github/BRANCH_PROTECTION_SETUP.md) - How to set up protection rules
- [CONTRIBUTING.md](CONTRIBUTING.md) - Contribution guidelines
- [CI_CD_GUIDE.md](.github/CI_CD_GUIDE.md) - How CI/CD works
- [GitHub Flow Guide](https://guides.github.com/introduction/flow/)

## Getting Help

1. Check this guide
2. Check `.github/BRANCH_PROTECTION_SETUP.md`
3. Review error messages in PR checks
4. Open an issue with "help wanted" label
