# Contributing to VibeCC

Thank you for your interest in contributing to VibeCC!

## Development Workflow

### Setting Up Your Environment

1. Fork the repository on GitHub
2. Clone your fork locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/VibeCC.git
   cd VibeCC
   ```

3. Add the upstream remote:
   ```bash
   git remote add upstream https://github.com/nadavbarak14/VibeCC.git
   ```

4. Create a virtual environment and install dependencies:
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -e ".[dev]"
   ```

5. Install pre-commit hooks:
   ```bash
   pre-commit install
   ```

### Making Changes

1. Create a new branch from `main`:
   ```bash
   git checkout main
   git pull upstream main
   git checkout -b feature/your-feature-name
   ```

2. Make your changes and ensure:
   - All tests pass: `pytest`
   - Code is formatted: `ruff format .`
   - Linting passes: `ruff check .`
   - Type checking passes: `mypy src/`

3. Commit your changes with clear, descriptive messages

4. Push to your fork and create a Pull Request

### Pull Request Guidelines

- All PRs must target the `main` branch
- PRs require passing CI checks before merge
- PRs require at least one approval from a code owner
- Use rebase to keep your branch up to date with main
- Write clear PR descriptions explaining the changes

### Code Style

- Follow PEP 8 style guidelines (enforced by Ruff)
- Use type hints for all function signatures
- Write docstrings for public functions and classes
- Keep functions focused and small

### Testing Guidelines

- Write tests for all new functionality
- Maintain minimum 80% code coverage
- Use appropriate test markers:
  - `@pytest.mark.unit` - Fast, isolated tests
  - `@pytest.mark.integration` - Component interaction tests
  - `@pytest.mark.e2e` - Full pipeline tests
  - `@pytest.mark.real` - Tests with actual external services (local only)

### Commit Message Format

Use clear, descriptive commit messages:
- Start with a verb in imperative mood (Add, Fix, Update, Remove)
- Keep the first line under 72 characters
- Add detailed description in the body if needed

Example:
```
Add user authentication module

- Implement JWT token generation
- Add login/logout endpoints
- Include unit tests for auth flow
```

## Questions?

If you have questions, feel free to open an issue for discussion.
