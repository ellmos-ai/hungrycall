"""The web app answering AWS Lambda Function URL events (demo/lambda_entry.py).

`mangum` is a deployment-only dependency (the `lambda` extra in
`pyproject.toml`), not something the dry run needs — so this whole file is
skipped rather than failing on a machine that never installed it, matching how
the other web tests skip when `fastapi` is absent.

Three things this proves, in order: (1) the handler turns a
Function-URL-shaped event into the same response the local web server would
give, (2) a first-time visitor lands in the app's own restaurant fixture mode
so the demo works end-to-end without reaching a third-party lookup, and
(3) a visitor who switched that mode off is left alone on later requests.
"""

from __future__ import annotations

import os
import sys
import tempfile
import uuid
from pathlib import Path

import pytest

pytest.importorskip("fastapi", reason="web app dependencies not installed")
pytest.importorskip("mangum", reason="mangum is only needed for the Lambda entry point")

# Set before the module-level import below runs its own module-level code
# (hungrycall.web calls init_db() while being imported, and demo.lambda_entry
# builds `handler` eagerly) — otherwise this test would write into the shared
# platform temp file that a real deployment or another test run might also be
# using.
#
# Nothing outside this file depends on this value, so leaving it set for the
# rest of the pytest process is harmless. DEMO_MODE is deliberately *not* set
# here: pytest imports every test file during collection, before any test
# runs, so setting it at module scope would leak into every other test file's
# execution window regardless of any teardown here. tests/test_live_guard.py
# sets it per test function instead.
_DEMO_DB = Path(tempfile.gettempdir()) / f"hungrycall-lambda-test-{uuid.uuid4().hex}.db"
os.environ["HUNGRYCALL_DB_PATH"] = str(_DEMO_DB)

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from demo.lambda_entry import handler  # noqa: E402
from hungrycall import restaurant_test_mode  # noqa: E402


def _get(path: str = "/", cookie: str | None = None) -> dict:
    """Invoke the handler with a Function-URL (payload format 2.0) event."""
    headers = {"host": "example.lambda-url.eu-central-1.on.aws"}
    if cookie is not None:
        headers["cookie"] = cookie
    event = {
        "version": "2.0",
        "rawPath": path,
        "rawQueryString": "",
        "headers": headers,
        "requestContext": {
            "http": {"method": "GET", "path": path, "sourceIp": "203.0.113.1"},
        },
        "isBase64Encoded": False,
    }
    return handler(event, None)


def test_handler_serves_the_same_homepage_the_local_server_does():
    response = _get("/")
    assert response["statusCode"] == 200
    body = response["body"]
    assert body.lstrip().startswith("<!DOCTYPE html>")
    # The app's own title, not a string invented for this test.
    assert "I am hungry" in body


def test_first_time_visitor_is_defaulted_into_the_apps_own_fixture_mode():
    """A judge opening the public URL must not be able to send a geo lookup
    to a third-party service by accident — and must see something that works
    on the first click, without setting anything up first."""
    response = _get("/")
    set_cookies = [
        value
        for key, value in (response.get("headers") or {}).items()
        if key.lower() == "set-cookie"
    ]
    multi = response.get("cookies") or []
    combined = " ".join(set_cookies + list(multi))
    assert f"{restaurant_test_mode.COOKIE_NAME}=on" in combined


def test_a_visitor_who_switched_the_mode_off_keeps_that_choice():
    """The banner's own off-switch has to keep working: the middleware only
    fills in a default, it never overrides a decision already made."""
    response = _get("/", cookie=f"{restaurant_test_mode.COOKIE_NAME}=off")
    set_cookies = [
        value
        for key, value in (response.get("headers") or {}).items()
        if key.lower() == "set-cookie"
    ]
    multi = response.get("cookies") or []
    combined = " ".join(set_cookies + list(multi))
    assert f"{restaurant_test_mode.COOKIE_NAME}=on" not in combined
    assert response["statusCode"] == 200
