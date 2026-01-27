# VibeCC

A code generation and analysis tool.

[![CI](https://github.com/nadavbarak14/VibeCC/actions/workflows/main.yml/badge.svg)](https://github.com/nadavbarak14/VibeCC/actions/workflows/main.yml)
[![codecov](https://codecov.io/gh/nadavbarak14/VibeCC/branch/main/graph/badge.svg)](https://codecov.io/gh/nadavbarak14/VibeCC)

## Overview

VibeCC is a Python-based tool for code generation and analysis.

## Requirements

- Python 3.11 or higher

## Installation

### Development Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/nadavbarak14/VibeCC.git
   cd VibeCC
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install the package with development dependencies:
   ```bash
   pip install -e ".[dev]"
   ```

4. Set up pre-commit hooks:
   ```bash
   pre-commit install
   ```

## Running Tests

### Run all tests
```bash
pytest
```

### Run specific test categories
```bash
# Unit tests only (fast, no external dependencies)
pytest -m unit

# Integration tests (component interactions)
pytest -m integration

# End-to-end tests (full pipeline)
pytest -m e2e

# Real tests with actual Claude Code (local only, not in CI)
pytest -m real
```

### Run tests with coverage
```bash
pytest --cov=src/vibecc --cov-report=html
# Open htmlcov/index.html to view the coverage report
```

## Code Quality

### Linting and Formatting
```bash
# Check linting
ruff check .

# Auto-fix linting issues
ruff check --fix .

# Check formatting
ruff format --check .

# Apply formatting
ruff format .
```

### Type Checking
```bash
mypy src/
```

### Run All Pre-commit Hooks
```bash
pre-commit run --all-files
```

## Project Structure

```
VibeCC/
├── src/
│   └── vibecc/          # Main package
│       └── __init__.py
├── tests/
│   ├── unit/            # Fast, isolated unit tests
│   ├── integration/     # Component interaction tests
│   ├── e2e/             # Full pipeline tests
│   └── conftest.py      # Shared fixtures
├── .github/
│   ├── workflows/       # CI/CD workflows
│   └── CODEOWNERS
├── pyproject.toml       # Project configuration
├── .pre-commit-config.yaml
└── README.md
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development workflow and guidelines.

## License

MIT License
