"""
Flask Dynamic Route Registration
-------
A library to help dynamically register routes in flask application
"""
from .blueprint_decorator import register_route
from .register_blueprints import register_blueprint, register_blueprints
__version__ = "0.1.0"

__all__ = [
    'register_blueprint',
    'register_blueprints',
    'register_route'
]