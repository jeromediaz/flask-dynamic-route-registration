import types
from typing import Optional, Callable, Union, cast, TYPE_CHECKING, Any
from typing_extensions import Protocol

if TYPE_CHECKING:
    from flask import Blueprint

class EndpointEnabledCallback(Protocol):
    def __call__(self, **params: Any) -> bool: ...

def register_route(rule: str, endpoint: Optional[str] = None, **rule_kwargs):
    """Function to create a decorator to register a route.

    Args:
        rule (str): the rule argument to regis
        endpoint (str, optional): name to use for the endpoint, if not given the decorated function name will be used
        **rule_kwargs: keyword arguments to pass to the rule

    Returns:
        Callable: a decorator function

    """

    def my_decorator(func):
        final_endpoint = endpoint if endpoint else func.__name__

        def wrapper(blueprint: "Blueprint", **params):
            endpoint_enabled = cast(
                Union[EndpointEnabledCallback | bool], rule_kwargs.pop("enabled", True)
            )

            if callable(endpoint_enabled):
                endpoint_enabled_func = cast(EndpointEnabledCallback, endpoint_enabled)
                endpoint_enabled = endpoint_enabled_func(**params)

            if endpoint_enabled:
                blueprint.route(
                    rule, endpoint=final_endpoint, defaults=params, **rule_kwargs
                )(func)

        wrapper.is_url_rule = True
        return wrapper

    return my_decorator


def is_register_route(func) -> bool:
    return isinstance(func, types.FunctionType) and getattr(func, "is_url_rule", False)
