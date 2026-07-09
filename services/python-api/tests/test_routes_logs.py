"""
Tests for app.routes.logs.
"""
from flask import Flask

from app.routes.logs import _parse_log_line, logs_bp


def make_app() -> Flask:
    app = Flask(__name__)
    app.register_blueprint(logs_bp)
    return app


class TestParseLogLine:
    def test_parses_well_formed_line(self):
        line = "2025-01-01 10:00:00 | INFO | app.core.pipeline | Pipeline completed"

        assert _parse_log_line(line) == {
            "timestamp": "2025-01-01 10:00:00",
            "level": "INFO",
            "logger": "app.core.pipeline",
            "message": "Pipeline completed",
        }

    def test_falls_back_for_malformed_line(self):
        assert _parse_log_line("not a structured log line") == {
            "timestamp": "", "level": "INFO", "logger": "",
            "message": "not a structured log line",
        }


class TestRecentLogs:
    def test_no_log_file_returns_empty_list(self, tmp_path, mocker):
        mocker.patch("app.routes.logs.LOG_DIRECTORY", str(tmp_path))
        client = make_app().test_client()

        response = client.get("/logs")

        assert response.status_code == 200
        assert response.get_json() == []

    def test_filters_by_level_and_reverses_order(self, tmp_path, mocker):
        mocker.patch("app.routes.logs.LOG_DIRECTORY", str(tmp_path))
        (tmp_path / "python_api.log").write_text(
            "2025-01-01 10:00:00 | INFO | app | first\n"
            "2025-01-01 10:00:01 | ERROR | app | second\n"
            "2025-01-01 10:00:02 | INFO | app | third\n"
        )
        client = make_app().test_client()

        response = client.get("/logs?level=INFO")

        body = response.get_json()
        assert [entry["message"] for entry in body] == ["third", "first"]

    def test_limit_is_respected(self, tmp_path, mocker):
        mocker.patch("app.routes.logs.LOG_DIRECTORY", str(tmp_path))
        (tmp_path / "python_api.log").write_text(
            "\n".join(f"2025-01-01 10:00:0{i} | INFO | app | msg{i}" for i in range(5)) + "\n"
        )
        client = make_app().test_client()

        response = client.get("/logs?limit=2")

        assert len(response.get_json()) == 2

    def test_query_filters_by_substring(self, tmp_path, mocker):
        mocker.patch("app.routes.logs.LOG_DIRECTORY", str(tmp_path))
        (tmp_path / "python_api.log").write_text(
            "2025-01-01 10:00:00 | INFO | app | pipeline started\n"
            "2025-01-01 10:00:01 | INFO | app | unrelated message\n"
        )
        client = make_app().test_client()

        response = client.get("/logs?query=pipeline")

        body = response.get_json()
        assert len(body) == 1
        assert "pipeline" in body[0]["message"]
