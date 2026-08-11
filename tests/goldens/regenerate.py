"""Regenerate the golden goal-text files for tests/test_scenario_goals.py.

Deliberately NOT collected by pytest (does not match ``test_*.py``) and NOT
run automatically by any test. A red scenario test must never be "fixed" by
silently overwriting the golden it disagrees with — regenerating is a
conscious, reviewed action:

    python tests/goldens/regenerate.py

This prints a diff-shaped summary of every file it changes or creates. Review
that output (and ``git diff tests/goldens/``) before committing — an
unexpected change here usually means the goal text changed, which is exactly
the kind of thing this suite exists to make visible.
"""

from __future__ import annotations

import difflib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from hungrycall.call_language import CALL_LOCALE_ENV  # noqa: E402
import os  # noqa: E402

from tests.test_scenario_goals import (  # noqa: E402
    GOLDENS_DIR, LANGUAGES, RESTAURANT, SCENARIOS,
)
from hungrycall.engine import build_call_goal  # noqa: E402


def main() -> int:
    GOLDENS_DIR.mkdir(parents=True, exist_ok=True)
    created, changed, unchanged = [], [], []

    for name, (factory, _check) in sorted(SCENARIOS.items()):
        for lang in LANGUAGES:
            os.environ[CALL_LOCALE_ENV] = lang
            goal = build_call_goal(RESTAURANT, factory())
            path = GOLDENS_DIR / f"{name}.{lang}.txt"
            if not path.exists():
                path.write_text(goal, encoding="utf-8")
                created.append(path.name)
                continue
            previous = path.read_text(encoding="utf-8")
            if previous == goal:
                unchanged.append(path.name)
                continue
            diff = "\n".join(difflib.unified_diff(
                previous.splitlines(), goal.splitlines(),
                fromfile=f"{path.name} (old)", tofile=f"{path.name} (new)",
                lineterm="",
            ))
            print(f"--- CHANGED: {path.name} ---\n{diff}\n")
            path.write_text(goal, encoding="utf-8")
            changed.append(path.name)

    os.environ.pop(CALL_LOCALE_ENV, None)
    print(f"{len(created)} created, {len(changed)} changed, {len(unchanged)} unchanged.")
    if created:
        print("Created: " + ", ".join(created))
    if changed:
        print("Changed (reviewed diffs above): " + ", ".join(changed))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
