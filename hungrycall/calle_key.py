"""Whose key pays for the call — and how the borrowed one is handled.

In ``huckepack-only-host`` the key belongs to the visitor. It arrives in one
request header, is used for that one call, and is gone when the request ends:
it is never written to the database, never put into a file, never placed in a
log line and never returned to the browser in anything but its masked form.

The rules that make that true are small enough to state:

* the value lives in a :class:`~contextvars.ContextVar` for the duration of one
  request and nowhere else;
* every error message about it carries the *fingerprint*, never the value —
  which is why :func:`describe_key` exists and no ``str(key)`` appears anywhere;
* :class:`~hungrycall.call_client.CalleSettings` already excludes the key from
  its ``repr``, so a stray ``logger.debug(settings)`` cannot leak it either.
"""

from __future__ import annotations

import re
from contextvars import ContextVar

from hungrycall.call_client import (
    DEFAULT_CALLE_BASE_URL,
    CalleSettings,
    load_calle_settings,
)
from hungrycall.safety import SafetyError
from hungrycall.server_mode import ServerMode, current_mode, require_implemented

#: The header the browser sends in ``huckepack-only-host``. Never a query
#: parameter: those end up in access logs and in browser history.
KEY_HEADER = "X-Calle-Key"

#: Deliberately loose about the shape (a provider may change it) and strict
#: about what would be dangerous: whitespace, control characters, absurd length.
_KEY_PATTERN = re.compile(r"^[!-~]{8,512}$")

_request_key: ContextVar[str | None] = ContextVar("huckepack_request_key", default=None)


class UserKeyError(SafetyError):
    """A missing or unusable visitor key. Never contains the key itself."""


def mask_key(value: str | None) -> str:
    """The only representation of a key that may be shown, stored or logged."""
    if not value:
        return ""
    if len(value) <= 4:
        return "••••"
    return f"••••{value[-4:]}"


def describe_key(value: str | None) -> str:
    """A sentence about a key that is safe in a log line."""
    if not value:
        return "no key"
    return f"key {mask_key(value)} ({len(value)} characters)"


def validate_key(raw: str | None) -> str:
    """Check the shape and return the cleaned key, or say why it is refused."""
    value = (raw or "").strip()
    if not value:
        raise UserKeyError("No CALL-E key was supplied for this call.")
    if not _KEY_PATTERN.match(value):
        raise UserKeyError(
            "The supplied CALL-E key has an unusable shape "
            "(8 to 512 characters, no spaces or control characters)."
        )
    return value


def bind_request_key(raw: str | None):
    """Hold a visitor key for the current request. Returns the reset token."""
    value = (raw or "").strip() or None
    return _request_key.set(value)


def unbind_request_key(reset_token) -> None:
    _request_key.reset(reset_token)


def current_request_key() -> str | None:
    return _request_key.get()


def current_key_fingerprint() -> str:
    return mask_key(_request_key.get())


def resolve_call_settings(
    mode: ServerMode | None = None,
    *,
    base_url: str | None = None,
) -> CalleSettings:
    """The settings a live call must use in this mode.

    ``huckepack-only-host`` never falls back to the host's own credential. If
    the visitor sent no key, the call does not happen — silently spending the
    host's money would be the one failure mode nobody could see.
    """
    mode = require_implemented(mode or current_mode())

    if mode.key_from_browser:
        key = validate_key(current_request_key())
        return CalleSettings(
            api_key=key,
            base_url=base_url or DEFAULT_CALLE_BASE_URL,
            env_file=None,
        )

    settings = load_calle_settings()
    if base_url:
        settings = CalleSettings(
            api_key=settings.api_key, base_url=base_url, env_file=settings.env_file
        )
    return settings
