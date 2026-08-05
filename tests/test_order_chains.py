"""Regression coverage for the approved position -> cell -> criterion blueprint."""

import json
import os

import pytest
from fastapi.testclient import TestClient

from hungrycall import web
from hungrycall.call_client import DryRunCallClient
from hungrycall.db import (
    create_order_record,
    get_order_record,
    init_db,
    list_order_templates,
    list_tags,
    save_order_template,
    save_tags,
)
from hungrycall.engine import CascadeEngine, build_call_goal
from hungrycall.fixtures import SAMPLE_RESTAURANTS
from hungrycall.models import Mode, OrderChain, UserRequest
from hungrycall.order_chains import (
    build_order_chain_instruction,
    evaluate_order_chain,
    order_chain_json,
    parse_order_chain,
)
from hungrycall.schemas import get_result_schema


def make_chain(*, first_reaction="naechster_ersatz", end_rule="posten_weglassen"):
    return OrderChain.from_dict({
        "version": 1,
        "posten": [{
            "zellen": [
                {
                    "menge": 1,
                    "produkt": "Burger",
                    "art": "essen",
                    "kriterien": [{
                        "art": "hoechstpreis",
                        "wert": 10,
                        "reaktion_ja": "annehmen",
                        "reaktion_nein": first_reaction,
                    }],
                },
                {
                    "menge": 2,
                    "produkt": "Toast",
                    "art": "essen",
                    "kriterien": [],
                },
            ],
            "tags": ["Alex"],
            "wenn_nichts_verfuegbar": end_rule,
        }],
    })


def position_result(*cells):
    return {"order_chain_results": [{"posten_index": 0, "zellen": list(cells)}]}


def test_data_model_round_trips_the_blueprint_config_values():
    chain = make_chain()
    restored = parse_order_chain(order_chain_json(chain))

    assert restored == chain
    payload = restored.to_dict()
    assert payload["posten"][0]["zellen"][0]["art"] == "essen"
    assert payload["posten"][0]["zellen"][0]["kriterien"][0]["art"] == "hoechstpreis"
    assert payload["posten"][0]["wenn_nichts_verfuegbar"] == "posten_weglassen"


def test_translator_preserves_position_cell_criterion_and_end_rule_order():
    text = build_order_chain_instruction(make_chain(end_rule="bestellung_abbrechen"))

    assert text.index("Position 1") < text.index("Cell 1") < text.index("Criterion 1")
    assert text.index("Criterion 1") < text.index("Cell 2")
    assert 'ask exactly "Do you have 1 x Burger?"' in text
    assert "discard this cell and try the next replacement cell" in text
    assert "do not place any order" in text


def test_soft_criterion_moves_to_the_next_replacement():
    result = position_result(
        {
            "zelle_index": 0,
            "verfuegbar": True,
            "kriterien": [{
                "kriterium_index": 0, "preis_bekannt": True, "preis_eur": 12,
            }],
        },
        {"zelle_index": 1, "verfuegbar": True, "kriterien": []},
    )

    evaluation = evaluate_order_chain(make_chain(), result)

    assert evaluation.success is True
    assert evaluation.accepted[0].cell_index == 1
    assert evaluation.accepted[0].cell.product == "Toast"


def test_hard_criterion_stops_the_replacement_chain_then_skips_the_position():
    result = position_result({
        "zelle_index": 0,
        "verfuegbar": True,
        "kriterien": [{
            "kriterium_index": 0, "preis_bekannt": True, "preis_eur": 12,
        }],
    })

    evaluation = evaluate_order_chain(make_chain(first_reaction="ablehnen"), result)

    assert evaluation.success is False  # skipping the only position would make an empty order
    assert evaluation.aborted is False
    assert evaluation.skipped_positions == [0]
    assert evaluation.accepted == []


def test_hard_criterion_and_abort_rule_abort_the_whole_order():
    result = position_result({
        "zelle_index": 0,
        "verfuegbar": True,
        "kriterien": [{
            "kriterium_index": 0, "preis_bekannt": True, "preis_eur": 12,
        }],
    })

    evaluation = evaluate_order_chain(make_chain(
        first_reaction="ablehnen", end_rule="bestellung_abbrechen"
    ), result)

    assert evaluation.success is False
    assert evaluation.aborted is True
    assert "bestellung_abbrechen" in evaluation.reason


def test_question_uses_its_configured_yes_and_no_reactions():
    chain = OrderChain.from_dict({
        "posten": [{
            "zellen": [{
                "menge": 1, "produkt": "Burger", "art": "essen",
                "kriterien": [{
                    "art": "rueckfrage", "wert": "Glutenfrei?",
                    "reaktion_ja": "annehmen", "reaktion_nein": "ablehnen",
                }],
            }],
            "tags": [], "wenn_nichts_verfuegbar": "bestellung_abbrechen",
        }],
    })
    yes = position_result({
        "zelle_index": 0, "verfuegbar": True,
        "kriterien": [{"kriterium_index": 0, "antwort_ja": True}],
    })
    no = position_result({
        "zelle_index": 0, "verfuegbar": True,
        "kriterien": [{"kriterium_index": 0, "antwort_ja": False}],
    })

    assert evaluate_order_chain(chain, yes).success is True
    assert evaluate_order_chain(chain, no).aborted is True


def test_missing_question_evidence_is_not_inferred():
    chain = OrderChain.from_dict({
        "posten": [{
            "zellen": [{
                "menge": 1, "produkt": "Cola", "art": "getraenk",
                "kriterien": [{
                    "art": "rueckfrage", "wert": "Zero?",
                    "reaktion_ja": "annehmen", "reaktion_nein": "naechster_ersatz",
                }],
            }],
            "tags": [], "wenn_nichts_verfuegbar": "posten_weglassen",
        }],
    })
    result = position_result({
        "zelle_index": 0, "verfuegbar": True,
        "kriterien": [{"kriterium_index": 0}],
    })

    evaluation = evaluate_order_chain(chain, result)

    assert evaluation.success is False
    assert "antwort_ja" in evaluation.reason


def test_dynamic_schema_and_goal_come_from_the_same_chain():
    chain = make_chain()
    request = UserRequest(
        mode=Mode.DELIVERY,
        customer_name="Alex",
        food_prompt=chain.summary(),
        max_budget_eur=35,
        delivery_address="Dorfstraße 10",
        order_chain=chain,
        requester_callback_number="+4910004069000",
    )

    schema = get_result_schema(Mode.DELIVERY, chain)
    goal = build_call_goal(SAMPLE_RESTAURANTS[0], request)

    assert "order_chain_results" in schema["required"]
    assert "order_chain_results" in schema["properties"]
    assert "1 x Burger" in goal and "2 x Toast" in goal


def test_dry_run_supplies_chain_evidence_and_never_needs_network():
    chain = make_chain()
    request = UserRequest(
        mode=Mode.DELIVERY,
        customer_name="Alex",
        food_prompt=chain.summary(),
        max_budget_eur=35,
        delivery_address="Dorfstraße 10",
        order_chain=chain,
    )
    result = DryRunCallClient("success_direct").execute_candidate_call(
        SAMPLE_RESTAURANTS[0], request, "fixture-key"
    )

    assert result.structured_result["order_chain_results"]
    passed, reason = CascadeEngine([]).evaluate_result(request, result)
    assert (passed, reason) == (True, None)


@pytest.fixture
def chain_db(tmp_path):
    path = str(tmp_path / "chains.db")
    os.environ["HUNGRYCALL_DB_PATH"] = path
    init_db(path)
    yield path
    os.environ.pop("HUNGRYCALL_DB_PATH", None)


def test_tags_templates_and_submitted_order_round_trip(chain_db):
    chain = make_chain()
    saved_template = save_order_template("Friday", chain.to_dict())
    save_tags(chain.all_tags() + ["Simon"])
    create_order_record(
        "ord_chain", "delivery", "Alex", chain.summary(), 35,
        "Dorfstraße 10", order_chain=chain.to_dict(),
    )

    assert list_order_templates()[0]["id"] == saved_template["id"]
    assert list_tags() == ["Alex", "Simon"]
    assert get_order_record("ord_chain")["order_chain"] == chain.to_dict()


def test_web_editor_is_bilingual_and_history_can_be_loaded(chain_db):
    client = TestClient(web.app)
    chain = make_chain()
    create_order_record(
        "ord_reload", "pickup", "Renate", chain.summary(), 30,
        "Dorfstraße 10", pickup_time="19:45", order_chain=chain.to_dict(),
    )

    german = client.get("/order?history=ord_reload&lang=de").text
    english = client.get("/order?history=ord_reload&lang=en").text

    assert "Bestellwunschketten" in german
    assert "Order wish chains" in english
    assert 'id="criteria-dialog"' in german
    assert 'id="order_chain_json"' in german
    assert "Renate" in german and "19:45" in german
    assert "HC.orderChainInitial" in german

    saved = client.post("/api/order-templates", data={
        "name": "Familienabend",
        "order_chain_json": order_chain_json(chain),
    })
    assert saved.status_code == 200
    assert client.get("/api/order-templates").json()[0]["name"] == "Familienabend"


def test_web_dry_run_uses_chain_and_renders_grouped_tag_summary(chain_db, monkeypatch):
    monkeypatch.setattr(web, "DRY_RUN_DIAL_SECONDS", 0)
    monkeypatch.setattr(web, "DRY_RUN_TURN_SECONDS", 0)
    monkeypatch.setattr(web, "current_clock", lambda: "19:00")
    monkeypatch.setattr(web, "current_day", lambda: "Fri")
    client = TestClient(web.app)
    client.cookies.set("hungrycall_restaurant_test_mode", "on")
    chain = make_chain()
    form = {
        "branch": "food",
        "mode": "delivery",
        "postcode": "12345",
        "city": "Dorfstadt",
        "radius_km": "3.0",
        "delivery_address": "Dorfstraße 10, 12345 Dorfstadt",
        "first_name": "Alex",
        "last_name": "Test",
        "requester_callback_number": "+4910004069000",
        "food_prompt": chain.summary(),
        "order_chain_json": order_chain_json(chain),
        "max_budget_eur": "35.00",
        "scenario": "success_direct",
        "candidate_order": "rest_burger_house",
        "selected_restaurants": ["rest_burger_house"],
    }

    started = client.post("/api/start-cascade?lang=de", data=form)
    order_id = started.text.split('HC.startStream("')[1].split('"')[0]
    stream = client.get(f"/api/cascade-stream?order_id={order_id}&lang=de")
    events = [
        json.loads(line[6:]) for line in stream.text.splitlines()
        if line.startswith("data: ")
    ]
    outcome = next(event for event in events if event["type"] == "outcome")

    assert "Bestellübersicht nach Tags" in outcome["html"]
    assert "Alex" in outcome["html"]
    assert "1× Burger" in outcome["html"]
    assert get_order_record(order_id)["order_chain"] == chain.to_dict()
