"""The one thing the public Lambda dry-run demo must never do.

``demo/lambda_entry.py`` deploys with no ``CALLE_API_KEY``/``IAM_API_KEY``
configured, which already makes ``resolve_call_settings()``/
``load_calle_settings()`` fail on their own. This suite proves the second,
independent lock: with ``DEMO_MODE=1`` set, ``LiveCallClient`` refuses to be
constructed at all -- before its own ``confirmed`` check, before anything
else -- so a future change that starts passing a real key and
``confirmed=True`` through would still be refused here.
"""

from __future__ import annotations

import urllib.request

import pytest

from hungrycall.call_client import CalleSettings, LiveCallBlocked, LiveCallClient

_SETTINGS = CalleSettings(api_key="a-real-looking-key", base_url="https://api.heycall-e.com")


def test_demo_mode_blocks_even_when_fully_confirmed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEMO_MODE", "1")
    with pytest.raises(LiveCallBlocked):
        LiveCallClient(_SETTINGS, confirmed=True)


def test_demo_mode_blocks_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEMO_MODE", "1")
    monkeypatch.setenv("CALLE_API_KEY", "a-real-looking-key")
    with pytest.raises(LiveCallBlocked):
        LiveCallClient.from_environment(confirmed=True)


def test_demo_mode_never_touches_the_network(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEMO_MODE", "1")
    calls = {"count": 0}

    def _fail_if_called(*args: object, **kwargs: object) -> None:
        calls["count"] += 1
        raise AssertionError("urlopen must never be reached while DEMO_MODE=1")

    monkeypatch.setattr(urllib.request, "urlopen", _fail_if_called)
    with pytest.raises(LiveCallBlocked):
        LiveCallClient(_SETTINGS, confirmed=True)
    assert calls["count"] == 0


def test_without_demo_mode_the_confirmed_gate_still_runs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Positive control: the guard is DEMO_MODE-specific, not a blanket block."""
    monkeypatch.delenv("DEMO_MODE", raising=False)
    with pytest.raises(Exception, match="explicit confirmation"):
        LiveCallClient(_SETTINGS, confirmed=False)


def test_without_demo_mode_a_confirmed_client_is_built(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Positive control: DEMO_MODE=1 is what changes the outcome, nothing else."""
    monkeypatch.delenv("DEMO_MODE", raising=False)
    client = LiveCallClient(_SETTINGS, confirmed=True)
    assert client.settings.api_key == "a-real-looking-key"
