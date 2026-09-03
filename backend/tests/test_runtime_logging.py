import errno
import io
import json
import logging
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from test_production_readiness import production_settings

from app.core.logging import JSONFormatter, RuntimeExceptionFilter, configure_logging


def test_runtime_exception_filter_preserves_safe_operational_information() -> None:
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JSONFormatter())
    logger = logging.Logger("uvicorn.error")
    logger.addFilter(RuntimeExceptionFilter())
    logger.addHandler(handler)
    marker = "VERY_SECRET_EXCEPTION_MARKER"
    try:
        raise ValueError(marker)
    except ValueError:
        logger.exception("Unhandled task: %s", marker)
    logger.error(OSError(errno.EADDRINUSE, marker))
    logger.error("Traceback (most recent call last):\n%s", marker)
    logger.warning("Application startup failed. Exiting.")
    output = stream.getvalue()
    assert marker not in output
    assert "Traceback" not in output
    events = [json.loads(line) for line in output.splitlines()]
    assert events[0]["exception_type"] == "ValueError"
    assert events[1]["errno"] == errno.EADDRINUSE
    assert events[-1]["event"] == "Application startup failed. Exiting."


def test_runtime_debug_logging_is_restored_outside_production() -> None:
    settings = production_settings()
    configure_logging(settings.model_copy(update={"app_env": "test"}))
    logger = logging.getLogger("asyncio")
    original = (logger.handlers[:], logger.level, logger.propagate)
    try:
        configure_logging(settings)
        assert any(isinstance(item, RuntimeExceptionFilter) for item in logger.filters)
    finally:
        configure_logging(settings.model_copy(update={"app_env": "test"}))
    assert (logger.handlers, logger.level, logger.propagate) == original
    assert not any(isinstance(item, RuntimeExceptionFilter) for item in logger.filters)


def test_real_uvicorn_production_exception_and_host_boundaries() -> None:
    # Separate process exercises Uvicorn's actual post-response exception log path.
    settings = production_settings(integration_token_encryption_key=None)
    environment = dict(os.environ)
    environment.update(
        {
            key.upper(): str(value) if value is not None else ""
            for key, value in settings.model_dump().items()
        }
    )
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "runtime_logging_probe:create_probe_app",
                "--factory",
                "--app-dir",
                str(Path(__file__).parent),
                "--fd",
                str(listener.fileno()),
                "--no-access-log",
            ],
            env=environment,
            pass_fds=(listener.fileno(),),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        try:

            def request(path, host="api.example.com"):
                return urlopen(
                    Request(
                        f"http://127.0.0.1:{port}{path}",
                        headers={"Host": host, "X-Request-ID": "runtime-regression"},
                    ),
                    timeout=2,
                )

            deadline = time.monotonic() + 20
            while True:
                try:
                    with request("/health") as response:
                        assert response.status == 200
                    break
                except (URLError, TimeoutError):
                    if process.poll() is not None or time.monotonic() >= deadline:
                        raise AssertionError("Uvicorn test server did not become ready") from None
                    time.sleep(0.05)
            try:
                request("/health", "untrusted.example.test")
                raise AssertionError("Untrusted host accepted")
            except HTTPError as response:
                assert response.code == 400
                response.close()
            try:
                request("/forced-error")
                raise AssertionError("Expected a safe 500 response")
            except HTTPError as response:
                body = response.read().decode()
                assert response.code == 500
                assert "VERY_SECRET_EXCEPTION_MARKER" not in body
                assert json.loads(body)["error"]["request_id"] == "runtime-regression"
                response.close()
        finally:
            process.terminate()
            try:
                output, _ = process.communicate(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                output, _ = process.communicate()
        assert "VERY_SECRET_EXCEPTION_MARKER" not in output
        assert "Traceback" not in output
        events = [json.loads(line) for line in output.splitlines() if line.startswith("{")]
        assert any(
            e["event"] == "unhandled_application_error" and e["request_id"] == "runtime-regression"
            for e in events
        )
        assert any(e["event"] == "runtime_exception" for e in events)
        assert any("Application startup complete" in e["event"] for e in events)
