"""The language seam (call_language.py): a single ``HUNGRYCALL_CALL_LOCALE``
resolves both the CALL-E recipient's region/locale (test_call_client.py) and
the language of the VERBATIM-quoted goal fragments in engine.py and
order_chains.py. German is the default and must stay byte-identical to the
pre-seam behaviour when the variable is unset."""

from hungrycall.call_language import CALL_LOCALE_ENV, DEFAULT_CALL_LOCALE, call_language
from hungrycall.engine import build_call_goal
from hungrycall.fixtures import SAMPLE_RESTAURANTS
from hungrycall.models import Mode, OrderChain, UserRequest
from hungrycall.order_chains import build_order_chain_instruction


def make_chain() -> OrderChain:
    return OrderChain.from_dict({
        "version": 1,
        "posten": [{
            "zellen": [{
                "menge": 1,
                "produkt": "Burger",
                "art": "essen",
                "kriterien": [],
            }],
            "tags": [],
            "wenn_nichts_verfuegbar": "posten_weglassen",
        }],
    })


def _delivery_request(**overrides):
    base = dict(
        mode=Mode.DELIVERY,
        customer_name="Alex Beispiel",
        food_prompt="Burger",
        max_budget_eur=25.0,
        delivery_address="Musterstrasse 5, 12345 Dorfstadt",
        requester_callback_number="+441632960090",
    )
    base.update(overrides)
    return UserRequest(**base)


def test_call_language_defaults_to_german_when_unset(monkeypatch):
    monkeypatch.delenv(CALL_LOCALE_ENV, raising=False)
    language = call_language()
    assert language.locale == "de"
    assert language.region == "DE"


def test_call_language_honours_an_explicit_english_override(monkeypatch):
    monkeypatch.setenv(CALL_LOCALE_ENV, "en")
    language = call_language()
    assert language.locale == "en"
    # Documented limitation, not a guess: CALL-E only confirms region "DE"
    # as supported (AGENTS.md). An English call locale changes the language
    # spoken, not the dialled country.
    assert language.region == "DE"


def test_call_language_is_case_insensitive_and_trims_whitespace(monkeypatch):
    monkeypatch.setenv(CALL_LOCALE_ENV, " EN ")
    assert call_language().locale == "en"


def test_call_language_falls_back_to_german_on_an_unsupported_value(monkeypatch):
    monkeypatch.setenv(CALL_LOCALE_ENV, "fr")
    language = call_language()
    assert language.locale == DEFAULT_CALL_LOCALE
    assert language.region == "DE"


def test_german_goal_keeps_its_verbatim_parts_byte_identical_by_default(monkeypatch):
    monkeypatch.delenv(CALL_LOCALE_ENV, raising=False)
    goal = build_call_goal(SAMPLE_RESTAURANTS[0], _delivery_request(order_chain=make_chain()))

    assert "Hallo, hier spricht ein automatisierter Assistent" in goal
    assert "Conduct the entire conversation in German" in goal
    assert 'ask exactly "Haben Sie Burger?"' in goal
    assert "Bestätigen Sie mir bitte kurz die Bestellung" in goal
    assert "Sie bestellen also 2 Pasta Napoli?" in goal
    assert "Hello, this is an automated assistant" not in goal


def test_english_goal_carries_english_verbatim_parts_and_no_german_ones(monkeypatch):
    monkeypatch.setenv(CALL_LOCALE_ENV, "en")
    goal = build_call_goal(SAMPLE_RESTAURANTS[0], _delivery_request(order_chain=make_chain()))

    assert "Hello, this is an automated assistant" in goal
    assert "Conduct the entire conversation in English" in goal
    assert 'ask exactly "Do you have Burger?"' in goal
    assert "Could you please briefly confirm the order" in goal
    assert "So you're ordering 2 Pasta Napoli?" in goal
    # None of the German-only mandatory sentences may leak into an English call
    # (this is exactly the 2026-08-11 field-trial defect the seam fixes).
    assert "Hallo, hier spricht ein automatisierter Assistent" not in goal
    assert "Conduct the entire conversation in German" not in goal
    assert "Haben Sie" not in goal
    assert "Bestätigen Sie" not in goal


def test_order_chain_instruction_locale_argument_overrides_the_environment(monkeypatch):
    monkeypatch.setenv(CALL_LOCALE_ENV, "en")
    chain = make_chain()

    de_text = build_order_chain_instruction(chain, "de")
    en_text = build_order_chain_instruction(chain, "en")
    env_text = build_order_chain_instruction(chain)  # falls back to the env

    assert 'ask exactly "Haben Sie Burger?"' in de_text
    assert "Do you have" not in de_text
    assert 'ask exactly "Do you have Burger?"' in en_text
    assert "Haben Sie" not in en_text
    assert 'ask exactly "Do you have Burger?"' in env_text
