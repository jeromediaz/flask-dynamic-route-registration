"""
Integration tests for flask_dynamic_route_registration.register_blueprints.

Covers:
- register_blueprint with a module containing register_route-decorated functions
- URL prefix computation (string blueprints_data)
- Dict-based blueprints_data configuration
- List-based blueprints_data (multiple blueprints from one module)
- enabled=False prevents route from being registered
- enabled=callable gates route per-blueprint
- register_blueprints registers multiple blueprint modules under a parent prefix
- Return value is the registered Blueprint object
- Module with no decorated functions returns early (None)

Strategy for module injection:
    Because register_blueprint calls __import__(module_name), we inject synthetic
    modules into sys.modules so no real filesystem modules are required.
"""

import sys
import types
import pytest
from flask import Flask, Blueprint, jsonify

from flask_dynamic_route_registration.blueprint_decorator import register_route
from flask_dynamic_route_registration.register_blueprints import (
    register_blueprint,
    register_blueprints,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_app() -> Flask:
    return Flask(__name__)


def _make_module(name: str, **attrs) -> types.ModuleType:
    """Create a synthetic module and inject it into sys.modules.

    The caller is responsible for removing it via _cleanup_module() after use.
    """
    mod = types.ModuleType(name)
    mod.__name__ = name
    for attr_name, attr_value in attrs.items():
        setattr(mod, attr_name, attr_value)
    sys.modules[name] = mod
    return mod


def _cleanup_module(name: str) -> None:
    sys.modules.pop(name, None)
    # Also clean up any parent package stubs.
    parts = name.split(".")
    for i in range(len(parts) - 1, 0, -1):
        parent = ".".join(parts[:i])
        sys.modules.pop(parent, None)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def flask_app() -> Flask:
    return _make_app()


# ---------------------------------------------------------------------------
# Tests: register_blueprint — basic operation
# ---------------------------------------------------------------------------


class TestRegisterBlueprintBasic:
    """Core register_blueprint behavior with real Flask route dispatch."""

    def test_string_blueprints_data_registers_route_with_prefix(self, flask_app):
        """Passing a URL-prefix string as blueprints_data wires the route correctly."""

        @register_route("/ping")
        def ping():
            return "pong", 200

        mod_name = "test_rb_basic.routes"
        _make_module(mod_name, ping=ping)
        try:
            result = register_blueprint(flask_app, mod_name, "/api", route_kwargs={})
            assert result is not None
            client = flask_app.test_client()
            response = client.get("/api/ping")
            assert response.status_code == 200
            assert b"pong" in response.data
        finally:
            _cleanup_module(mod_name)

    def test_returns_list_of_blueprints(self, flask_app):
        """register_blueprint must return a list of Blueprint objects."""

        @register_route("/health")
        def health():
            return "ok", 200

        mod_name = "test_rb_returns.routes"
        _make_module(mod_name, health=health)
        try:
            result = register_blueprint(flask_app, mod_name, "/v1", route_kwargs={})
            assert isinstance(result, list)
            assert len(result) == 1
            assert isinstance(result[0], Blueprint)
        finally:
            _cleanup_module(mod_name)

    def test_blueprint_registered_on_container(self, flask_app):
        """The new blueprint must actually be attached to the Flask app."""

        @register_route("/check")
        def check():
            return "check", 200

        mod_name = "test_rb_container.routes"
        _make_module(mod_name, check=check)
        try:
            register_blueprint(flask_app, mod_name, "/x", route_kwargs={})
            # After registration the URL must be reachable.
            assert flask_app.test_client().get("/x/check").status_code == 200
        finally:
            _cleanup_module(mod_name)

    def test_module_with_no_decorated_functions_returns_none(self, flask_app):
        """register_blueprint must return None when no register_route functions exist."""

        def plain():
            return "plain"

        mod_name = "test_rb_empty.routes"
        _make_module(mod_name, plain=plain)
        try:
            result = register_blueprint(flask_app, mod_name, "/empty", route_kwargs={})
            assert result is None
        finally:
            _cleanup_module(mod_name)

    def test_blueprint_name_defaults_to_last_module_segment(self, flask_app):
        """When blueprint_name is not given, Blueprint uses the last module segment."""

        @register_route("/x")
        def x_view():
            return "x", 200

        mod_name = "myapp.api.items"
        _make_module(mod_name, x_view=x_view)
        try:
            result = register_blueprint(flask_app, mod_name, "/items", route_kwargs={})
            assert result is not None
            # Blueprint name must be the last segment of the module name.
            assert result[0].name == "items"
        finally:
            _cleanup_module(mod_name)


# ---------------------------------------------------------------------------
# Tests: register_blueprint — dict-based blueprints_data
# ---------------------------------------------------------------------------


class TestRegisterBlueprintDictData:
    """Verify dict-based blueprints_data configuration."""

    def test_dict_with_url_prefix(self, flask_app):
        """blueprint_kwargs.url_prefix controls the mount point."""

        @register_route("/data")
        def data():
            return "data", 200

        blueprint_data = {"blueprint_kwargs": {"url_prefix": "/v2"}}
        mod_name = "test_rb_dict.routes"
        _make_module(mod_name, data=data)
        try:
            result = register_blueprint(
                flask_app, mod_name, blueprint_data, route_kwargs={}
            )
            assert result is not None
            client = flask_app.test_client()
            assert client.get("/v2/data").status_code == 200
        finally:
            _cleanup_module(mod_name)

    def test_dict_with_custom_blueprint_name(self, flask_app):
        """blueprint_name key overrides the default last-segment name."""

        @register_route("/info")
        def info():
            return "info", 200

        blueprint_data = {
            "blueprint_name": "custom_name",
            "blueprint_kwargs": {"url_prefix": "/bp"},
        }
        mod_name = "test_rb_name.routes"
        _make_module(mod_name, info=info)
        try:
            result = register_blueprint(
                flask_app, mod_name, blueprint_data, route_kwargs={}
            )
            assert result is not None
            assert result[0].name == "custom_name"
        finally:
            _cleanup_module(mod_name)

    def test_dict_with_params(self, flask_app):
        """params dict is forwarded as defaults to the route wrapper."""

        @register_route("/versioned")
        def versioned(*, version: int = 0):
            return jsonify({"version": version}), 200

        blueprint_data = {
            "blueprint_kwargs": {"url_prefix": "/bp"},
            "params": {"version": 5},
        }
        mod_name = "test_rb_params.routes"
        _make_module(mod_name, versioned=versioned)
        try:
            register_blueprint(flask_app, mod_name, blueprint_data, route_kwargs={})
            response = flask_app.test_client().get("/bp/versioned")
            assert response.status_code == 200
            assert response.get_json()["version"] == 5
        finally:
            _cleanup_module(mod_name)

    def test_route_kwargs_merged_with_params(self, flask_app):
        """route_kwargs values are merged into params before route registration."""

        @register_route("/merged")
        def merged(*, extra: str = "none"):
            return jsonify({"extra": extra}), 200

        blueprint_data = {"blueprint_kwargs": {"url_prefix": "/m"}}
        mod_name = "test_rb_kwargs.routes"
        _make_module(mod_name, merged=merged)
        try:
            register_blueprint(
                flask_app,
                mod_name,
                blueprint_data,
                route_kwargs={"extra": "injected"},
            )
            response = flask_app.test_client().get("/m/merged")
            assert response.status_code == 200
            assert response.get_json()["extra"] == "injected"
        finally:
            _cleanup_module(mod_name)


# ---------------------------------------------------------------------------
# Tests: register_blueprint — list-based blueprints_data
# ---------------------------------------------------------------------------


class TestRegisterBlueprintListData:
    """Verify list-based blueprints_data creates multiple blueprints."""

    def test_list_creates_multiple_blueprints(self, flask_app):
        """A list with two dicts must create two blueprints and return both."""

        @register_route("/status")
        def status(*, version: int = 0):
            return jsonify({"version": version}), 200

        blueprints_data = [
            {
                "blueprint_name": "api_v1",
                "blueprint_kwargs": {"url_prefix": "/api/1"},
                "params": {"version": 1},
            },
            {
                "blueprint_name": "api_v2",
                "blueprint_kwargs": {"url_prefix": "/api/2"},
                "params": {"version": 2},
            },
        ]
        mod_name = "test_rb_list.routes"
        _make_module(mod_name, status=status)
        try:
            result = register_blueprint(
                flask_app, mod_name, blueprints_data, route_kwargs={}
            )
            assert result is not None
            assert len(result) == 2

            client = flask_app.test_client()
            r1 = client.get("/api/1/status")
            assert r1.status_code == 200
            assert r1.get_json()["version"] == 1

            r2 = client.get("/api/2/status")
            assert r2.status_code == 200
            assert r2.get_json()["version"] == 2
        finally:
            _cleanup_module(mod_name)

    def test_list_with_string_entry_uses_prefix(self, flask_app):
        """A string entry inside a list is treated as url_prefix."""

        @register_route("/hello")
        def hello():
            return "hello", 200

        mod_name = "test_rb_list_str.routes"
        _make_module(mod_name, hello=hello)
        try:
            result = register_blueprint(
                flask_app, mod_name, ["/greet"], route_kwargs={}
            )
            assert result is not None
            assert len(result) == 1
            assert flask_app.test_client().get("/greet/hello").status_code == 200
        finally:
            _cleanup_module(mod_name)


# ---------------------------------------------------------------------------
# Tests: enabled flag via register_blueprint
# ---------------------------------------------------------------------------


class TestRegisterBlueprintEnabled:
    """enabled flag on register_route must gate route registration end-to-end."""

    def test_enabled_false_route_not_accessible(self, flask_app):
        """enabled=False means the route is not reachable via the Flask client."""

        @register_route("/secret", enabled=False)
        def secret():
            return "secret", 200

        mod_name = "test_rb_enabled_false.routes"
        _make_module(mod_name, secret=secret)
        try:
            register_blueprint(flask_app, mod_name, "/ep", route_kwargs={})
            assert flask_app.test_client().get("/ep/secret").status_code == 404
        finally:
            _cleanup_module(mod_name)

    def test_enabled_callable_false_route_not_accessible(self, flask_app):
        """enabled=callable returning False produces a 404 for that route."""

        @register_route("/private", enabled=lambda **params: False)
        def private():
            return "private", 200

        mod_name = "test_rb_callable_false.routes"
        _make_module(mod_name, private=private)
        try:
            register_blueprint(flask_app, mod_name, "/cf", route_kwargs={})
            assert flask_app.test_client().get("/cf/private").status_code == 404
        finally:
            _cleanup_module(mod_name)

    def test_enabled_callable_version_gate(self, flask_app):
        """Realistic version gate: route exists for v2 only when version param >= 2."""

        @register_route(
            "/gated",
            enabled=lambda **params: params.get("version", 1) >= 2,
        )
        def gated(*, version: int = 1):
            return jsonify({"version": version}), 200

        blueprints_data = [
            {
                "blueprint_name": "vg_v1",
                "blueprint_kwargs": {"url_prefix": "/api/1"},
                "params": {"version": 1},
            },
            {
                "blueprint_name": "vg_v2",
                "blueprint_kwargs": {"url_prefix": "/api/2"},
                "params": {"version": 2},
            },
        ]
        mod_name = "test_rb_vgate.routes"
        _make_module(mod_name, gated=gated)
        try:
            register_blueprint(flask_app, mod_name, blueprints_data, route_kwargs={})
            client = flask_app.test_client()
            assert client.get("/api/1/gated").status_code == 404
            assert client.get("/api/2/gated").status_code == 200
        finally:
            _cleanup_module(mod_name)


# ---------------------------------------------------------------------------
# Tests: register_blueprints (plural)
# ---------------------------------------------------------------------------


class TestRegisterBlueprintsPlural:
    """register_blueprints wires multiple sub-modules under a parent blueprint."""

    def test_registers_multiple_modules(self, flask_app):
        """Each entry in the blueprints dict becomes a sub-blueprint."""

        @register_route("/alpha")
        def alpha():
            return "alpha", 200

        @register_route("/beta")
        def beta():
            return "beta", 200

        prefix = "test_rbs_multi"
        _make_module(f"{prefix}.mod_a", alpha=alpha)
        _make_module(f"{prefix}.mod_b", beta=beta)
        # Inject parent package stub so __import__ resolves correctly.
        _make_module(prefix)
        try:
            result = register_blueprints(
                flask_app,
                prefix,
                blueprints={
                    "mod_a": "/a",
                    "mod_b": "/b",
                },
                route_kwargs={},
                url_prefix="/root",
            )
            assert isinstance(result, Blueprint)
            client = flask_app.test_client()
            assert client.get("/root/a/alpha").status_code == 200
            assert client.get("/root/b/beta").status_code == 200
        finally:
            _cleanup_module(f"{prefix}.mod_a")
            _cleanup_module(f"{prefix}.mod_b")
            _cleanup_module(prefix)

    def test_returns_parent_blueprint(self, flask_app):
        """register_blueprints must return the parent Blueprint object."""

        @register_route("/item")
        def item():
            return "item", 200

        prefix = "test_rbs_return"
        _make_module(f"{prefix}.items", item=item)
        _make_module(prefix)
        try:
            result = register_blueprints(
                flask_app,
                prefix,
                blueprints={"items": "/items"},
                route_kwargs={},
            )
            assert isinstance(result, Blueprint)
        finally:
            _cleanup_module(f"{prefix}.items")
            _cleanup_module(prefix)

    def test_parent_blueprint_name_derived_from_prefix(self, flask_app):
        """Dots in module_prefix are replaced with underscores for blueprint name."""

        @register_route("/thing")
        def thing():
            return "thing", 200

        prefix = "myapp.api.v3"
        _make_module(f"{prefix}.things", thing=thing)
        _make_module("myapp.api.v3")
        _make_module("myapp.api")
        _make_module("myapp")
        try:
            result = register_blueprints(
                flask_app,
                prefix,
                blueprints={"things": "/things"},
                route_kwargs={},
            )
            assert result.name == "myapp_api_v3"
        finally:
            _cleanup_module(f"{prefix}.things")
            _cleanup_module("myapp.api.v3")
            _cleanup_module("myapp.api")
            _cleanup_module("myapp")

    def test_kwargs_forwarded_to_parent_blueprint(self, flask_app):
        """Extra **kwargs are passed to both Blueprint() and container.register_blueprint."""

        @register_route("/nested")
        def nested():
            return "nested", 200

        prefix = "test_rbs_kwargs"
        _make_module(f"{prefix}.sub", nested=nested)
        _make_module(prefix)
        try:
            register_blueprints(
                flask_app,
                prefix,
                blueprints={"sub": "/sub"},
                route_kwargs={},
                url_prefix="/outer",
            )
            client = flask_app.test_client()
            assert client.get("/outer/sub/nested").status_code == 200
        finally:
            _cleanup_module(f"{prefix}.sub")
            _cleanup_module(prefix)

    def test_module_without_routes_skipped_gracefully(self, flask_app):
        """A sub-module with no decorated functions must not raise an error."""

        def plain():
            return "plain"

        prefix = "test_rbs_skip"
        _make_module(f"{prefix}.empty", plain=plain)
        _make_module(prefix)
        try:
            result = register_blueprints(
                flask_app,
                prefix,
                blueprints={"empty": "/empty"},
                route_kwargs={},
            )
            # The parent blueprint is still returned even if the child had no routes.
            assert isinstance(result, Blueprint)
        finally:
            _cleanup_module(f"{prefix}.empty")
            _cleanup_module(prefix)

    def test_route_kwargs_propagated_to_all_sub_modules(self, flask_app):
        """route_kwargs values reach every sub-module's route wrappers."""

        @register_route("/env")
        def env_view(*, env: str = "unknown"):
            return jsonify({"env": env}), 200

        prefix = "test_rbs_rk"
        _make_module(f"{prefix}.views", env_view=env_view)
        _make_module(prefix)
        try:
            register_blueprints(
                flask_app,
                prefix,
                blueprints={"views": "/views"},
                route_kwargs={"env": "production"},
            )
            response = flask_app.test_client().get("/views/env")
            assert response.status_code == 200
            assert response.get_json()["env"] == "production"
        finally:
            _cleanup_module(f"{prefix}.views")
            _cleanup_module(prefix)

    def test_register_blueprint_with_parent_blueprint_container(self):
        """register_blueprint accepts a Blueprint as container (not just Flask app)."""

        @register_route("/sub")
        def sub():
            return "sub", 200

        mod_name = "test_rb_bp_container.routes"
        _make_module(mod_name, sub=sub)
        try:
            parent_bp = Blueprint("parent", __name__)
            register_blueprint(parent_bp, mod_name, "/child", route_kwargs={})

            app = _make_app()
            app.register_blueprint(parent_bp, url_prefix="/top")
            assert app.test_client().get("/top/child/sub").status_code == 200
        finally:
            _cleanup_module(mod_name)

    def test_route_kwargs_takes_precedence_over_params(self, flask_app):
        """route_kwargs values override same-key values in params."""

        @register_route("/kw")
        def kw_view(*, val: str = "default"):
            return jsonify({"val": val}), 200

        blueprint_data = {
            "blueprint_kwargs": {"url_prefix": "/kw"},
            "params": {"val": "from_params"},
        }
        mod_name = "test_rb_kw_precedence.routes"
        _make_module(mod_name, kw_view=kw_view)
        try:
            register_blueprint(
                flask_app, mod_name, blueprint_data, route_kwargs={"val": "from_route_kwargs"}
            )
            response = flask_app.test_client().get("/kw/kw")
            assert response.status_code == 200
            assert response.get_json()["val"] == "from_route_kwargs"
        finally:
            _cleanup_module(mod_name)

    def test_params_not_mutated_across_list_blueprints(self, flask_app):
        """params dict of first blueprint entry must not bleed into the second."""

        @register_route("/val")
        def val_view(*, x: int = 0, extra: int = 0):
            return jsonify({"x": x}), 200

        blueprints_data = [
            {
                "blueprint_name": "pm_v1",
                "blueprint_kwargs": {"url_prefix": "/pm/1"},
                "params": {"x": 10},
            },
            {
                "blueprint_name": "pm_v2",
                "blueprint_kwargs": {"url_prefix": "/pm/2"},
                "params": {"x": 20},
            },
        ]
        mod_name = "test_rb_params_mutation.routes"
        _make_module(mod_name, val_view=val_view)
        try:
            register_blueprint(flask_app, mod_name, blueprints_data, route_kwargs={"extra": 99})
            client = flask_app.test_client()
            assert client.get("/pm/1/val").get_json()["x"] == 10
            assert client.get("/pm/2/val").get_json()["x"] == 20
            # Original params dicts must not have been mutated by route_kwargs.
            assert blueprints_data[0]["params"] == {"x": 10}
            assert blueprints_data[1]["params"] == {"x": 20}
        finally:
            _cleanup_module(mod_name)

    def test_register_blueprints_without_url_prefix(self, flask_app):
        """register_blueprints without url_prefix mounts routes at root."""

        @register_route("/root_route")
        def root_route():
            return "root", 200

        prefix = "test_rbs_no_prefix"
        _make_module(f"{prefix}.views", root_route=root_route)
        _make_module(prefix)
        try:
            register_blueprints(
                flask_app,
                prefix,
                blueprints={"views": "/v"},
                route_kwargs={},
            )
            assert flask_app.test_client().get("/v/root_route").status_code == 200
        finally:
            _cleanup_module(f"{prefix}.views")
            _cleanup_module(prefix)

    def test_register_blueprints_with_parent_blueprint_container(self):
        """register_blueprints accepts a Blueprint as container."""

        @register_route("/bp_sub")
        def bp_sub():
            return "bp_sub", 200

        prefix = "test_rbs_bp_container"
        _make_module(f"{prefix}.mod", bp_sub=bp_sub)
        _make_module(prefix)
        try:
            parent = Blueprint("outer", __name__)
            register_blueprints(
                parent,
                prefix,
                blueprints={"mod": "/mod"},
                route_kwargs={},
                url_prefix="/inner",
            )
            app = _make_app()
            app.register_blueprint(parent, url_prefix="/top")
            assert app.test_client().get("/top/inner/mod/bp_sub").status_code == 200
        finally:
            _cleanup_module(f"{prefix}.mod")
            _cleanup_module(prefix)

    def test_duplicate_default_names_raise_before_partial_registration(self, flask_app):
        """Two entries whose default names collide must raise with no partial registration."""

        @register_route("/dup")
        def dup():
            return "dup", 200

        prefix = "test_rbs_dup_names"
        _make_module(f"{prefix}.views", dup=dup)
        _make_module(prefix)
        try:
            # Both entries default to the module's last segment: "views".
            blueprints_data = [
                {"blueprint_kwargs": {"url_prefix": "/one"}},
                {"blueprint_kwargs": {"url_prefix": "/two"}},
            ]
            before_map = sorted(
                (rule.rule, sorted(rule.methods or ()))
                for rule in flask_app.url_map.iter_rules()
            )
            before_blueprints = dict(flask_app.blueprints)

            with pytest.raises(ValueError) as excinfo:
                register_blueprints(
                    flask_app,
                    prefix,
                    blueprints={"views": blueprints_data},
                    route_kwargs={},
                )
            assert "views" in str(excinfo.value)

            after_map = sorted(
                (rule.rule, sorted(rule.methods or ()))
                for rule in flask_app.url_map.iter_rules()
            )
            assert after_map == before_map
            assert flask_app.blueprints == before_blueprints
        finally:
            _cleanup_module(f"{prefix}.views")
            _cleanup_module(prefix)

    def test_duplicate_names_across_modules_raise_before_partial_registration(self, flask_app):
        """Collision across two modules (same last segment) must not mount the first child."""

        @register_route("/a")
        def a_view():
            return "a", 200

        @register_route("/b")
        def b_view():
            return "b", 200

        # Two different modules whose last segments are identical.
        prefix = "test_rbs_dup_xmod"
        _make_module(f"{prefix}.pkg_a", a_view=a_view)
        _make_module(f"{prefix}.pkg_a.views", a_view=a_view)
        _make_module(f"{prefix}.pkg_b.views", b_view=b_view)
        _make_module(prefix)
        try:
            before_map = sorted(
                (rule.rule, sorted(rule.methods or ()))
                for rule in flask_app.url_map.iter_rules()
            )
            before_blueprints = dict(flask_app.blueprints)

            with pytest.raises(ValueError) as excinfo:
                register_blueprints(
                    flask_app,
                    prefix,
                    blueprints={"pkg_a.views": "/a", "pkg_b.views": "/b"},
                    route_kwargs={},
                )
            assert "views" in str(excinfo.value)

            after_map = sorted(
                (rule.rule, sorted(rule.methods or ()))
                for rule in flask_app.url_map.iter_rules()
            )
            assert after_map == before_map
            assert flask_app.blueprints == before_blueprints
        finally:
            _cleanup_module(f"{prefix}.pkg_a.views")
            _cleanup_module(f"{prefix}.pkg_b.views")
            _cleanup_module(f"{prefix}.pkg_a")
            _cleanup_module(prefix)

    def test_distinct_blueprint_names_register_both(self, flask_app):
        """Entries with distinct explicit blueprint_name values still register."""

        @register_route("/ok")
        def ok():
            return "ok", 200

        prefix = "test_rbs_distinct_names"
        _make_module(f"{prefix}.views", ok=ok)
        _make_module(prefix)
        try:
            register_blueprints(
                flask_app,
                prefix,
                blueprints={
                    "views": [
                        {
                            "blueprint_name": "views_v1",
                            "blueprint_kwargs": {"url_prefix": "/v1"},
                        },
                        {
                            "blueprint_name": "views_v2",
                            "blueprint_kwargs": {"url_prefix": "/v2"},
                        },
                    ]
                },
                route_kwargs={},
            )
            client = flask_app.test_client()
            assert client.get("/v1/ok").status_code == 200
            assert client.get("/v2/ok").status_code == 200
        finally:
            _cleanup_module(f"{prefix}.views")
            _cleanup_module(prefix)

    def test_multiple_routes_in_same_module(self, flask_app):
        """All register_route-decorated functions in a module are registered."""

        @register_route("/one")
        def one():
            return "one", 200

        @register_route("/two")
        def two():
            return "two", 200

        @register_route("/three")
        def three():
            return "three", 200

        prefix = "test_rbs_multi_routes"
        _make_module(f"{prefix}.views", one=one, two=two, three=three)
        _make_module(prefix)
        try:
            register_blueprints(
                flask_app,
                prefix,
                blueprints={"views": "/v"},
                route_kwargs={},
            )
            client = flask_app.test_client()
            assert client.get("/v/one").status_code == 200
            assert client.get("/v/two").status_code == 200
            assert client.get("/v/three").status_code == 200
        finally:
            _cleanup_module(f"{prefix}.views")
            _cleanup_module(prefix)
