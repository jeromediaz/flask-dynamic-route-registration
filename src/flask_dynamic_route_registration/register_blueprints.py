from collections.abc import Mapping
from inspect import getmembers
from typing import TYPE_CHECKING, Any, Union

from flask import Blueprint

from .blueprint_decorator import is_register_route

if TYPE_CHECKING:
    from flask.app import Flask


def register_blueprint(
    container: Union["Flask", "Blueprint"],
    module_name: str,
    blueprints_data: str | Any | list[str | Any],
    route_kwargs: Mapping[str, Any],
):
    """
    Function to register a blueprint inside `container`

    Args:
        container (Union["Flask", "Blueprint"]): a flask app object or a parent blueprint to register the new blueprint in
        module_name (str): the name of the module that contains the decorated routes
        blueprints_data: configuration data, if a string is given it is used as the url_prefix value

    Returns:
        List[Blueprint]: the new blueprints
    """
    module_object = __import__(module_name, fromlist=[""])
    functions = getmembers(module_object, is_register_route)

    if not functions:
        return

    if not isinstance(blueprints_data, list):
        blueprints_data = [blueprints_data]

    new_blueprints: list[Blueprint] = []

    for blueprint_data in blueprints_data:
        if isinstance(blueprint_data, str):
            blueprint_data = {"blueprint_kwargs": {"url_prefix": blueprint_data}}

        blueprint_name = blueprint_data.get(
            "blueprint_name", module_object.__name__.split(".")[-1]
        )
        blueprint_kwargs = blueprint_data.get("blueprint_kwargs", {})
        params = {**blueprint_data.get("params", {}), **route_kwargs}
        module_blueprint = Blueprint(blueprint_name, module_object.__name__)

        for register_route in functions:
            register_route[1](module_blueprint, **params)

        container.register_blueprint(module_blueprint, **blueprint_kwargs)

        new_blueprints.append(module_blueprint)

    return new_blueprints


def register_blueprints(
    container: Union["Flask", "Blueprint"],
    module_prefix: str,
    blueprints: Mapping[str, Any],
    route_kwargs: Mapping[str, Any],
    **kwargs,
):
    """
    Method to register multiple blueprints in `container`

    Args:
        container (Union["Flask", "Blueprint"]): a flask app object or a parent blueprint to register new blueprints in
        module_prefix: the prefix of the modules that will contain the route to register
        blueprints: configuration mapping
        route_kwargs: additional options to pass to the container register_blueprint method
        **kwargs: additional options to pass to the container register_blueprint method

    Returns:
        Blueprint: the new blueprint

    """
    # Pre-validate blueprint names so a collision fails before mutating `container`.
    # Without this, container.register_blueprint raises ValueError after earlier
    # children already merged into the container, leaving a partial URL surface.
    seen_names = set()
    duplicate_names = []
    for module, blueprints_data in blueprints.items():
        module_name = f"{module_prefix}.{module}"
        module_object = __import__(module_name, fromlist=[""])
        if not getmembers(module_object, is_register_route):
            continue

        entries = (
            blueprints_data if isinstance(blueprints_data, list) else [blueprints_data]
        )
        for entry in entries:
            if isinstance(entry, str):
                entry = {"blueprint_kwargs": {"url_prefix": entry}}
            name = entry.get("blueprint_name", module_name.split(".")[-1])
            if name in seen_names and name not in duplicate_names:
                duplicate_names.append(name)
            seen_names.add(name)
    if duplicate_names:
        raise ValueError(
            "Duplicate blueprint name(s): "
            + ", ".join(repr(name) for name in duplicate_names)
            + ". Set blueprint_name in the blueprint configuration to make each name unique."
        )

    blueprint_object = Blueprint(module_prefix.replace(".", "_"), __name__, **kwargs)

    for module, blueprints_data in blueprints.items():
        module_name = f"{module_prefix}.{module}"

        register_blueprint(
            blueprint_object, module_name, blueprints_data, route_kwargs=route_kwargs
        )

    container.register_blueprint(blueprint_object, **kwargs)

    return blueprint_object
