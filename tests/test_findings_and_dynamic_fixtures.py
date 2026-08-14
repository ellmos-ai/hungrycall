"""Tests for measured FINDINGS.md behavior and dynamic input fixture reflection."""

from hungrycall.call_client import DryRunCallClient
from hungrycall.cli import main
from hungrycall.fixtures import SAMPLE_RESTAURANTS, deduplicate_activity
from hungrycall.models import Mode, UserRequest


def test_dynamic_user_input_reflection_in_transcript():
    """Verify user inputs (address, customer name, food, budget) are reflected dynamically in transcript."""
    client = DryRunCallClient(scenario_name="success_direct")
    req = UserRequest(
        mode=Mode.DELIVERY,
        customer_name="Max Mustermann",
        food_prompt="2x Döner Kebab",
        max_budget_eur=28.0,
        delivery_address="Dorfstrasse 1, 16321 Bernau"
    )
    restaurant = SAMPLE_RESTAURANTS[0]
    result = client.execute_candidate_call(restaurant, req, "idemp_test_123")

    # Assert exact inputs are present in transcript text and raw_transcript_text
    assert "Dorfstrasse 1, 16321 Bernau" in result.raw_transcript_text
    assert "Max Mustermann" in result.raw_transcript_text
    assert "2x Döner Kebab" in result.raw_transcript_text
    assert "28.00" in result.raw_transcript_text

    # Assert speaker normalization uses BOT and USER as measured in real CALL-E runs
    assert "[00:05] BOT: Hello, I am an automated assistant calling on behalf of Max Mustermann. Do you deliver to Dorfstrasse 1, 16321 Bernau?" in result.raw_transcript_text
    assert "[00:10] USER: Yes, we deliver to Dorfstrasse 1, 16321 Bernau." in result.raw_transcript_text


def test_cli_reflects_custom_user_address(capsys):
    """Test CLI execution output reflects custom user address and prompt."""
    ret = main([
        "delivery",
        "--food", "2x Schnitzel Wiener Art",
        "--address", "Dorfstrasse 1, 16321 Bernau",
        "--budget", "40.0",
        "--customer-name", "Julia",
        "--scenario", "success_direct"
    ])
    assert ret == 0
    captured = capsys.readouterr()
    assert "Dorfstrasse 1, 16321 Bernau" in captured.out
    assert "2x Schnitzel Wiener Art" in captured.out
    assert "Julia" in captured.out
    assert "[00:05] BOT: Hello, I am an automated assistant calling on behalf of Julia" in captured.out


def test_activity_stt_deduplication():
    """Test deduplication of streaming raw STT drafts when followed by corrected versions."""
    raw_events = [
        "17:37:05.100 | Bot initialized.",
        "17:37:44.200 | Call is ringing (~40s setup latency).",
        "17:37:49.500 | Call connected.",
        "17:37:50.700 | Bot is speaking: Hello, calling on behalf of Alex.",
        "17:37:51.500 | Callee said: ja",
        "17:37:52.200 | Callee said: Ja, wir liefern nach Bernau.",
        "17:38:21.300 | Call ended."
    ]
    deduped = deduplicate_activity(raw_events)
    # The raw STT draft "Callee said: ja" should be removed in favor of "Callee said: Ja, wir liefern..."
    assert len(deduped) == 6
    assert not any(e == "17:37:51.500 | Callee said: ja" for e in deduped)
    assert any(e == "17:37:52.200 | Callee said: Ja, wir liefern nach Bernau." for e in deduped)


def test_activity_log_contains_40s_setup_latency_notice():
    """Verify activity log contains the ~40s setup latency notice."""
    client = DryRunCallClient(scenario_name="success_direct")
    req = UserRequest(
        mode=Mode.DELIVERY,
        customer_name="Alex",
        food_prompt="Burger",
        max_budget_eur=30.0,
        delivery_address="Marktplatz 5"
    )
    result = client.execute_candidate_call(SAMPLE_RESTAURANTS[0], req, "idemp_40s")
    assert any("~40s setup latency" in act for act in result.activity)
