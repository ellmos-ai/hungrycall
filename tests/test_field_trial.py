"""The field-trial override must rewire live calls — and only live calls.

Fixture and search candidates carry phone numbers that belong to strangers.
A supervised field trial replaces every candidate's phone with one consenting
test number; a set-but-invalid number must refuse the run instead of silently
falling back to the real numbers.
"""

import pytest

from hungrycall import field_trial
from hungrycall.fixtures import SAMPLE_RESTAURANTS
from hungrycall.safety import SafetyError

TEST_NUMBER = "+447700900201"


def test_without_env_candidates_stay_untouched(monkeypatch):
    monkeypatch.delenv(field_trial.ENV_VAR, raising=False)
    rewritten, number = field_trial.apply(SAMPLE_RESTAURANTS)
    assert number is None
    assert rewritten is SAMPLE_RESTAURANTS
    assert {r.phone for r in rewritten} == {r.phone for r in SAMPLE_RESTAURANTS}


def test_with_env_every_candidate_dials_the_test_number(monkeypatch):
    monkeypatch.setenv(field_trial.ENV_VAR, TEST_NUMBER)
    rewritten, number = field_trial.apply(SAMPLE_RESTAURANTS)
    assert number == TEST_NUMBER
    assert rewritten is not SAMPLE_RESTAURANTS
    assert all(r.phone == TEST_NUMBER for r in rewritten)
    # Everything except the phone stays real: names, ranking inputs, hours.
    assert [r.name for r in rewritten] == [r.name for r in SAMPLE_RESTAURANTS]
    # The originals are not mutated in place.
    assert all(r.phone != TEST_NUMBER for r in SAMPLE_RESTAURANTS)


def test_display_formatting_is_normalized(monkeypatch):
    monkeypatch.setenv(field_trial.ENV_VAR, "+44 7700 900201")
    _, number = field_trial.apply(SAMPLE_RESTAURANTS)
    assert number == "+447700900201"


def test_invalid_number_refuses_instead_of_falling_back(monkeypatch):
    monkeypatch.setenv(field_trial.ENV_VAR, "not-a-number")
    with pytest.raises(SafetyError):
        field_trial.apply(SAMPLE_RESTAURANTS)
