"""Explicit, installation-gated restaurant fixture mode for the web UI."""

from __future__ import annotations

import html
import os
import urllib.parse
from collections.abc import Mapping

from hungrycall.i18n import t

ENV_VAR = "HUNGRYCALL_RESTAURANT_TEST_MODE"
COOKIE_NAME = "hungrycall_restaurant_test_mode"
FIXTURE_DAY = "Fri"
FIXTURE_TIME = "19:00"


def feature_enabled(environ: Mapping[str, str] | None = None) -> bool:
    """Return whether the installation exposes restaurant fixture mode.

    It is available by default while HungryCall is being evaluated. Set the
    environment variable to ``off`` to remove the switch and ignore any stale
    browser cookie. Only the documented ``on`` value enables an explicit
    override.
    """
    source = os.environ if environ is None else environ
    value = source.get(ENV_VAR)
    if value is None or not value.strip():
        return True
    return value.strip().lower() == "on"


def active(cookies: Mapping[str, str], environ: Mapping[str, str] | None = None) -> bool:
    """Test mode is active only when both installation and browser opt in."""
    return feature_enabled(environ) and cookies.get(COOKIE_NAME) == "on"


def safe_return_path(path: str | None) -> str:
    """Keep toggle redirects on a HungryCall page."""
    candidate = str(path or "/order")
    return candidate if candidate in {"/", "/order", "/reserve"} else "/order"


def banner(is_active: bool, lang: str, return_to: str) -> str:
    """Render the separate mode switch; this is not an order-form field."""
    target = urllib.parse.quote(safe_return_path(return_to), safe="")
    action = f"/restaurant-test-mode/toggle?lang={html.escape(lang, quote=True)}&next={target}"
    if is_active:
        title = t("search.test_mode.active.title", lang)
        detail = t("search.test_mode.banner.active", lang)
        button = t("search.test_mode.leave", lang)
        state = "active"
    else:
        title = t("search.test_mode.off.title", lang)
        detail = t("search.test_mode.off.body", lang)
        button = t("search.test_mode.enable", lang)
        state = "off"

    return (
        f'<section class="test-mode-banner {state}" data-test-mode="{state}" role="status">'
        f'<div><strong>{html.escape(title)}</strong>'
        f'<div class="small">{html.escape(detail)}</div></div>'
        f'<form method="post" action="{action}">'
        f'<button class="btn secondary" type="submit">{html.escape(button)}</button>'
        "</form></section>"
    )
