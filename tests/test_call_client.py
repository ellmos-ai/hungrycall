"""Credential loading and live REST tests; every network operation is mocked."""

import urllib.error
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

import pytest

from hungrycall import cli
from hungrycall.call_client import (
    CalleSettings,
    LiveCallClient,
    PreflightResult,
    load_calle_settings,
    probe_calle_connection,
)
from hungrycall.fixtures import SAMPLE_RESTAURANTS
from hungrycall.models import CallStatus, Mode, UserRequest
from hungrycall.safety import SafetyError


def write_env(path: Path, key: str = "file-fixture-token") -> None:
    path.write_text(
        f"CALLE_API_KEY={key}\nCALLE_BASE_URL=https://api.example.invalid\n",
        encoding="utf-8",
    )


def test_environment_overrides_external_env_file(tmp_path):
    env_file = tmp_path / "call-e.env"
    write_env(env_file)

    settings = load_calle_settings(
        env_file=env_file,
        environment={
            "CALLE_API_KEY": "environment-fixture-token",
            "CALLE_BASE_URL": "https://override.example.invalid/",
        },
    )

    assert settings.api_key == "environment-fixture-token"
    assert settings.base_url == "https://override.example.invalid"
    assert "environment-fixture-token" not in repr(settings)


def test_external_env_file_is_used_without_process_variables(tmp_path):
    env_file = tmp_path / "call-e.env"
    write_env(env_file)

    settings = load_calle_settings(env_file=env_file, environment={})

    assert settings.api_key == "file-fixture-token"
    assert settings.base_url == "https://api.example.invalid"
    assert settings.env_file == env_file


def test_missing_key_names_the_safe_recovery_path(tmp_path):
    missing = tmp_path / "missing.env"
    with pytest.raises(SafetyError, match="CALLE_API_KEY") as caught:
        load_calle_settings(env_file=missing, environment={})

    assert str(missing) in str(caught.value)
    assert "Dry-run is still available" in str(caught.value)


def test_preflight_is_a_get_and_treats_authenticated_404_as_success():
    settings = CalleSettings("fixture-token", "https://api.example.invalid")
    captured = []

    def fake_urlopen(request, timeout):
        captured.append((request, timeout))
        raise urllib.error.HTTPError(request.full_url, 404, "not found", {}, None)

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        result = probe_calle_connection(settings, timeout_seconds=3)

    request, timeout = captured[0]
    assert request.get_method() == "GET"
    assert request.full_url.endswith("/v1/calls/probe-does-not-exist")
    assert request.data is None
    assert timeout == 3
    assert result.status_code == 404
    assert result.authenticated is True


@pytest.mark.parametrize("status", [401, 403])
def test_preflight_reports_rejected_credentials_without_echoing_them(status):
    settings = CalleSettings("never-print-this-fixture-token", "https://api.example.invalid")

    def fake_urlopen(request, timeout):
        del timeout
        raise urllib.error.HTTPError(request.full_url, status, "denied", {}, None)

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        result = probe_calle_connection(settings)

    assert result.authenticated is False
    assert "never-print" not in result.detail
    assert result.status_code == status


def test_live_client_requires_explicit_confirmation():
    with pytest.raises(SafetyError, match="explicit confirmation"):
        LiveCallClient(CalleSettings("fixture-token"))


def test_live_rest_payload_polls_and_masks_phone_numbers():
    client = LiveCallClient(
        CalleSettings("fixture-token", "https://api.example.invalid"),
        confirmed=True,
        first_poll_seconds=0,
        poll_seconds=0,
        poll_timeout_seconds=1,
    )
    requests = []
    responses = iter([
        {"id": "rest-call-1"},
        {"status": "PREPARING", "activity": []},
        {
            "status": "COMPLETED",
            "taskCompleted": True,
            "completionConfidence": 0.93,
            "activity": [
                {"timestamp": "17:01:02", "message": "Callback +441632960090"}
            ],
            "result": {
                "structuredResult": {
                    "delivers_to_address": True,
                    "price_known": True,
                    "total_price_eur": 28.5,
                    "eta_minutes": 35,
                    "order_placed": True,
                    "callback_number": "+441632960090",
                },
                "transcript": "[00:10] USER: Call +441632960090",
            },
        },
    ])

    def fake_request(method, path, payload=None, idempotency_key=None):
        requests.append((method, path, payload, idempotency_key))
        return next(responses)

    restaurant = replace(SAMPLE_RESTAURANTS[0], phone="+44 1632 960090")
    request = UserRequest(
        mode=Mode.DELIVERY,
        customer_name="Test User",
        food_prompt="Burger",
        max_budget_eur=35,
        delivery_address="Teststraße 1",
        requester_callback_number="+4910004069000",
    )
    with patch.object(client, "_request", side_effect=fake_request):
        result = client.execute_candidate_call(restaurant, request, "stable-key")

    assert requests[0][0:2] == ("POST", "/v1/calls")
    assert requests[0][3] == "stable-key"
    assert requests[0][2]["recipients"][0]["phones"] == ["+441632960090"]
    # call_language.py: HUNGRYCALL_CALL_LOCALE unset -> German by default.
    assert requests[0][2]["recipients"][0]["locale"] == "de"
    assert requests[0][2]["recipients"][0]["region"] == "DE"
    assert "recipient_result_schema" in requests[0][2]
    assert requests[1][0:2] == ("GET", "/v1/calls/rest-call-1")
    assert result.status is CallStatus.COMPLETED
    assert result.structured_result["order_placed"] is True
    assert "+441632960090" not in result.raw_transcript_text
    assert "+441632960090" not in result.activity[0]


def test_live_payload_locale_follows_the_call_language_seam(monkeypatch):
    """call_language.py is the single seam for the CALL-E recipient's
    region/locale (2026-08-11 language seam, AGENTS.md/FINDINGS.md)."""
    from hungrycall.call_language import CALL_LOCALE_ENV

    monkeypatch.setenv(CALL_LOCALE_ENV, "en")
    client = LiveCallClient(
        CalleSettings("fixture-token", "https://api.example.invalid"),
        confirmed=True,
        first_poll_seconds=0,
        poll_seconds=0,
        poll_timeout_seconds=1,
    )
    requests = []
    responses = iter([
        {"id": "rest-call-en-1"},
        {"status": "completed", "task_completed": True, "recipients": []},
    ])

    def fake_request(method, path, payload=None, idempotency_key=None):
        requests.append((method, path, payload, idempotency_key))
        return next(responses)

    request = UserRequest(
        mode=Mode.PICKUP,
        customer_name="Test User",
        food_prompt="Pizza",
        max_budget_eur=20.0,
        pickup_time="19:30",
        requester_callback_number="+4910004069000",
    )
    with patch.object(client, "_request", side_effect=fake_request):
        client.execute_candidate_call(SAMPLE_RESTAURANTS[0], request, "lang-key-en")

    recipient = requests[0][2]["recipients"][0]
    assert recipient["locale"] == "en"
    # Documented limitation: CALL-E only confirms region "DE" as supported;
    # an English call locale still dials into Germany, not a different
    # country (call_language.py).
    assert recipient["region"] == "DE"
    assert "Hello, this is an automated assistant" in requests[0][2]["task"]
    assert "Hallo, hier spricht" not in requests[0][2]["task"]


def test_cli_preflight_prints_only_safe_metadata(tmp_path, capsys, monkeypatch):
    env_file = tmp_path / "call-e.env"
    write_env(env_file)
    settings = CalleSettings("fixture-token", "https://api.example.invalid", env_file)
    result = PreflightResult(
        base_url=settings.base_url,
        status_code=404,
        reachable=True,
        authenticated=True,
        detail="Service reachable; credential accepted.",
    )
    monkeypatch.setattr(cli, "load_calle_settings", lambda env_file=None: settings)
    monkeypatch.setattr(cli, "probe_calle_connection", lambda *args, **kwargs: result)

    assert cli.main(["preflight", "--env-file", str(env_file)]) == 0
    output = capsys.readouterr().out
    assert "no POST /v1/calls was sent" in output
    assert "fixture-token" not in output
    assert str(env_file) in output


def test_transcript_rebuilt_from_live_turns_payload():
    """Live payloads carry the conversation only as transcript_turns inside
    recipients[].attempts[] (measured 2026-08-11); the rebuilt verbatim text
    must survive so live calls stay auditable."""
    from hungrycall.call_client import LiveCallClient

    payload = {
        "status": "completed",
        "recipients": [{
            "status": "completed",
            "attempts": [{
                "status": "completed",
                "transcript_turns": [
                    {"offset_seconds": 0, "speaker": "bot",
                     "text": "Hallo, hier spricht ein automatisierter Assistent."},
                    {"offset_seconds": 65, "speaker": "user",
                     "text": "Ja, wir liefern dorthin."},
                ],
            }],
        }],
    }
    text = LiveCallClient._transcript_from_turns(payload)
    assert "[00:00] BOT: Hallo, hier spricht ein automatisierter Assistent." in text
    assert "[01:05] USER: Ja, wir liefern dorthin." in text
    assert LiveCallClient._transcript_from_turns({"status": "completed"}) == ""


def test_create_retries_with_same_idempotency_key_on_transient_failure(monkeypatch):
    """A timed-out POST may still have created a call (ghost call, 2026-08-11);
    the retry must reuse the SAME Idempotency-Key so it re-attaches instead of
    dialling twice."""
    from hungrycall.call_client import CalleSettings, LiveCallClient
    from hungrycall.fixtures import SAMPLE_RESTAURANTS
    from hungrycall.models import Mode, UserRequest

    client = LiveCallClient(
        CalleSettings(api_key="test_key_never_logged"), confirmed=True,
        poll_seconds=0, first_poll_seconds=0,
    )
    calls = []

    def fake_request(method, path, payload=None, idempotency_key=None):
        calls.append((method, path, idempotency_key))
        if method == "POST" and len([c for c in calls if c[0] == "POST"]) < 3:
            raise RuntimeError("CALL-E API was unreachable during POST /v1/calls.")
        if method == "POST":
            return {"id": "call_test123", "status": "queued"}
        return {"status": "completed", "task_completed": True, "recipients": []}

    monkeypatch.setattr(client, "_request", fake_request)
    monkeypatch.setattr("time.sleep", lambda *_: None)
    request = UserRequest(
        mode=Mode.PICKUP, customer_name="Alex Beispiel",
        food_prompt="Burger", max_budget_eur=20.0, pickup_time="19:30",
        requester_callback_number="+4910004069001",
    )
    result = client.execute_candidate_call(SAMPLE_RESTAURANTS[0], request, "idem-key-1")
    posts = [c for c in calls if c[0] == "POST"]
    assert len(posts) == 3
    assert all(key == "idem-key-1" for _, _, key in posts)
    assert result.call_id == "call_test123"


def test_recipient_answers_win_over_the_batch_envelope():
    """Measured 2026-08-11: the top-level result_schema payload
    ({'completed_count': 1}) shadowed the filled recipient answers for three
    live cascades — every real order looked like 'missing required fields'."""
    from hungrycall.call_client import LiveCallClient

    payload = {
        "status": "completed",
        "structured_result": {"completed_count": 1},
        "recipients": [{
            "structured_result": {
                "delivers_to_address": True, "price_known": True,
                "order_placed": True, "total_price_eur": 19,
            },
            "attempts": [],
        }],
    }
    result = LiveCallClient._structured_result(payload)
    assert result["order_placed"] is True
    assert "completed_count" not in result
    # Without recipient answers the envelope is still better than nothing.
    assert LiveCallClient._structured_result(
        {"structured_result": {"completed_count": 0}, "recipients": []}
    ) == {"completed_count": 0}
