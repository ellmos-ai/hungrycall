"""Field-trial override: route every live call to one consenting test number.

Live candidates come from fixtures or the OpenStreetMap search — both carry
phone numbers that belong to strangers. A supervised field trial must never
dial those. When ``HUNGRYCALL_FIELD_TRIAL_PHONE`` is set, every candidate's
phone is replaced by that single consenting number before a live cascade
starts, and the run is visibly marked as a field trial. The restaurant names,
ranking and dialogue stay real; only the wire goes to the test line.

The override is deliberately fail-closed: a set-but-invalid number refuses the
live run instead of falling back to the real numbers.
"""

from __future__ import annotations

import os
from dataclasses import replace

from hungrycall.models import Restaurant
from hungrycall.phone_utils import normalize_e164, validate_e164
from hungrycall.safety import SafetyError

ENV_VAR = "HUNGRYCALL_FIELD_TRIAL_PHONE"


def trial_phone() -> str | None:
    """The configured test number, normalized — or ``None`` when unset.

    Raises ``SafetyError`` when the variable is set but not a usable E.164
    number: silently ignoring it would send live calls to strangers, which is
    the one outcome this module exists to prevent.
    """
    raw = os.environ.get(ENV_VAR, "").strip()
    if not raw:
        return None
    normalized = normalize_e164(raw)
    if not validate_e164(normalized):
        raise SafetyError(
            f"{ENV_VAR} is set but not a valid E.164 number; "
            "refusing to start a live cascade."
        )
    return normalized


def apply(candidates: list[Restaurant]) -> tuple[list[Restaurant], str | None]:
    """Rewrite every candidate's phone to the trial number, if one is set.

    Returns the (possibly rewritten) candidate list and the trial number —
    ``None`` means no override is configured and the list is returned as-is.
    """
    number = trial_phone()
    if number is None:
        return candidates, None
    return [replace(r, phone=number) for r in candidates], number
