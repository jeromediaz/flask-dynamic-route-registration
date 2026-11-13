import types
from typing import TYPE_CHECKING, Any, cast

from typing_extensions import Protocol
from werkzeug.routing import Map, Rule

if TYPE_CHECKING:
    from flask import Blueprint


class EndpointEnabledCallback(Protocol):
    def __call__(self, **params: Any) -> bool: ...


def register_route(rule: str, endpoint: str | None = None, **rule_kwargs):
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
                EndpointEnabledCallback | bool, rule_kwargs.get("enabled", True)
            )

            if callable(endpoint_enabled):
                endpoint_enabled = endpoint_enabled(**params)

            if not isinstance(endpoint_enabled, bool):
                raise TypeError(
                    f"enabled gate for endpoint {final_endpoint!r} must return a bool, "
                    f"got {endpoint_enabled!r} of type {type(endpoint_enabled).__name__}"
                )

            if endpoint_enabled:
                route_kw = {k: v for k, v in rule_kwargs.items() if k != "enabled"}
                # Rule.arguments is only populated once the rule is bound to a
                # map, so bind a throwaway Map to extract the URL variables.
                rule_map = Map()
                bound_rule = Rule(rule)
                rule_map.add(bound_rule)
                url_variables = bound_rule.arguments
                colliding_params = sorted(set(params) & url_variables)
                if colliding_params:
                    raise ValueError(
                        f"params {colliding_params!r} collide with URL variables in rule {rule!r}; "
                        "defaults would override client path values"
                    )
                blueprint.route(
                    rule, endpoint=final_endpoint, defaults=params, **route_kw
                )(func)

        wrapper.is_url_rule = True
        return wrapper

    return my_decorator


def is_register_route(func) -> bool:
    return isinstance(func, types.FunctionType) and getattr(func, "is_url_rule", False)
