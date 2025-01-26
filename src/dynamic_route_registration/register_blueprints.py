from inspect import getmembers
from typing import Mapping, Any, TYPE_CHECKING, Union, List

from flask import Blueprint

from .blueprint_decorator import is_register_route

if TYPE_CHECKING:
    from flask.app import Flask

def register_blueprint(
    container: Union["Flask", "Blueprint"], module_name: str, blueprints_data: Union[str, Any, List[str | Any]]
):
    """
    Method to register a blueprint inside `container`

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

    new_blueprints: List[Blueprint] = []

    for blueprint_data in blueprints_data:
        if isinstance(blueprint_data, str):
            blueprint_data = {"blueprint_kwargs": {"url_prefix": blueprint_data}}

        blueprint_name = blueprint_data.get(
            "blueprint_name", module_object.__name__.split(".")[-1]
        )
        blueprint_kwargs = blueprint_data.get("blueprint_kwargs", {})
        params = blueprint_data.get("params", {})
        module_blueprint = Blueprint(blueprint_name, module_object.__name__)

        for register_route in functions:
            register_route[1](module_blueprint, **params)

        container.register_blueprint(module_blueprint, **blueprint_kwargs)

        new_blueprints.append(module_blueprint)

    return new_blueprints

def register_blueprints(
    container: Union["Flask", "Blueprint"], module_prefix: str, blueprints: Mapping[str, Any], **kwargs
):
    """
    Method to register multiple blueprints in `container`

    Args:
        container (Union["Flask", "Blueprint"]): a flask app object or a parent blueprint to register new blueprints in
        module_prefix: the prefix of the modules that will contain the route to register
        blueprints: configuration mapping
        **kwargs: additional options to pass to the container register_blueprint method

    Returns:
        Blueprint: the new blueprint

    """
    blueprint_object = Blueprint(module_prefix.replace(".", "_"), __name__, **kwargs)

    for module, blueprints_data in blueprints.items():
        module_name = f"{module_prefix}.{module}"

        register_blueprint(blueprint_object, module_name, blueprints_data)

    container.register_blueprint(blueprint_object, **kwargs)

    return blueprint_object
