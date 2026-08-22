"""Shared test fixtures.

Module-global mutable state in hungrycall.web (ACTIVE_ORDERS,
CANCELED_ORDERS, _SESSION_ACTIVE_ORDER) lives for the whole Python process,
which is also the whole pytest run across every test file. Individual tests
already relied on ACTIVE_ORDERS entries being effectively invisible to each
other -- order ids are random and looked up by id, never enumerated --  but
_SESSION_ACTIVE_ORDER (E23, 2026-08-22) is the first piece of that state
that IS looked up by an implicit shared key (one session, normalized to
"__local__" outside huckepack mode -- see _session_lock_key() in web.py).
A test that starts a cascade via /api/start-cascade without draining its
/api/cascade-stream to completion would otherwise leave that key set, and
the next test's own /api/start-cascade call would see "this session already
has a cascade running" and get handed back the previous test's order
instead of starting its own.
"""

import pytest

from hungrycall import web


@pytest.fixture(autouse=True)
def _reset_cascade_session_locks():
    web._SESSION_ACTIVE_ORDER.clear()
    yield
    web._SESSION_ACTIVE_ORDER.clear()
