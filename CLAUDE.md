# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies (tools are pinned in the dev extra)
pip install -e ".[dev]"

# Run tests
pytest tests/

# Run a single test
pytest tests/test_blueprint_decorator.py::test_name

# Format / lint / type-check (same commands as CI)
black src/ tests/
ruff check src/ tests/          # ruff check --fix for auto-fixables
mypy src/flask_dynamic_route_registration
```

Release: bump `version` in `pyproject.toml` in its own commit, tag it `vX.Y.Z`, push branch + tag. CI builds and publishes the tag to PyPI via Trusted Publishing (no API token). `__version__` derives from the installed distribution metadata — never edit it.

## Architecture

This is a small Flask utility library (`flask-dynamic-route-registration`) that enables dynamic, parameterized route registration via decorators.

### Two-phase registration pattern

Routes are defined with `@register_route` but **not registered immediately**. Instead, the decorator wraps the function in a `wrapper(blueprint, **params)` callable tagged with `is_url_rule = True`. The actual `blueprint.route(...)` call happens later when `register_blueprint` iterates over the module's members.

This two-phase approach allows the same module to be mounted multiple times with different `params` (e.g., different API versions at different URL prefixes).

### Key files

- `src/flask_dynamic_route_registration/blueprint_decorator.py` — `@register_route` decorator and `is_register_route` predicate
- `src/flask_dynamic_route_registration/register_blueprints.py` — `register_blueprint` and `register_blueprints` functions that import a module, find all decorated functions, and register them on new Flask Blueprints
- `src/flask_dynamic_route_registration/__init__.py` — public API: `register_route`, `register_blueprint`, `register_blueprints`

### `register_blueprint` signature

```python
register_blueprint(container, module_name, blueprints_data, route_kwargs)
```

- `container`: Flask app or parent Blueprint
- `module_name`: dotted module path to import (must have `@register_route`-decorated functions)
- `blueprints_data`: str (url_prefix), dict, or list of dicts with keys `blueprint_name`, `blueprint_kwargs`, `params`
- `route_kwargs`: extra kwargs merged into `params` for every blueprint

### `enabled` parameter

`@register_route` accepts `enabled=True|False|callable`. If callable, it receives `**params` and must return bool — allowing routes to be conditionally registered per blueprint instance. The bool contract is enforced at registration: a gate result (or a literal `enabled` value) that is not a `bool` raises `TypeError` before anything is registered. Truthy non-bools like `'false'` no longer silently register a route.

### Registration validation (fails fast, no partial state)

- **params vs URL variables**: a `params`/`route_kwargs` key named identically to a URL variable in the rule (e.g. `subject` with rule `/foo/<subject>`) raises `ValueError` at registration — Flask route `defaults` would silently override the client's path value.
- **name-uniqueness pre-pass in `register_blueprints`**: effective blueprint names (default = module's last dot-segment) are validated across all entries of all modules before the container is touched; duplicates raise `ValueError` telling you to set `blueprint_name`. A failed plural registration leaves the container byte-identical to its pre-call state.
- `register_blueprint` called directly with colliding list entries still fails via Flask's own duplicate-name `ValueError`, which can leave earlier children registered — prefer `register_blueprints` for the atomic behavior.

### Gotcha: params become view kwargs

All `params` (merged `blueprint_data["params"]` + `route_kwargs`) are passed as Flask `defaults`, so every params key must be accepted by each registered view function — a view that doesn't take the key raises `TypeError` per request. Views consuming config params should accept `**kwargs` or declare the keys.
