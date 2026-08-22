"""Regression coverage for E25 (Endabnahme E-3 field-trial finding, 2026-08-22).

seating_confirmed is free text the call reports (schemas.py), not an enum:
for "indoor"/"outdoor" it happens to match a translation key this app
defines, but for a custom seating wish the call reports back the guest's
own words verbatim -- and the reservation result card built a translation
key out of that text unconditionally. The raw, unresolved key i18n.t()
falls back to leaked straight into the sentence: "Tisch bei Zum Falken ...
um 19:00result.sentence.seating.draussen unter dem Kirschbaum".
localized_seating() (templates.py) only translates when the constructed key
actually exists; otherwise it shows exactly what was confirmed.
"""

from hungrycall.i18n import t
from hungrycall.models import Mode, OpeningHours, Restaurant
from hungrycall.templates import localized_seating, render_result_card, render_result_sentence

RESTAURANT = Restaurant(
    id="rest_zum_falken",
    name="Zum Falken",
    phone="+441632960090",
    cuisines=["German"],
    opening_hours=OpeningHours(
        days=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        open_time="11:00",
        close_time="22:00",
    ),
    address="Marktplatz 1, Dorfstadt",
)


def test_a_known_seating_value_is_translated():
    assert localized_seating("indoor", "de", "result.sentence.seating") == t(
        "result.sentence.seating.indoor", "de"
    )
    assert localized_seating("outdoor", "en", "result.sentence.seating") == t(
        "result.sentence.seating.outdoor", "en"
    )


def test_a_custom_seating_wish_is_shown_verbatim_not_as_a_raw_key():
    """Zum Falken (E25): the call confirmed the guest's own custom wording,
    which is not one of this app's fixed seating values."""
    custom = "draußen unter dem Kirschbaum"
    assert localized_seating(custom, "de", "result.sentence.seating") == custom
    assert "result.sentence.seating." not in localized_seating(custom, "de", "result.sentence.seating")


def test_empty_or_missing_seating_is_the_empty_string():
    assert localized_seating(None, "de", "result.sentence.seating") == ""
    assert localized_seating("", "de", "result.sentence.seating") == ""


def test_reservation_sentence_never_leaks_a_raw_translation_key():
    structured = {
        "callback_number": "+441632960090",
        "seating_confirmed": "draußen unter dem Kirschbaum",
    }
    sentence = render_result_sentence(
        lang="de",
        mode=Mode.RESERVATION,
        restaurant=RESTAURANT,
        structured=structured,
        food_prompt="",
        party_size=2,
        reservation_date="2026-08-22",
        reservation_time="19:00",
    )
    assert "draußen unter dem Kirschbaum" in sentence
    assert "result.sentence.seating." not in sentence


def test_result_card_facts_table_never_leaks_a_raw_translation_key():
    structured = {
        "callback_number": "+441632960090",
        "reservation_confirmed": True,
        "reservation_time_confirmed": "19:00",
        "party_size_confirmed": 2,
        "seating_confirmed": "draußen unter dem Kirschbaum",
    }
    card = render_result_card(
        lang="de",
        mode=Mode.RESERVATION,
        restaurant=RESTAURANT,
        structured=structured,
        post_summary="",
        raw_transcript_text="",
        message="Tisch reserviert.",
        order_id="ord_test",
        calls_made=1,
    )
    assert "draußen unter dem Kirschbaum" in card
    assert "table.seating." not in card
