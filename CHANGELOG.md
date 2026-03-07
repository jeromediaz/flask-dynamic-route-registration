# Changelog

All notable changes to this project will be documented in this file.

## [0.9.1] - 2024-12-01

### Changed
- Allow passing additional data to routes via `route_kwargs`
- Refactor model manager access to use `extract_models_manager`

### Added
- Comprehensive integration tests for dynamic Flask route registration
- Consistent formatting across test suite
- Enhanced Docker setup and optimized dependencies handling

## [0.9.0] - 2024-11-01

### Added
- Initial public release
- `@register_route` decorator for two-phase route registration
- `register_blueprint` and `register_blueprints` functions
- `enabled` parameter support (bool or callable) for conditional route registration
- Support for `blueprints_data` as str, dict, or list of dicts
