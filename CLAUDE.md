# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/

# Run a single test
pytest tests/test_blueprint_decorator.py::test_name

# Format
black src/ tests/
```

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

`@register_route` accepts `enabled=True|False|callable`. If callable, it receives `**params` and must return bool — allowing routes to be conditionally registered per blueprint instance.
