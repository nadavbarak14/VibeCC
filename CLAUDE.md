# Claude Code Instructions for VibeCC

## Ticket Workflow

When working on any ticket:

1. **Create branch** from latest main
   ```bash
   git checkout main
   git pull origin main
   git checkout -b ticket-{number}
   ```

2. **Implement** the ticket requirements with tests

3. **Push and create PR**
   ```bash
   git push -u origin ticket-{number}
   gh pr create --title "#{number}: {ticket title}" --body "Closes #{number}"
   ```

4. **Wait for CI** to pass
   ```bash
   gh pr checks --watch
   ```

5. **Merge** when CI passes (rebase)
   ```bash
   gh pr merge --rebase --delete-branch
   ```

## Project Structure

```
src/vibecc/           # Main package
tests/
  unit/               # Fast, mocked tests
  integration/        # Real DB/API tests
docs/design/          # Component specs
```

## Code Style

- Python 3.11+
- Type hints required
- Use dataclasses for DTOs
- SQLAlchemy for database
- pytest for tests
- ruff for linting

## Testing

- Every ticket must include tests as specified
- Run tests before pushing: `pytest`
- Unit tests should be fast and mocked
- Integration tests can use real DB (SQLite in temp dir)

## References

- Design docs: `docs/design/`
- API specs: `docs/design/components/{component}/API.md`
