"""Integration tests for HungryCall CLI."""

import json
from hungrycall.cli import main


def test_cli_delivery_dry_run(capsys):
    ret = main([
        "delivery",
        "--food", "Burger",
        "--address", "Hauptstraße 12",
        "--budget", "35.0",
        "--scenario", "success_direct"
    ])
    assert ret == 0
    captured = capsys.readouterr()
    assert "HUNGRYCALL — Cascade Agent Execution" in captured.out
    assert "RESULT: SUCCESS" in captured.out
    assert "Ordered from Burger House Dorfstadt" in captured.out


def test_cli_delivery_json_output(capsys):
    ret = main([
        "delivery",
        "--food", "Burger",
        "--address", "Hauptstraße 12",
        "--budget", "35.0",
        "--scenario", "success_direct",
        "--json-output"
    ])
    assert ret == 0
    captured = capsys.readouterr()
    parsed = json.loads(captured.out)
    assert parsed["success"] is True
    assert parsed["mode"] == "delivery"
    assert len(parsed["attempts"]) == 1


def test_cli_budget_exceeded_scenario(capsys):
    ret = main([
        "delivery",
        "--food", "Burger",
        "--address", "Hauptstraße 12",
        "--budget", "35.0",
        "--scenario", "budget_exceeded_cascade"
    ])
    assert ret == 0
    captured = capsys.readouterr()
    assert "Attempt #1: Burger House Dorfstadt" in captured.out
    assert "exceeds maximum budget limit" in captured.out
    assert "Attempt #2: Trattoria Bella Luigi" in captured.out
    assert "RESULT: SUCCESS" in captured.out


def test_cli_reservation(capsys):
    ret = main([
        "reservation",
        "--food", "Italian",
        "--date", "2026-08-05",
        "--time", "19:00",
        "--party", "4",
        "--scenario", "reservation_cascade"
    ])
    assert ret == 0
    captured = capsys.readouterr()
    assert "Table reserved at Trattoria Bella Luigi" in captured.out


def test_cli_pickup(capsys):
    ret = main([
        "pickup",
        "--food", "Burger",
        "--budget", "25.0",
        "--scenario", "pickup_cascade"
    ])
    assert ret == 0
    captured = capsys.readouterr()
    assert "Pickup order placed at Burger House Dorfstadt" in captured.out


def test_cli_live_without_confirm_fails(capsys):
    ret = main([
        "delivery",
        "--food", "Burger",
        "--address", "Hauptstraße 12",
        "--budget", "35.0",
        "--live"
    ])
    assert ret == 2
    captured = capsys.readouterr()
    assert "ERROR: Live execution requires explicit confirmation" in captured.err


def test_cli_demo_subcommand(capsys):
    ret = main(["demo"])
    assert ret == 0
    captured = capsys.readouterr()
    assert "HUNGRYCALL — Cascade Agent Execution" in captured.out
    assert "Attempt #1: Trattoria Bella Luigi" in captured.out
    assert "Unclear price statement" in captured.out
    assert "Attempt #2: Burger House Dorfstadt" in captured.out
    assert "exceeds maximum budget limit" in captured.out
    assert "Attempt #3: Asia Wok Express" in captured.out
    assert "RESULT: SUCCESS" in captured.out
    assert "Ordered from Asia Wok Express" in captured.out
    assert "Verification Transcript (Order Proof):" in captured.out

