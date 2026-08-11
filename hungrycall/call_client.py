"""CALL-E transports: offline fixtures by default, explicitly gated live REST."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

from hungrycall.fixtures import (
    SCENARIO_FIXTURES,
    deduplicate_activity,
    render_fixture_data,
)
from hungrycall.models import CallResult, CallStatus, Mode, Restaurant, UserRequest
from hungrycall.order_chains import simulate_order_chain_result
from hungrycall.phone_utils import mask_phones_in_text, normalize_e164
from hungrycall.safety import SafetyError, verify_phone_safety
from hungrycall.schemas import get_result_schema


DEFAULT_CALLE_ENV_FILE = Path(r"C:\_Local_DEV\CREDENTIALS\call-e\call-e.env")
DEFAULT_CALLE_BASE_URL = "https://api.heycall-e.com"
TERMINAL_STATUSES = {status.value for status in CallStatus}


@dataclass(frozen=True)
class CalleSettings:
    """Resolved live settings; the secret is deliberately excluded from repr."""

    api_key: str = field(repr=False)
    base_url: str = DEFAULT_CALLE_BASE_URL
    env_file: Optional[Path] = None


@dataclass(frozen=True)
class PreflightResult:
    """Safe, non-secret result of an authenticated GET that cannot place a call."""

    base_url: str
    status_code: int
    reachable: bool
    authenticated: bool
    detail: str


class CalleAPIError(RuntimeError):
    """An API error that never includes the response body or bearer token."""

    def __init__(self, status_code: int, operation: str):
        self.status_code = status_code
        self.operation = operation
        super().__init__(f"CALL-E API returned HTTP {status_code} during {operation}.")


def _parse_env_file(path: Path) -> Dict[str, str]:
    """Read the three supported settings without importing python-dotenv."""

    values: Dict[str, str] = {}
    try:
        lines = path.read_text(encoding="utf-8-sig").splitlines()
    except FileNotFoundError:
        return values
    except OSError as exc:
        raise SafetyError(f"CALL-E settings file could not be read: {path}") from exc

    allowed = {"CALLE_API_KEY", "IAM_API_KEY", "CALLE_BASE_URL"}
    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        name, value = line.split("=", 1)
        name = name.strip()
        if name not in allowed:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        values[name] = value
    return values


def load_calle_settings(
    env_file: Optional[str | Path] = None,
    environment: Optional[Mapping[str, str]] = None,
) -> CalleSettings:
    """Resolve environment first, then the external ``call-e.env`` fallback.

    No value is copied into the repository. ``CALLE_ENV_FILE`` can point to a
    different machine-local file; if it is absent, HungryCall checks the known
    operator path outside this repository.
    """

    environ = os.environ if environment is None else environment
    configured_path = env_file or environ.get("CALLE_ENV_FILE")
    path = Path(configured_path) if configured_path else DEFAULT_CALLE_ENV_FILE
    file_values = _parse_env_file(path)

    api_key = (
        environ.get("CALLE_API_KEY")
        or environ.get("IAM_API_KEY")
        or file_values.get("CALLE_API_KEY")
        or file_values.get("IAM_API_KEY")
        or ""
    ).strip()
    if not api_key:
        raise SafetyError(
            "CALL-E API key missing. Set CALLE_API_KEY (or IAM_API_KEY), "
            f"or provide it in {path}. Dry-run is still available."
        )

    base_url = (
        environ.get("CALLE_BASE_URL")
        or file_values.get("CALLE_BASE_URL")
        or DEFAULT_CALLE_BASE_URL
    ).strip().rstrip("/")
    if not base_url.startswith("https://"):
        raise SafetyError("CALLE_BASE_URL must use HTTPS for live mode.")

    return CalleSettings(
        api_key=api_key,
        base_url=base_url,
        env_file=path if file_values else None,
    )


def probe_calle_connection(
    settings: Optional[CalleSettings] = None,
    *,
    timeout_seconds: float = 10.0,
) -> PreflightResult:
    """Authenticate with a read-only GET to an intentionally absent call id.

    The method is deliberately fixed to GET. It never invokes ``POST /v1/calls``
    and therefore cannot create a call or spend call credit.
    """

    resolved = settings or load_calle_settings()
    request = urllib.request.Request(
        resolved.base_url + "/v1/calls/probe-does-not-exist",
        headers={
            "Authorization": f"Bearer {resolved.api_key}",
            "Accept": "application/json",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            status_code = int(response.status)
    except urllib.error.HTTPError as error:
        status_code = int(error.code)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise SafetyError(
            f"CALL-E preflight could not reach {resolved.base_url}; no call was placed."
        ) from exc

    if status_code in (401, 403):
        return PreflightResult(
            base_url=resolved.base_url,
            status_code=status_code,
            reachable=True,
            authenticated=False,
            detail="Service reachable, but the credential was rejected.",
        )

    # This exact probe id should not exist. A 404 therefore proves the request
    # crossed authentication and reached the calls resource without creating one.
    if status_code == 404:
        return PreflightResult(
            base_url=resolved.base_url,
            status_code=status_code,
            reachable=True,
            authenticated=True,
            detail="Service reachable; credential accepted; probe resource absent as expected.",
        )

    return PreflightResult(
        base_url=resolved.base_url,
        status_code=status_code,
        reachable=True,
        authenticated=200 <= status_code < 400,
        detail="Service answered the read-only preflight; no call was placed.",
    )


class CallClient:
    """Base abstract class for CALL-E interaction."""

    def execute_candidate_call(
        self,
        restaurant: Restaurant,
        user_request: UserRequest,
        idempotency_key: str,
    ) -> CallResult:
        raise NotImplementedError


class DryRunCallClient(CallClient):
    """Dry-run client using local fixtures without network or CALL-E account."""

    def __init__(self, scenario_name: str = "success_direct"):
        self.scenario_name = scenario_name
        self.scenario_data = SCENARIO_FIXTURES.get(scenario_name, {})

    def execute_candidate_call(
        self,
        restaurant: Restaurant,
        user_request: UserRequest,
        idempotency_key: str,
    ) -> CallResult:
        normalized_phone = normalize_e164(restaurant.phone)
        verify_phone_safety(normalized_phone)
        raw_mock_entry = self.scenario_data.get(restaurant.id)

        if not raw_mock_entry:
            raw_mock_entry = {
                "status": CallStatus.FAILED,
                "structured_result": {
                    "delivers_to_address": False,
                    "price_known": False,
                    "order_placed": False,
                    "rejection_reason": "No response / busy line",
                },
                "post_summary": "Call failed to connect.",
                "transcript": [],
                "activity": ["Call initiated", "No response"],
            }

        rendered = render_fixture_data(raw_mock_entry, user_request, restaurant)
        status = rendered.get("status", CallStatus.COMPLETED)
        structured = rendered.get("structured_result", {})
        if user_request.order_chain and "order_chain_results" not in structured:
            structured["order_chain_results"] = simulate_order_chain_result(
                user_request.order_chain, structured
            )
        transcript = []
        for turn in rendered.get("transcript", []):
            if isinstance(turn, dict):
                safe_turn = dict(turn)
                safe_turn["text"] = mask_phones_in_text(str(safe_turn.get("text", "")))
                transcript.append(safe_turn)

        return CallResult(
            call_id=f"dry_call_{restaurant.id}_{int(time.time())}",
            run_id=f"dry_run_{idempotency_key}",
            status=status,
            task_completed=(status == CallStatus.COMPLETED),
            completion_confidence=0.95,
            structured_result=structured,
            transcript=transcript,
            post_summary=mask_phones_in_text(str(rendered.get("post_summary") or "")),
            rejection_reason=mask_phones_in_text(str(structured.get("rejection_reason") or "")) or None,
            activity=deduplicate_activity([
                mask_phones_in_text(str(line)) for line in rendered.get("activity", [])
            ]),
            raw_transcript_text=mask_phones_in_text(str(rendered.get("raw_transcript_text") or "")),
        )


class LiveCallClient(CallClient):
    """Serial CALL-E REST adapter, available only after explicit confirmation."""

    def __init__(
        self,
        settings: CalleSettings,
        *,
        confirmed: bool = False,
        first_poll_seconds: float = 60.0,
        poll_seconds: float = 8.0,
        poll_timeout_seconds: float = 900.0,
    ):
        if not confirmed:
            raise SafetyError("Live calls require explicit confirmation.")
        self.settings = settings
        self.confirmed = True
        self.first_poll_seconds = first_poll_seconds
        self.poll_seconds = poll_seconds
        self.poll_timeout_seconds = poll_timeout_seconds

    @classmethod
    def from_environment(
        cls,
        *,
        confirmed: bool = False,
        env_file: Optional[str | Path] = None,
        **kwargs: Any,
    ) -> "LiveCallClient":
        return cls(
            load_calle_settings(env_file=env_file),
            confirmed=confirmed,
            **kwargs,
        )

    def _request(
        self,
        method: str,
        path: str,
        payload: Optional[Dict[str, Any]] = None,
        idempotency_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self.settings.api_key}",
            "Accept": "application/json",
        }
        data = None
        if payload is not None:
            headers["Content-Type"] = "application/json"
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key

        request = urllib.request.Request(
            self.settings.base_url + path,
            data=data,
            headers=headers,
            method=method,
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                value = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            raise CalleAPIError(error.code, f"{method} {path}") from error
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise RuntimeError(f"CALL-E API was unreachable during {method} {path}.") from exc
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RuntimeError("CALL-E API returned invalid JSON.") from exc
        if not isinstance(value, dict):
            raise RuntimeError("CALL-E API returned a non-object response.")
        return value

    @staticmethod
    def _containers(value: Dict[str, Any]) -> List[Dict[str, Any]]:
        containers = [value]
        if isinstance(value.get("result"), dict):
            containers.insert(0, value["result"])
        return containers

    @classmethod
    def _status(cls, value: Dict[str, Any]) -> Optional[str]:
        for container in cls._containers(value):
            status = container.get("status") or container.get("call_status")
            if isinstance(status, str):
                normalized = status.upper()
                return "CANCELED" if normalized == "CANCELLED" else normalized
        return None

    @classmethod
    def _structured_result(cls, value: Dict[str, Any]) -> Dict[str, Any]:
        """The recipient's answers, not the batch envelope.

        Live payloads carry TWO structured results (measured 2026-08-11): the
        top-level one answers ``result_schema`` (just ``completed_count``) and
        SHADOWED the per-recipient answers three cascades long — every filled
        result was mistaken for "missing required fields". The recipient's
        ``recipient_result_schema`` answers are the ones a candidate call is
        about, so they win; the top level is only a fallback.
        """
        for container in cls._containers(value):
            recipients = container.get("recipients")
            if isinstance(recipients, list) and recipients and isinstance(recipients[0], dict):
                for key in ("structured_result", "structuredResult"):
                    if isinstance(recipients[0].get(key), dict) and recipients[0][key]:
                        return recipients[0][key]
        for container in cls._containers(value):
            for key in ("structured_result", "structuredResult"):
                if isinstance(container.get(key), dict):
                    return container[key]
        return {}

    @classmethod
    def _value(cls, value: Dict[str, Any], *keys: str, default: Any = None) -> Any:
        for container in cls._containers(value):
            for key in keys:
                if container.get(key) is not None:
                    return container[key]
        return default

    @classmethod
    def _activity(cls, value: Dict[str, Any]) -> List[str]:
        raw = cls._value(value, "activity", default=[])
        if not isinstance(raw, list):
            return []
        lines: List[str] = []
        for event in raw:
            if isinstance(event, str):
                line = event
            elif isinstance(event, dict):
                message = event.get("message") or event.get("text") or event.get("activity")
                timestamp = event.get("timestamp") or event.get("created_at") or event.get("time")
                line = f"{timestamp} | {message}" if timestamp and message else str(message or timestamp or "")
            else:
                line = str(event)
            if line:
                lines.append(mask_phones_in_text(line))
        return deduplicate_activity(lines)

    @classmethod
    def _transcript_from_turns(cls, value: Dict[str, Any]) -> str:
        """Rebuild the verbatim conversation from recipients[].attempts[].

        Format: one line per turn, ``[mm:ss] SPEAKER: text`` — the same shape
        the earlier MCP evidence used, so downstream verification reads both.
        """
        for container in cls._containers(value):
            recipients = container.get("recipients")
            if not isinstance(recipients, list):
                continue
            for recipient in recipients:
                if not isinstance(recipient, dict):
                    continue
                for attempt in reversed(recipient.get("attempts") or []):
                    turns = attempt.get("transcript_turns") if isinstance(attempt, dict) else None
                    if not isinstance(turns, list) or not turns:
                        continue
                    lines = []
                    for turn in turns:
                        if not isinstance(turn, dict):
                            continue
                        offset = turn.get("offset_seconds")
                        try:
                            seconds = int(offset)
                        except (TypeError, ValueError):
                            seconds = 0
                        speaker = str(turn.get("speaker") or "?").upper()
                        text = str(turn.get("text") or "").strip()
                        if text:
                            lines.append(f"[{seconds // 60:02d}:{seconds % 60:02d}] {speaker}: {text}")
                    if lines:
                        return "\n".join(lines)
        return ""

    def execute_candidate_call(
        self,
        restaurant: Restaurant,
        user_request: UserRequest,
        idempotency_key: str,
    ) -> CallResult:
        normalized_phone = normalize_e164(restaurant.phone)
        verify_phone_safety(normalized_phone)

        # Imported lazily to avoid a module cycle: engine owns the canonical
        # goal builder and imports the transport abstraction above.
        from hungrycall.engine import build_call_goal

        payload = {
            "task": build_call_goal(restaurant, user_request),
            "recipients": [
                {
                    "phones": [normalized_phone],
                    "region": "DE",
                    "locale": "de",
                }
            ],
            "result_schema": {
                "type": "object",
                "properties": {"completed_count": {"type": "integer"}},
            },
            "recipient_result_schema": get_result_schema(
                user_request.mode, user_request.order_chain
            ),
            "metadata": {
                "hungrycall_restaurant_id": restaurant.id,
                "hungrycall_mode": user_request.mode.value,
            },
        }
        # A timed-out create is NOT proof that no call exists: the field trial
        # 2026-08-11 produced a "ghost call" — the client gave up after 30s,
        # the provider dialled anyway, and the cascade lost track of a running
        # conversation. Retrying with the SAME Idempotency-Key is safe by
        # design and re-attaches to whatever the first attempt created.
        created = None
        for create_attempt in range(3):
            try:
                created = self._request(
                    "POST", "/v1/calls", payload=payload, idempotency_key=idempotency_key
                )
                break
            except (RuntimeError, CalleAPIError) as exc:
                if isinstance(exc, CalleAPIError) and exc.status_code < 500:
                    raise
                if create_attempt == 2:
                    raise
                time.sleep(3 * (create_attempt + 1))
        run_id = self._value(created, "id", "call_id", "run_id")
        if not isinstance(run_id, str) or not run_id:
            raise RuntimeError("CALL-E create response did not include a call id.")

        deadline = time.monotonic() + self.poll_timeout_seconds
        if self.first_poll_seconds:
            time.sleep(self.first_poll_seconds)

        latest = created
        poll_failures = 0
        while True:
            # A live call keeps running on the provider side while we poll.
            # One transient network hiccup must not abandon the cascade
            # (field trial 2026-08-11: a single unreachable GET killed a
            # running call whose conversation completed fine).
            try:
                latest = self._request("GET", f"/v1/calls/{run_id}")
                poll_failures = 0
            except (RuntimeError, CalleAPIError) as exc:
                if isinstance(exc, CalleAPIError) and exc.status_code < 500:
                    raise
                poll_failures += 1
                if poll_failures >= 4:
                    raise
                if time.monotonic() >= deadline:
                    raise TimeoutError(
                        "CALL-E status polling exceeded the configured timeout."
                    ) from exc
                time.sleep(max(self.poll_seconds or 0, 5))
                continue
            status = self._status(latest)
            if status in TERMINAL_STATUSES:
                break
            if time.monotonic() >= deadline:
                raise TimeoutError("CALL-E status polling exceeded the configured timeout.")
            if self.poll_seconds:
                time.sleep(self.poll_seconds)

        debug_dir = os.environ.get("HUNGRYCALL_DEBUG_PAYLOAD_DIR", "").strip()
        if debug_dir:
            # Field-trial diagnosis aid: the masked terminal payload answers
            # "what did the API actually send" without dashboard access.
            # Local file, phone numbers masked, opt-in via environment only.
            try:
                os.makedirs(debug_dir, exist_ok=True)
                dump = mask_phones_in_text(json.dumps(latest, ensure_ascii=False, indent=1))
                stamp = time.strftime("%Y%m%dT%H%M%S")
                with open(
                    os.path.join(debug_dir, f"terminal-{stamp}-{run_id[-8:]}.json"),
                    "w", encoding="utf-8",
                ) as handle:
                    handle.write(dump)
            except OSError:
                pass

        status_value = CallStatus(status)
        structured = self._structured_result(latest)
        transcript = self._value(latest, "transcript", default="")
        raw_transcript = mask_phones_in_text(transcript) if isinstance(transcript, str) else ""
        if not raw_transcript:
            # Live payloads carry the conversation as transcript_turns inside
            # recipients[].attempts[] (measured 2026-08-11); the top-level
            # transcript string may be missing entirely. Without this fallback
            # the verbatim record of a live call is silently lost.
            raw_transcript = mask_phones_in_text(self._transcript_from_turns(latest))
        confidence = self._value(
            latest, "completionConfidence", "completion_confidence", default=0.0
        )
        try:
            confidence_value = float(confidence)
        except (TypeError, ValueError):
            confidence_value = 0.0

        post_summary = self._value(latest, "post_summary", "summary", default="")
        return CallResult(
            call_id=run_id,
            run_id=run_id,
            status=status_value,
            task_completed=bool(
                self._value(
                    latest,
                    "taskCompleted",
                    "task_completed",
                    default=status_value == CallStatus.COMPLETED,
                )
            ),
            completion_confidence=confidence_value,
            structured_result=structured,
            transcript=[],
            post_summary=mask_phones_in_text(str(post_summary or "")),
            rejection_reason=mask_phones_in_text(str(structured.get("rejection_reason") or "")) or None,
            activity=self._activity(latest),
            raw_transcript_text=raw_transcript,
        )
