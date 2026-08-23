"""Run the web interface as an AWS Lambda function behind a Function URL.

The target for the public dry-run demo is a Lambda Function URL, the same
pattern already deployed for the two sibling apps of this submission
(`ringedingeding`, `researchcall`) and for `roshambo` before them. This module
is the whole of the adaptation: one Mangum wrapper over the very same
`hungrycall.web:app` that `START-WEB.bat` and `python -m uvicorn` serve
locally. There is deliberately no second code path.

    # Lambda handler:  demo.lambda_entry.handler
    # Local:           uvicorn hungrycall.web:app

What this deployment must never do
-----------------------------------

No `CALLE_API_KEY` (or any `CALLE_*` credential) is ever set in this Lambda's
environment — the deploy script (`infra/deploy_demo_lambda.py`) does not pass
one, by construction. That alone would already make every live-call attempt
fail for want of a key. On top of it, the deploy script sets `DEMO_MODE=1` in
the Lambda's own environment configuration, which
`hungrycall.call_client.LiveCallClient.__init__` checks *before* its own
`confirmed` gate and before the credential resolver, and refuses
unconditionally (`LiveCallBlocked`). Two independent locks on the same door:
losing one of them (a misconfigured environment, a future refactor of the key
resolver) still leaves the other standing. `tests/test_live_guard.py` proves
both the refusal itself and that no socket is opened.

This holds for the E41 correction call too: it is dispatched through the same
`execute_candidate_call()` pipeline and therefore through the same
`LiveCallClient` seam, so the demo's "Korrekturanruf auslösen" button reaches
the identical refusal instead of dialling anyone.

Deliberately, **this module never sets `DEMO_MODE` itself.** Importing it must
stay free of that particular global side effect: pytest imports every test
module during collection, so a `setdefault` here would silently block
unrelated live-client construction in other test files. The real Lambda gets
`DEMO_MODE=1` from its environment configuration; a test sets it in its own
scope and restores it afterwards.

What a judge sees
------------------

`hungrycall.restaurant_test_mode` is the app's own, pre-existing fixture mode:
it swaps the live restaurant lookup for a bundled set of example restaurants
and shows a banner saying so. It is normally opt-in per browser (a cookie).
For this deployment `_TestModeDefaultMiddleware` turns it on for a visitor who
has not chosen otherwise — so the first page a judge loads already works
end-to-end, and a stray click cannot send a geo query to a third-party lookup
service from a public URL. A visitor can still switch it off through the
banner's own link; that choice is respected on every later request.

No fixture mode of the app's own was reinvented here, and no demo data was
made up: what the demo shows is what the repository already ships.

Ephemeral by design
--------------------

The database lives in the execution environment's own scratch space
(`tempfile.gettempdir()`, which resolves to Lambda's `/tmp` and to a normal OS
temp directory on a developer machine). State resets whenever AWS recycles the
sandbox; nothing here is meant to persist. `HUNGRYCALL_DB_PATH` has to be set
*before* `hungrycall.web` is imported, because importing that module calls
`init_db()` at module scope — hence the explicit ordering below, and the
`# noqa: E402` markers that go with it.

`lifespan="off"` because Lambda never delivers a startup or shutdown event
between invocations of a frozen execution environment.
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

DEMO_DB_PATH_ENV = "HUNGRYCALL_DB_PATH"
"""The app's own database override. Left unset by the deploy script, so this
module points it at the platform temp directory — correct on Lambda (`/tmp`,
the only writable location there) and on a developer machine alike, without
hard-coding a POSIX-only path."""


def _db_path() -> str:
    override = os.environ.get(DEMO_DB_PATH_ENV)
    if override:
        return override
    return str(Path(tempfile.gettempdir()) / "hungrycall-demo.db")


# Must precede the `hungrycall.web` import: that module calls init_db() while
# being imported, and would otherwise create the database in the read-only
# deployment directory.
os.environ[DEMO_DB_PATH_ENV] = _db_path()

from mangum import Mangum  # noqa: E402

from hungrycall import restaurant_test_mode  # noqa: E402
from hungrycall.web import app  # noqa: E402


class _TestModeDefaultMiddleware:
    """Default a first-time visitor into the app's own restaurant fixture mode.

    Pure ASGI middleware rather than Starlette's `BaseHTTPMiddleware`: the
    cookie has to be visible to the *current* request (the app reads
    `request.cookies` while rendering), not only to the next one, so the
    header is injected into the request scope before the app sees it and the
    `Set-Cookie` is appended to the response on the way out.

    A visitor who has already chosen — either value — is left alone: the
    banner's own off-switch keeps working exactly as it does locally.
    """

    COOKIE = restaurant_test_mode.COOKIE_NAME

    def __init__(self, application):
        self.app = application

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = list(scope.get("headers") or [])
        cookie_header = ""
        for key, value in headers:
            if key.lower() == b"cookie":
                cookie_header = value.decode("latin-1")
                break

        already_chosen = f"{self.COOKIE}=" in cookie_header
        if not already_chosen:
            merged = f"{cookie_header}; {self.COOKIE}=on" if cookie_header else f"{self.COOKIE}=on"
            headers = [(k, v) for k, v in headers if k.lower() != b"cookie"]
            headers.append((b"cookie", merged.encode("latin-1")))
            scope = dict(scope, headers=headers)

        async def send_with_cookie(message):
            if not already_chosen and message["type"] == "http.response.start":
                message = dict(message)
                message["headers"] = [
                    *(message.get("headers") or []),
                    (b"set-cookie", f"{self.COOKIE}=on; Path=/; SameSite=Lax".encode("latin-1")),
                ]
            await send(message)

        await self.app(scope, receive, send_with_cookie)


handler = Mangum(_TestModeDefaultMiddleware(app), lifespan="off")
