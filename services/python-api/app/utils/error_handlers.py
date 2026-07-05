from flask import jsonify
from requests.exceptions import RequestException
from werkzeug.exceptions import HTTPException

from app.utils.logger import logger


def register_error_handlers(app):
    """Central JSON responses for the exception types that were being
    caught identically in every pipeline route (RuntimeError for an
    uninitialized Mongo/pipeline extension, RequestException for an
    unreachable Rust Engine, and a blanket 500 for anything unexpected).

    Route-specific exception meanings stay local to their route instead
    of being centralized here — e.g. `ValueError` means "asteroid not
    found" in `analyze_single_neo` but "Rust Engine URL misconfigured"
    in `rust_client`, so a single global mapping for it would be wrong
    for one of the two cases.
    """

    @app.errorhandler(RuntimeError)
    def handle_runtime_error(e):
        logger.error(f"Pipeline initialization error: {e}")
        return jsonify({"error": "Pipeline not properly initialized", "details": str(e)}), 500

    @app.errorhandler(RequestException)
    def handle_request_exception(e):
        logger.error(f"Rust Engine communication error: {e}")
        return jsonify({"error": "Rust Engine unreachable", "details": str(e)}), 503

    @app.errorhandler(Exception)
    def handle_unexpected_error(e):
        # `Exception` matches every class in an HTTPException's MRO too
        # (NotFound -> HTTPException -> Exception), so without this check
        # every 404/405/etc. that Flask raises itself would be rewritten
        # into a generic 500 here instead of its real status code.
        if isinstance(e, HTTPException):
            return e

        logger.critical(f"Unexpected error: {e}")
        return jsonify({"error": "Internal server error"}), 500
