# Contributing to UnrealityTV

Thank you for your interest in contributing to UnrealityTV! This document provides guidelines and instructions for contributing to the project.

## Getting Started

### Prerequisites
- Python 3.10 or higher
- pip and virtual environment support
- Git

### Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/iainswarts/UnrealityTV.git
   cd UnrealityTV
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install in development mode with all dependencies**
   ```bash
   pip install -e ".[dev]"
   ```

4. **Install pre-commit hooks (optional but recommended)**
   ```bash
   pip install pre-commit
   pre-commit install
   ```

## Development Workflow

### Running Tests
```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src/unrealitytv --cov-report=html

# Run specific test file
pytest tests/test_models.py -v
```

### Code Quality
```bash
# Check code with ruff
ruff check src/ tests/

# Format code
ruff format src/ tests/

# Fix common issues automatically
ruff check --fix src/ tests/
```

### Before Committing
```bash
# Run the full test suite
pytest tests/ -v

# Check linting
ruff check src/ tests/

# Verify package installation
pip install -e ".[dev]"
```

## Project Structure

```
UnrealityTV/
├── src/unrealitytv/          # Main package source code
│   ├── __init__.py           # Package initialization with version
│   ├── cli.py                # Click CLI commands
│   ├── config.py             # Pydantic Settings configuration
│   ├── db.py                 # SQLite database layer
│   ├── models.py             # Pydantic data models
│   ├── parsers.py            # Episode filename parsing
│   ├── migrations/           # SQL migration files
│   └── [phase-specific]/     # Phase 1-9 modules
├── tests/                    # Test suite
│   ├── conftest.py           # Pytest configuration and fixtures
│   ├── test_*.py             # Test modules
├── docs/                     # Documentation
├── pyproject.toml            # Project metadata and dependencies
└── .github/
    ├── workflows/            # GitHub Actions CI/CD
    └── pull_request_template.md
```

## Making Changes

### Creating a Feature Branch
```bash
git checkout -b feature/your-feature-name
# or for bug fixes:
git checkout -b fix/your-bug-fix
```

### Committing Changes
- Write clear, descriptive commit messages
- Reference related issues when applicable
- Include co-author information if pair programming:
  ```
  Co-Authored-By: Your Name <your.email@example.com>
  ```

### Writing Tests
- Add tests for all new functionality
- Maintain >80% code coverage
- Use descriptive test names and docstrings
- Test both happy paths and edge cases

Example test structure:
```python
def test_feature_does_something_specific():
    """Test that feature X behaves correctly when Y happens."""
    # Arrange
    input_data = ...

    # Act
    result = function_under_test(input_data)

    # Assert
    assert result == expected_value
```

### Documentation
- Update README.md for new public APIs
- Add docstrings to functions and classes
- Document breaking changes in commit messages
- Update relevant docs/ files for significant changes

## Pull Request Process

1. **Ensure all tests pass locally**
   ```bash
   pytest tests/ -v
   ruff check src/ tests/
   ```

2. **Push to your branch**
   ```bash
   git push origin feature/your-feature-name
   ```

3. **Create a Pull Request**
   - Use the PR template
   - Provide clear description of changes
   - Link related issues
   - Ensure CI checks pass

4. **Code Review**
   - Address reviewer feedback
   - Re-run tests if changes are made
   - Keep commits clean and logical

5. **Merge**
   - Squash commits if requested
   - Delete branch after merging

## Coding Standards

### Python Style
- Follow PEP 8 style guide
- Use type hints where practical
- Maximum line length: 88 characters (enforced by ruff)
- Use f-strings for string formatting

### Imports
- Group imports: stdlib, third-party, local
- Use absolute imports
- Sort alphabetically within groups

### Naming
- `CamelCase` for classes
- `snake_case` for functions and variables
- `UPPER_CASE` for constants
- Descriptive, meaningful names

### Docstrings
Use Google-style docstrings:
```python
def function_name(param1: str, param2: int) -> bool:
    """Brief description.

    Longer description if needed.

    Args:
        param1: Description of param1
        param2: Description of param2

    Returns:
        Description of return value

    Raises:
        ValueError: When something invalid happens
    """
```

## CI/CD Pipeline

The project uses GitHub Actions for continuous integration:

- **Tests**: Run pytest on Python 3.10, 3.11, 3.12
- **Linting**: Ensure ruff compliance
- **Coverage**: Track code coverage with Codecov
- **Package Check**: Verify package installation works
- **Security**: Basic security scan with bandit

All checks must pass before merging.

## Reporting Issues

When reporting bugs, please include:
- Python version and OS
- Steps to reproduce
- Expected vs actual behavior
- Relevant code snippets or logs
- Any relevant error messages

## Questions?

- Check existing issues and discussions
- Review the project documentation
- Open a new discussion if your question isn't answered

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
