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
                {"timestamp": "17:01:02", "message": "Callback +491701234567"}
            ],
            "result": {
                "structuredResult": {
                    "delivers_to_address": True,
                    "price_known": True,
                    "total_price_eur": 28.5,
                    "eta_minutes": 35,
                    "order_placed": True,
                    "callback_number": "+491701234567",
                },
                "transcript": "[00:10] USER: Call +491701234567",
            },
        },
    ])

    def fake_request(method, path, payload=None, idempotency_key=None):
        requests.append((method, path, payload, idempotency_key))
        return next(responses)

    restaurant = replace(SAMPLE_RESTAURANTS[0], phone="+49 170 1234567")
    request = UserRequest(
        mode=Mode.DELIVERY,
        customer_name="Test User",
        food_prompt="Burger",
        max_budget_eur=35,
        delivery_address="Teststraße 1",
        requester_callback_number="+4917612345678",
    )
    with patch.object(client, "_request", side_effect=fake_request):
        result = client.execute_candidate_call(restaurant, request, "stable-key")

    assert requests[0][0:2] == ("POST", "/v1/calls")
    assert requests[0][3] == "stable-key"
    assert requests[0][2]["recipients"][0]["phones"] == ["+491701234567"]
    assert "recipient_result_schema" in requests[0][2]
    assert requests[1][0:2] == ("GET", "/v1/calls/rest-call-1")
    assert result.status is CallStatus.COMPLETED
    assert result.structured_result["order_placed"] is True
    assert "+491701234567" not in result.raw_transcript_text
    assert "+491701234567" not in result.activity[0]


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
