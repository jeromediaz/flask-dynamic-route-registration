# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Changed
- **BREAKING**: the `enabled` contract is now enforced — a gate result (or literal
  `enabled` value) that is not a `bool` raises `TypeError` at registration instead of
  registering the route by truthiness. Config strings like `"false"` no longer
  silently enable routes.
- Registering `params`/`route_kwargs` keys that collide with a rule's URL variables
  raises `ValueError` (they would silently pin the variable via Flask route defaults).
- `register_blueprints` validates blueprint-name uniqueness across all entries before
  touching the container; a duplicate raises a clean `ValueError` and leaves the
  container byte-identical to its pre-call state instead of partially registering.
- Declared Python floor raised to 3.10 (the code never worked on 3.8/3.9 — PEP 604
  runtime unions); classifiers and black/ruff targets follow.
- `__version__` derives from distribution metadata instead of a drifted literal.

### Infrastructure
- CI matrix (Python 3.10–3.13 × flask 2.0 floor and latest), build + `twine check`,
  and Trusted Publishing to PyPI on `v*` tags.
- `black`/`ruff`/`mypy` pinned in dev extras, configured in pyproject, enforced in CI
  and in `lefthook.yml` pre-commit/pre-push hooks.

## [0.9.1] - date unknown

### Changed
- Allow passing additional data to routes via `route_kwargs`

### Added
- Comprehensive integration tests for dynamic Flask route registration
- Consistent formatting across test suite

<!-- The previous entry for this release dated 2024-12-01 and listed
     "Refactor model manager access to use extract_models_manager" and
     "Enhanced Docker setup"; neither corresponds to anything in this
     repository's source or git history, and the version bump commit is
     dated 2025-12-22. Corrected 2026-11-13; the 0.9.1 artifact on PyPI is
     not anchored to any git tag. -->

## [0.9.0] - 2024-11-01

### Added
- Initial public release
- `@register_route` decorator for two-phase route registration
- `register_blueprint` and `register_blueprints` functions
- `enabled` parameter support (bool or callable) for conditional route registration
- Support for `blueprints_data` as str, dict, or list of dicts
