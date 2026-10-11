# Testing Strategy

## Test Suite Organization

- `tests/part1/`: Unit and integration tests for Part 1 (deterministic metadata engine, parallel queries, formatting, LaTeX export, CLI).
- `tests/fixtures/`: Trimmed responses from Crossref and OpenAlex.
- `tests/conftest.py`: Shared pytest fixtures.

## Running Tests

```bash
# Run Part 1 tests (no network access required)
pytest tests/part1 -q

# Run with linting
ruff check . && ruff format --check .

# Run live network integration tests (optional)
pytest -m live -q
```
