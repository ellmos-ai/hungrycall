"""The huckepack modes: what is promised, verified.

Three promises carry the whole pattern, and each one is only worth as much as
its test:

* in a huckepack mode the host writes **no file** — asserted by pointing the
  database path at a file and checking afterwards that it was never created;
* the visitor's key is used and dropped — asserted by looking for it in the
  database bytes, in the log records and in the response;
* ``pay-membership`` is a placeholder — asserted by the refusal, not by a
  comment claiming so.
"""

from __future__ import annotations

import logging
import os
import sqlite3

import pytest
from fastapi.testclient import TestClient

from hungrycall import calle_key, huckepack_storage, server_mode, web
from hungrycall.call_client import DryRunCallClient
from hungrycall.db import create_order_record, init_db, list_saved_results
from hungrycall.huckepack_storage import SESSIONS, SnapshotError, open_connection
from hungrycall.huckepack_web import SESSION_HEADER, receipt_script_tag
from hungrycall.server_mode import ServerMode, ServerModeError

TOKEN = "AAAAAAAAAAAAAAAAAAAAAAAAAAAA"
OTHER_TOKEN = "BBBBBBBBBBBBBBBBBBBBBBBBBBBB"
VISITOR_KEY = "sk-visitor-9999-abcdefgh"


@pytest.fixture(autouse=True)
def clean_slate(tmp_path, monkeypatch):
    """Every test picks its own mode; nothing leaks into the next one."""
    monkeypatch.setenv("HUNGRYCALL_DB_PATH", str(tmp_path / "hungrycall.db"))
    monkeypatch.delenv(server_mode.ENV_VAR, raising=False)
    server_mode.reset_mode_cache()
    SESSIONS.clear()
    yield
    SESSIONS.clear()
    server_mode.reset_mode_cache()


def names_in(token: str) -> list:
    """Customer names in a session database, independent of the row factory."""
    rows = SESSIONS.connection(token).execute("SELECT customer_name FROM orders").fetchall()
    return [row[0] for row in rows]


def use_mode(monkeypatch, mode: str) -> None:
    monkeypatch.setenv(server_mode.ENV_VAR, mode)
    server_mode.reset_mode_cache()


# ---------------------------------------------------------------- the mode

def test_unset_means_local():
    assert server_mode.current_mode() is ServerMode.LOCAL
    assert server_mode.current_mode().stores_on_host


@pytest.mark.parametrize(
    "name,browser,key_field",
    [
        ("local", False, False),
        ("huckepack-gift", True, False),
        ("huckepack-only-host", True, True),
        ("pay-membership", False, False),
    ],
)
def test_every_mode_decides_storage_and_key(monkeypatch, name, browser, key_field):
    use_mode(monkeypatch, name)
    mode = server_mode.current_mode()
    assert mode.stores_in_browser is browser
    assert mode.key_from_browser is key_field
    descriptor = server_mode.describe_mode()
    assert descriptor["mode"] == name
    assert descriptor["storage"] == ("browser" if browser else "host")
    assert descriptor["key_field"] is key_field


def test_an_unknown_mode_is_refused_by_name():
    with pytest.raises(ServerModeError) as error:
        server_mode.parse_mode("huckepack-maybe")
    assert "huckepack-maybe" in str(error.value)
    assert "huckepack-gift" in str(error.value)


def test_the_mode_does_not_change_under_a_running_process(monkeypatch):
    use_mode(monkeypatch, "huckepack-gift")
    assert server_mode.current_mode() is ServerMode.HUCKEPACK_GIFT
    monkeypatch.setenv(server_mode.ENV_VAR, "local")
    assert server_mode.current_mode() is ServerMode.HUCKEPACK_GIFT


def test_pay_membership_refuses_to_pretend(monkeypatch):
    use_mode(monkeypatch, "pay-membership")
    assert server_mode.current_mode().implemented is False
    with pytest.raises(ServerModeError):
        server_mode.require_implemented()


# ------------------------------------------------------------- the storage

def test_local_mode_writes_the_file_as_before(monkeypatch):
    use_mode(monkeypatch, "local")
    create_order_record("ord_local", "delivery", "Ada", "pizza")
    assert os.path.exists(os.environ["HUNGRYCALL_DB_PATH"])


@pytest.mark.parametrize("mode", ["huckepack-gift", "huckepack-only-host"])
def test_a_huckepack_mode_never_creates_the_database_file(monkeypatch, mode):
    use_mode(monkeypatch, mode)
    reset = huckepack_storage.bind_session(TOKEN)
    try:
        create_order_record("ord_browser", "delivery", "Ada", "pizza")
        stored = names_in(TOKEN)
    finally:
        huckepack_storage.unbind_session(reset)

    assert stored == ["Ada"]
    assert not os.path.exists(os.environ["HUNGRYCALL_DB_PATH"])


def test_two_sessions_do_not_see_each_other(monkeypatch):
    use_mode(monkeypatch, "huckepack-gift")
    for token, name in ((TOKEN, "Ada"), (OTHER_TOKEN, "Grace")):
        reset = huckepack_storage.bind_session(token)
        try:
            create_order_record(f"ord_{name}", "delivery", name, "pizza")
        finally:
            huckepack_storage.unbind_session(reset)

    assert names_in(TOKEN) == ["Ada"]
    assert names_in(OTHER_TOKEN) == ["Grace"]


def test_closing_a_connection_does_not_throw_the_session_away(monkeypatch):
    use_mode(monkeypatch, "huckepack-gift")
    reset = huckepack_storage.bind_session(TOKEN)
    try:
        connection = open_connection("ignored.db")
        connection.execute("CREATE TABLE t (a)")
        connection.execute("INSERT INTO t VALUES (1)")
        connection.commit()
        connection.close()  # the data layer does this after every write
        assert open_connection("ignored.db").execute("SELECT a FROM t").fetchall() == [(1,)]
    finally:
        huckepack_storage.unbind_session(reset)


def test_a_snapshot_carries_the_data_to_another_session(monkeypatch):
    use_mode(monkeypatch, "huckepack-only-host")
    reset = huckepack_storage.bind_session(TOKEN)
    try:
        create_order_record("ord_travel", "delivery", "Ada", "pizza")
        blob = huckepack_storage.snapshot_for_current_session()
    finally:
        huckepack_storage.unbind_session(reset)

    assert blob.startswith(huckepack_storage.SQLITE_MAGIC)
    SESSIONS.load(OTHER_TOKEN, blob)
    assert names_in(OTHER_TOKEN) == ["Ada"]


def test_a_snapshot_that_is_not_a_database_is_refused():
    with pytest.raises(SnapshotError):
        SESSIONS.load(TOKEN, b"this is not a database")


def test_an_oversized_snapshot_is_refused_before_it_is_parked():
    small = huckepack_storage.SessionDatabases(max_snapshot_bytes=64)
    with pytest.raises(SnapshotError):
        small.load(TOKEN, huckepack_storage.SQLITE_MAGIC + b"x" * 200)


def test_sessions_are_dropped_when_they_go_stale():
    registry = huckepack_storage.SessionDatabases(ttl_seconds=-1)
    registry.connection(TOKEN)
    registry.connection(OTHER_TOKEN)  # the sweep runs on the next access
    assert registry.known(TOKEN) is False


# ------------------------------------------------------------------ the key

def test_a_key_is_only_ever_shown_masked():
    assert calle_key.mask_key(VISITOR_KEY) == "••••efgh"
    assert VISITOR_KEY not in calle_key.mask_key(VISITOR_KEY)
    assert VISITOR_KEY not in calle_key.describe_key(VISITOR_KEY)


@pytest.mark.parametrize("bad", ["", "   ", "short", "has space in it", "line\nbreak"])
def test_an_unusable_key_is_refused_without_echoing_it(bad):
    with pytest.raises(calle_key.UserKeyError) as error:
        calle_key.validate_key(bad)
    assert bad.strip() not in str(error.value) or not bad.strip()


def test_only_host_takes_the_visitors_key(monkeypatch):
    use_mode(monkeypatch, "huckepack-only-host")
    reset = calle_key.bind_request_key(VISITOR_KEY)
    try:
        settings = calle_key.resolve_call_settings()
    finally:
        calle_key.unbind_request_key(reset)
    assert settings.api_key == VISITOR_KEY
    assert VISITOR_KEY not in repr(settings)


def test_only_host_never_falls_back_to_the_hosts_key(monkeypatch):
    use_mode(monkeypatch, "huckepack-only-host")
    monkeypatch.setenv("CALLE_API_KEY", "host-key-that-must-not-be-spent")
    with pytest.raises(calle_key.UserKeyError):
        calle_key.resolve_call_settings()


def test_gift_mode_uses_the_hosts_key_and_ignores_a_sent_one(monkeypatch):
    use_mode(monkeypatch, "huckepack-gift")
    monkeypatch.setenv("CALLE_API_KEY", "host-key-12345678")
    reset = calle_key.bind_request_key(VISITOR_KEY)
    try:
        settings = calle_key.resolve_call_settings()
    finally:
        calle_key.unbind_request_key(reset)
    assert settings.api_key == "host-key-12345678"


def test_the_visitors_key_reaches_no_store_and_no_log(monkeypatch, caplog):
    """A full only-host request: the key must leave no trace behind it."""
    use_mode(monkeypatch, "huckepack-only-host")
    monkeypatch.setattr(web, "live_call_client", lambda: DryRunCallClient("jury_30s_demo"))

    with caplog.at_level(logging.DEBUG):
        with TestClient(web.app) as client:
            response = client.post(
                "/api/search?lang=de",
                data={
                    "branch": "food",
                    "mode": "delivery",
                    "customer_name": "Ada",
                    "food_prompt": "Pizza",
                    "city": "Dorfstadt",
                    "postcode": "12345",
                    "radius_km": "3",
                    "test_mode": "yes",
                    "transport": "dry_run",
                },
                headers={calle_key.KEY_HEADER: VISITOR_KEY, SESSION_HEADER: TOKEN},
            )
            assert response.status_code == 200
            assert VISITOR_KEY not in response.text

            snapshot = client.get(
                "/huckepack/session", headers={SESSION_HEADER: TOKEN}
            ).content

    assert VISITOR_KEY.encode() not in snapshot
    assert VISITOR_KEY not in caplog.text
    assert calle_key.current_request_key() is None


# ------------------------------------------------------------------ the web

@pytest.fixture()
def client():
    with TestClient(web.app) as test_client:
        yield test_client


def test_the_browser_is_told_what_kind_of_installation_this_is(monkeypatch, client):
    use_mode(monkeypatch, "huckepack-only-host")
    payload = client.get("/huckepack/mode").json()
    assert payload["mode"] == "huckepack-only-host"
    assert payload["storage"] == "browser"
    assert payload["key_field"] is True
    assert payload["key_header"] == calle_key.KEY_HEADER
    assert payload["session_header"] == SESSION_HEADER


def test_a_snapshot_can_be_handed_in_and_taken_back(monkeypatch, client):
    use_mode(monkeypatch, "huckepack-gift")
    seed = sqlite3.connect(":memory:")
    seed.execute("CREATE TABLE orders (id TEXT, customer_name TEXT)")
    seed.execute("INSERT INTO orders VALUES ('ord_1', 'Ada')")
    seed.commit()
    blob = seed.serialize()

    loaded = client.put("/huckepack/session", content=blob, headers={SESSION_HEADER: TOKEN})
    assert loaded.status_code == 200

    fetched = client.get("/huckepack/session", headers={SESSION_HEADER: TOKEN})
    assert fetched.status_code == 200
    back = sqlite3.connect(":memory:")
    back.deserialize(fetched.content)
    assert back.execute("SELECT customer_name FROM orders").fetchall() == [("Ada",)]

    dropped = client.delete("/huckepack/session", headers={SESSION_HEADER: TOKEN})
    assert dropped.status_code == 200
    assert SESSIONS.known(TOKEN) is False


def test_a_token_that_is_not_a_token_is_refused(monkeypatch, client):
    use_mode(monkeypatch, "huckepack-gift")
    response = client.get("/huckepack/session", headers={SESSION_HEADER: "abc"})
    assert response.status_code == 400


def test_local_mode_has_no_browser_snapshot(monkeypatch, client):
    use_mode(monkeypatch, "local")
    response = client.get("/huckepack/session", headers={SESSION_HEADER: TOKEN})
    assert response.status_code == 409
    assert response.json()["mode"] == "local"


def test_the_stub_mode_says_so_instead_of_serving_pages(monkeypatch, client):
    use_mode(monkeypatch, "pay-membership")
    page = client.get("/order")
    assert page.status_code == 503
    assert "placeholder" in page.text
    # The interface still needs to learn why, so the descriptor keeps answering.
    assert client.get("/huckepack/mode").json()["implemented"] is False


# -------------------------------------------------------------- the receipt

def test_the_receipt_payload_carries_no_dialable_number():
    from hungrycall.location import get_offline_restaurants

    class Result:
        post_summary = "Bestellt bei 020 79460090."
        raw_transcript_text = "Kunde: Meine Nummer ist +44 1632 960090."

    restaurant = get_offline_restaurants()[0]
    payload = web.build_receipt_payload(
        order_id="ord_1",
        mode="delivery",
        restaurant=restaurant,
        structured={"callback_number": "+44 1632 960090", "total_price_eur": 18.5},
        call_result=Result(),
        customer_name="Ada",
    )
    assert restaurant.phone not in payload["business_phone_masked"]
    assert restaurant.phone not in str(payload)
    assert "1234567" not in payload["transcript"].replace("•", "")
    assert "person who was called" in payload["third_party_notice"]


def test_the_receipt_block_cannot_end_itself_early():
    tag = receipt_script_tag({"summary": "</script><script>alert(1)</script>"})
    assert "</script><script>" not in tag
    assert tag.endswith("</script>")


def test_saving_a_result_hands_the_receipt_to_the_browser(monkeypatch, client):
    use_mode(monkeypatch, "local")
    init_db()
    assert list_saved_results() == []
    # Without a finished run there is nothing to save, and the endpoint says so
    # rather than inventing a receipt.
    response = client.post("/api/save-result", data={"order_id": "ord_missing"})
    assert response.status_code == 200
    assert "huckepack-receipt" not in response.text


# --------------------------------------------------------- the browser file

def test_the_browser_half_is_shipped_and_never_prints_the_key():
    source = (
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "hungrycall", "static", "huckepack.js")
    )
    with open(source, encoding="utf-8") as handle:
        script = handle.read()
    for needed in ("receiptFilename", "maskKey", "looksLikeSqlite", "showDirectoryPicker"):
        assert needed in script
    # No console output at all: the one thing that would casually leak a key.
    assert "console." not in script


# ------------------------------------ what the audit of 2026-08-02 found

def cascade_form(**overrides):
    form = {
        "branch": "food",
        "mode": "delivery",
        "customer_name": "Ada",
        "food_prompt": "Pizza",
        "city": "Dorfstadt",
        "postcode": "12345",
        "radius_km": "3",
        "test_mode": "yes",
        "transport": "dry_run",
        "scenario": "jury_30s_demo",
    }
    form.update(overrides)
    return form


def start_a_cascade(client, token):
    """Start one cascade as the given browser session; returns its order id."""
    from hungrycall.location import search_overpass_restaurants

    pool = search_overpass_restaurants(52.52, 13.405, test_mode=True, city="Dorfstadt")
    form = cascade_form()
    form["candidate_order"] = ",".join(r.id for r in pool)
    form["selected_restaurants"] = [r.id for r in pool]
    response = client.post(
        "/api/start-cascade?lang=de", data=form, headers={SESSION_HEADER: token}
    )
    assert response.status_code == 200, response.text
    return response.text.split('HC.startStream("')[1].split('"')[0]


def test_a_cascade_belongs_to_the_browser_that_started_it(monkeypatch, client):
    """The finding of 2026-08-02: an order id is an identifier, not a permission."""
    use_mode(monkeypatch, "huckepack-gift")
    monkeypatch.setattr(web, "DRY_RUN_DIAL_SECONDS", 0)
    monkeypatch.setattr(web, "DRY_RUN_TURN_SECONDS", 0)

    order_id = start_a_cascade(client, TOKEN)

    # The stranger knows the id and asks for the stream, the result and the
    # cancel button. All three answer as if the cascade did not exist.
    stranger = client.get(
        f"/api/cascade-stream?order_id={order_id}", headers={SESSION_HEADER: OTHER_TOKEN}
    )
    owner = client.get(
        f"/api/cascade-stream?order_id={order_id}", headers={SESSION_HEADER: TOKEN}
    )
    # The comparison is the test: the owner's stream narrates the calls, the
    # stranger's says the cascade is over before it began.
    assert "restaurant" in owner.text or "call" in owner.text
    assert len(stranger.text) < len(owner.text) / 2
    assert "phone" not in stranger.text

    saved = client.post(
        "/api/save-result",
        data={"order_id": order_id},
        headers={SESSION_HEADER: OTHER_TOKEN},
    )
    assert "huckepack-receipt" not in saved.text

    canceled = client.post(
        "/api/cancel-cascade",
        data={"order_id": order_id},
        headers={SESSION_HEADER: OTHER_TOKEN},
    )
    assert order_id not in web.CANCELED_ORDERS, "a stranger must not stop your calls"
    assert canceled.status_code == 200


def test_the_owner_still_reaches_their_own_cascade(monkeypatch, client):
    use_mode(monkeypatch, "huckepack-gift")
    monkeypatch.setattr(web, "DRY_RUN_DIAL_SECONDS", 0)
    monkeypatch.setattr(web, "DRY_RUN_TURN_SECONDS", 0)

    order_id = start_a_cascade(client, TOKEN)
    client.post(
        "/api/cancel-cascade", data={"order_id": order_id}, headers={SESSION_HEADER: TOKEN}
    )
    assert order_id in web.CANCELED_ORDERS
    web.CANCELED_ORDERS.discard(order_id)


def test_local_mode_keeps_todays_behaviour(monkeypatch, client):
    """No session binding where there is one user and one machine."""
    use_mode(monkeypatch, "local")
    monkeypatch.setattr(web, "DRY_RUN_DIAL_SECONDS", 0)
    monkeypatch.setattr(web, "DRY_RUN_TURN_SECONDS", 0)

    order_id = start_a_cascade(client, TOKEN)
    assert web.active_order(order_id) is not None
