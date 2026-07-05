"""
Tests for app.utils.error_handlers.register_error_handlers.

Before this, every pipeline route caught RuntimeError / RequestException /
Exception locally with an identical try/except block. Centralizing them
into Flask error handlers only pays off if Flask actually dispatches to
the right one by exception type — this verifies that dispatch, plus the
one case that's easy to get wrong: a generic `Exception` handler must not
swallow Flask's own routing errors (404 for an unknown route).
"""
from flask import Flask
from requests.exceptions import RequestException

from app.utils.error_handlers import register_error_handlers


def make_app() -> Flask:
    app = Flask(__name__)
    register_error_handlers(app)

    @app.route("/boom/runtime")
    def boom_runtime():
        raise RuntimeError("mongo not initialized")

    @app.route("/boom/request")
    def boom_request():
        raise RequestException("rust engine down")

    @app.route("/boom/unexpected")
    def boom_unexpected():
        raise KeyError("something nobody expected")

    return app


def test_runtime_error_returns_500_with_pipeline_message():
    client = make_app().test_client()

    response = client.get("/boom/runtime")

    assert response.status_code == 500
    body = response.get_json()
    assert body["error"] == "Pipeline not properly initialized"
    assert "mongo not initialized" in body["details"]


def test_request_exception_returns_503_rust_engine_unreachable():
    client = make_app().test_client()

    response = client.get("/boom/request")

    assert response.status_code == 503
    body = response.get_json()
    assert body["error"] == "Rust Engine unreachable"
    assert "rust engine down" in body["details"]


def test_unexpected_exception_returns_generic_500_without_leaking_details():
    client = make_app().test_client()

    response = client.get("/boom/unexpected")

    assert response.status_code == 500
    body = response.get_json()
    assert body == {"error": "Internal server error"}


def test_unknown_route_still_returns_flasks_own_404_not_the_generic_handler():
    # The catch-all `Exception` handler must not hijack Flask's built-in
    # HTTPException handling — otherwise every 404/405 would be rewritten
    # into a generic 500 "Internal server error".
    client = make_app().test_client()

    response = client.get("/this/route/does/not/exist")

    assert response.status_code == 404
    body = response.get_json()
    assert body != {"error": "Internal server error"}
