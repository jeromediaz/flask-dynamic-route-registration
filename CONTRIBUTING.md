# Contributing

## Setup

```bash
git clone <repo>
cd flask-dynamic-route-registration
pip install -e ".[dev]"
```

## Running Tests

```bash
# All tests
pytest tests/

# Single test
pytest tests/test_blueprint_decorator.py::test_name
```

## Code Style

This project uses `black` for formatting and `ruff` for linting:

```bash
black src/ tests/
ruff check src/ tests/
```

## Pull Requests

1. Fork the repository and create a feature branch
2. Make your changes with tests covering new behavior
3. Ensure all tests pass and code is formatted
4. Open a PR with a clear description of the change
