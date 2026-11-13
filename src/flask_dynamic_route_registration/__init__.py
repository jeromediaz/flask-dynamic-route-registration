"""
Flask Dynamic Route Registration
-------
A library to help dynamically register routes in flask application
"""

from .blueprint_decorator import register_route
from .register_blueprints import register_blueprint, register_blueprints

try:
    from importlib.metadata import PackageNotFoundError
    from importlib.metadata import version as _version

    __version__ = _version("flask-dynamic-route-registration")
except PackageNotFoundError:
    # Source-tree checkout without an installed distribution.
    __version__ = "0.10.0"

__all__ = ["register_blueprint", "register_blueprints", "register_route"]
