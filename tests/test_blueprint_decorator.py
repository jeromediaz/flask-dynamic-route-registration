"""
Integration tests for flask_dynamic_route_registration.blueprint_decorator.

Covers:
- register_route decorator attribute assignment
- register_route wiring into a real Flask Blueprint
- enabled=True/False/callable routing logic
- is_register_route detection
"""

import types
from flask import Flask, Blueprint

from flask_dynamic_route_registration.blueprint_decorator import (
    register_route,
    is_register_route,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_app() -> Flask:
    """Return a minimal Flask application used for test clients."""
    return Flask(__name__)


# ---------------------------------------------------------------------------
# Tests: register_route decorator attributes
# ---------------------------------------------------------------------------


class TestRegisterRouteAttributes:
    """The decorator must stamp specific attributes onto the wrapper it returns."""

    def test_decorated_function_has_is_url_rule_attribute(self):
        """register_route must set is_url_rule=True on the returned wrapper."""

        @register_route("/ping")
        def ping_view():
            return "pong"

        assert getattr(ping_view, "is_url_rule", False) is True

    def test_decorated_function_is_a_function(self):
        """The wrapper returned by register_route must be a plain function."""

        @register_route("/ping")
        def ping_view():
            return "pong"

        assert isinstance(ping_view, types.FunctionType)

    def test_original_function_without_decorator_has_no_is_url_rule(self):
        """A plain function must NOT have is_url_rule."""

        def plain():
            return "plain"

        assert not hasattr(plain, "is_url_rule")

    def test_multiple_decorated_functions_are_independent(self):
        """Two separately decorated functions each carry their own is_url_rule."""

        @register_route("/a")
        def view_a():
            return "a"

        @register_route("/b")
        def view_b():
            return "b"

        assert view_a.is_url_rule is True
        assert view_b.is_url_rule is True
        # They must be different wrapper objects.
        assert view_a is not view_b


# ---------------------------------------------------------------------------
# Tests: register_route wires real routes into Flask
# ---------------------------------------------------------------------------


class TestRegisterRouteFlaskIntegration:
    """Verify that calling the wrapper registers working routes on a Blueprint."""

    def _register_and_build_client(self, blueprint: Blueprint, blueprint_kwargs=None):
        """Helper: attach a blueprint to a fresh Flask app and return test client."""
        app = _make_app()
        app.register_blueprint(blueprint, **(blueprint_kwargs or {}))
        return app.test_client()

    def test_basic_route_returns_200(self):
        """A decorated function registered on a blueprint must be reachable."""

        @register_route("/hello")
        def hello():
            return "hello world", 200

        bp = Blueprint("test_basic", __name__)
        hello(bp)  # wire the route

        client = self._register_and_build_client(bp)
        response = client.get("/hello")
        assert response.status_code == 200
        assert b"hello world" in response.data

    def test_custom_endpoint_name_is_used(self):
        """When endpoint is given, Flask must register with that endpoint name."""

        @register_route("/greet", endpoint="my_greet")
        def greet_view():
            return "greet", 200

        bp = Blueprint("test_endpoint", __name__)
        greet_view(bp)

        app = _make_app()
        app.register_blueprint(bp)

        # The view function registered under the blueprint must be reachable
        # via url_for using the custom endpoint.
        with app.test_request_context():
            from flask import url_for

            url = url_for("test_endpoint.my_greet")
        assert url == "/greet"

    def test_default_endpoint_uses_function_name(self):
        """When no endpoint is given, Flask uses the decorated function name."""

        @register_route("/status")
        def status_view():
            return "ok", 200

        bp = Blueprint("test_default_ep", __name__)
        status_view(bp)

        app = _make_app()
        app.register_blueprint(bp)

        with app.test_request_context():
            from flask import url_for

            url = url_for("test_default_ep.status_view")
        assert url == "/status"

    def test_route_with_methods_kwarg(self):
        """Extra rule_kwargs such as methods are forwarded to Blueprint.route."""

        @register_route("/submit", methods=["POST"])
        def submit():
            return "submitted", 201

        bp = Blueprint("test_methods", __name__)
        submit(bp)

        client = self._register_and_build_client(bp)
        assert client.post("/submit").status_code == 201
        # GET must not be allowed (Flask returns 405 for disallowed methods).
        assert client.get("/submit").status_code == 405

    def test_route_with_url_prefix(self):
        """The wrapper works when the blueprint is registered with a url_prefix."""

        @register_route("/info")
        def info():
            return "info", 200

        bp = Blueprint("test_prefix", __name__)
        info(bp)

        client = self._register_and_build_client(bp, {"url_prefix": "/api/v1"})
        assert client.get("/api/v1/info").status_code == 200
        assert client.get("/info").status_code == 404

    def test_params_are_passed_as_defaults(self):
        """Keyword arguments supplied to the wrapper are forwarded as defaults."""
        from flask import jsonify

        @register_route("/versioned")
        def versioned(*, version: int = 0):
            return jsonify({"version": version}), 200

        bp = Blueprint("test_params", __name__)
        versioned(bp, version=42)

        client = self._register_and_build_client(bp)
        response = client.get("/versioned")
        assert response.status_code == 200
        data = response.get_json()
        assert data["version"] == 42

    def test_route_with_url_variable(self):
        """Routes with URL variables are properly forwarded to Blueprint.route."""

        @register_route("/item/<int:item_id>")
        def get_item(item_id: int):
            return f"item {item_id}", 200

        bp = Blueprint("test_url_var", __name__)
        get_item(bp)

        client = self._register_and_build_client(bp)
        assert client.get("/item/7").status_code == 200
        assert b"item 7" in client.get("/item/7").data


# ---------------------------------------------------------------------------
# Tests: enabled flag
# ---------------------------------------------------------------------------


class TestRegisterRouteEnabled:
    """enabled=True/False/callable must gate route registration."""

    def _bp_client(self, bp: Blueprint, url_prefix: str = ""):
        app = _make_app()
        app.register_blueprint(bp, url_prefix=url_prefix)
        return app.test_client()

    def test_enabled_true_registers_route(self):
        """enabled=True (default) registers the route normally."""

        @register_route("/active", enabled=True)
        def active():
            return "active", 200

        bp = Blueprint("enabled_true", __name__)
        active(bp)
        assert self._bp_client(bp).get("/active").status_code == 200

    def test_enabled_false_prevents_registration(self):
        """enabled=False must skip blueprint.route, leaving route absent (404)."""

        @register_route("/inactive", enabled=False)
        def inactive():
            return "inactive", 200

        bp = Blueprint("enabled_false", __name__)
        inactive(bp)
        assert self._bp_client(bp).get("/inactive").status_code == 404

    def test_enabled_callable_returning_true_registers_route(self):
        """A callable enabled that returns True must register the route."""

        @register_route("/cond_yes", enabled=lambda **params: True)
        def cond_yes():
            return "yes", 200

        bp = Blueprint("enabled_callable_true", __name__)
        cond_yes(bp)
        assert self._bp_client(bp).get("/cond_yes").status_code == 200

    def test_enabled_callable_returning_false_prevents_registration(self):
        """A callable enabled that returns False must skip route registration."""

        @register_route("/cond_no", enabled=lambda **params: False)
        def cond_no():
            return "no", 200

        bp = Blueprint("enabled_callable_false", __name__)
        cond_no(bp)
        assert self._bp_client(bp).get("/cond_no").status_code == 404

    def test_enabled_callable_receives_params(self):
        """The enabled callable must receive the **params passed to the wrapper."""
        received_params = {}

        def check_params(**params):
            received_params.update(params)
            return True

        @register_route("/param_check", enabled=check_params)
        def param_check(*, version: int = 0):
            return "ok", 200

        bp = Blueprint("enabled_params", __name__)
        param_check(bp, version=99)

        assert received_params.get("version") == 99

    def test_enabled_callable_version_condition_per_blueprint(self):
        """Realistic scenario: same route enabled for v2 but not v1."""
        from flask import jsonify

        @register_route("/foo", enabled=lambda **params: params.get("version", 1) >= 2)
        def foo(*, version: int = 1):
            return jsonify({"version": version}), 200

        app = _make_app()

        bp_v1 = Blueprint("v1", __name__)
        foo(bp_v1, version=1)
        app.register_blueprint(bp_v1, url_prefix="/api/1")

        bp_v2 = Blueprint("v2", __name__)
        foo(bp_v2, version=2)
        app.register_blueprint(bp_v2, url_prefix="/api/2")

        client = app.test_client()
        # Route must not exist for v1
        assert client.get("/api/1/foo").status_code == 404
        # Route must exist for v2
        assert client.get("/api/2/foo").status_code == 200


# ---------------------------------------------------------------------------
# Tests: is_register_route detection
# ---------------------------------------------------------------------------


class TestIsRegisterRoute:
    """is_register_route must correctly classify callables."""

    def test_returns_true_for_decorated_function(self):
        """A function decorated with register_route must pass is_register_route."""

        @register_route("/check")
        def check():
            return "ok"

        assert is_register_route(check) is True

    def test_returns_false_for_plain_function(self):
        """An ordinary function must NOT pass is_register_route."""

        def plain():
            return "plain"

        assert is_register_route(plain) is False

    def test_returns_false_for_none(self):
        """None is not a FunctionType so is_register_route must return False."""
        assert is_register_route(None) is False

    def test_returns_false_for_integer(self):
        """An integer is not a FunctionType so is_register_route must return False."""
        assert is_register_route(42) is False

    def test_returns_false_for_lambda(self):
        """A bare lambda with no is_url_rule attribute must return False."""
        lam = lambda: None  # noqa: E731
        assert is_register_route(lam) is False

    def test_returns_false_for_class_instance(self):
        """A class instance is not a FunctionType, so it must return False."""

        class MyCallable:
            def __call__(self):
                # nothing to do
                pass

        assert is_register_route(MyCallable()) is False

    def test_returns_false_for_function_with_is_url_rule_false(self):
        """A function where is_url_rule is explicitly False must return False."""

        def sneaky():
            # nothing to do
            pass

        sneaky.is_url_rule = False
        assert is_register_route(sneaky) is False

    def test_returns_true_for_function_with_is_url_rule_manually_set(self):
        """A plain function with is_url_rule=True manually should pass (duck-typing)."""

        def manual():
            # nothing to do
            pass

        manual.is_url_rule = True
        assert is_register_route(manual) is True
