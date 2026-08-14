"""Command Line Interface for HungryCall ("I am hungry")."""

import argparse
import json
import math
import sys

from hungrycall import field_trial
from hungrycall.call_client import (
    CalleAPIError,
    DryRunCallClient,
    LiveCallClient,
    load_calle_settings,
    probe_calle_connection,
)
from hungrycall.engine import CascadeEngine
from hungrycall.fixtures import SAMPLE_RESTAURANTS, SCENARIO_FIXTURES
from hungrycall.geo import weekday_key
from hungrycall.models import Mode, Seating, UserRequest
from hungrycall.phone_utils import mask_phone, normalize_e164, validate_e164
from hungrycall.safety import SINGAPORE_ENDPOINT_NOTICE, SafetyError


def build_parser() -> argparse.ArgumentParser:
    # Common parent parser for flags shared across all subcommands
    common_parser = argparse.ArgumentParser(add_help=False)
    common_parser.add_argument("--live", action="store_true", help="Execute live call via CALL-E (default: False / Dry-run)")
    common_parser.add_argument("--confirm-live", action="store_true", help="Explicit user confirmation required for live execution")
    common_parser.add_argument("--env-file", help="External CALL-E .env path (default: operator credential path)")
    common_parser.add_argument("--json-output", action="store_true", help="Print output in JSON format")
    common_parser.add_argument(
        "--requester-callback-number",
        help="Human callback number in E.164 format; mandatory for live calls",
    )

    parser = argparse.ArgumentParser(
        prog="hungrycall",
        description="HungryCall — Sequential automated voice cascade for food delivery, reservations, and pickup.",
        parents=[common_parser]
    )

    subparsers = parser.add_subparsers(dest="subcommand", help="HungryCall command modes")

    # Delivery subcommand
    deliv_parser = subparsers.add_parser("delivery", parents=[common_parser], help="Order food for delivery within budget")
    deliv_parser.add_argument("--food", required=True, help="Food prompt or items (e.g. 'Burger', '2 Pizza Margherita')")
    deliv_parser.add_argument("--address", required=True, help="Delivery address")
    deliv_parser.add_argument("--budget", type=float, required=True, help="Maximum total budget in EUR (including delivery fee)")
    deliv_parser.add_argument("--customer-name", default="Alex", help="Name of person placing order")
    deliv_parser.add_argument("--scenario", default="success_direct", choices=list(SCENARIO_FIXTURES.keys()), help="Dry-run scenario preset")

    # Reservation subcommand
    res_parser = subparsers.add_parser("reservation", parents=[common_parser], help="Reserve a table at a restaurant")
    res_parser.add_argument("--food", required=True, help="Food / cuisine prompt (e.g. 'Italian', 'Sushi')")
    res_parser.add_argument("--date", required=True, help="Reservation date (YYYY-MM-DD)")
    res_parser.add_argument("--time", required=True, help="Reservation time (HH:MM)")
    res_parser.add_argument("--party", type=int, required=True, help="Number of guests")
    res_parser.add_argument("--customer-name", default="Alex", help="Name under which to reserve")
    res_parser.add_argument("--seating", default="any", choices=[s.value for s in Seating], help="Where you want to sit")
    res_parser.add_argument("--seating-custom", help="Specific table request; requires --seating custom")
    res_parser.add_argument("--note", help="Additional restaurant note")
    res_parser.add_argument("--earlier-hours", type=int, choices=range(4), default=0)
    res_parser.add_argument("--later-hours", type=int, choices=range(4), default=0)
    res_parser.add_argument("--earlier-minutes", type=int, choices=range(60), default=0)
    res_parser.add_argument("--later-minutes", type=int, choices=range(60), default=0)
    res_parser.add_argument("--max-booking-fee-eur", type=float, default=0.0)
    res_parser.add_argument("--scenario", default="reservation_cascade", choices=list(SCENARIO_FIXTURES.keys()), help="Dry-run scenario preset")

    # Pickup subcommand
    pickup_parser = subparsers.add_parser("pickup", parents=[common_parser], help="Place a pickup order")
    pickup_parser.add_argument("--food", required=True, help="Food prompt or items")
    pickup_parser.add_argument("--budget", type=float, required=True, help="Maximum total budget in EUR")
    pickup_parser.add_argument("--pickup-time", default="19:30", help="Preferred pickup time (HH:MM)")
    pickup_parser.add_argument("--customer-name", default="Alex", help="Name of person picking up")
    pickup_parser.add_argument("--scenario", default="pickup_cascade", choices=list(SCENARIO_FIXTURES.keys()), help="Dry-run scenario preset")

    # Demo subcommand (30-second reproducible core dry-run demo for jurors without accounts)
    demo_parser = subparsers.add_parser("demo", parents=[common_parser], help="Run 30-second reproducible core cascade demo for jurors (no account required)")
    demo_parser.add_argument("--customer-name", default="Alex", help="Name of person placing demo order")

    # Authenticated, read-only network check. This subcommand has no phone
    # number argument and its implementation never calls POST /v1/calls.
    probe_parser = subparsers.add_parser(
        "preflight",
        parents=[common_parser],
        help="Check CALL-E credentials with a read-only GET; never place a call",
    )
    probe_parser.add_argument("--timeout", type=float, default=10.0, help="Network timeout in seconds")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.subcommand:
        parser.print_help()
        return 1

    if args.subcommand == "preflight":
        print("CALL-E PREFLIGHT — read-only; no call will be placed")
        try:
            settings = load_calle_settings(env_file=args.env_file)
            result = probe_calle_connection(settings, timeout_seconds=args.timeout)
        except SafetyError as err:
            print(f"PREFLIGHT ERROR: {err}", file=sys.stderr)
            return 3
        source = str(settings.env_file) if settings.env_file else "process environment"
        print(f"Credentials: {source}")
        print(f"Endpoint: {result.base_url}")
        print(f"HTTP: {result.status_code}")
        print(f"Result: {result.detail}")
        print("Confirmed: no POST /v1/calls was sent.")
        return 0 if result.authenticated else 4

    callback_number = ""
    if args.requester_callback_number:
        callback_number = normalize_e164(args.requester_callback_number)
        if not validate_e164(callback_number):
            print(
                "ERROR: --requester-callback-number must be a valid E.164 phone number.",
                file=sys.stderr,
            )
            return 2

    # Safety live check
    if args.live:
        if not args.confirm_live:
            print("ERROR: Live execution requires explicit confirmation via --confirm-live flag.", file=sys.stderr)
            return 2
        if not callback_number:
            print(
                "ERROR: Live execution requires --requester-callback-number so the restaurant can contact a human.",
                file=sys.stderr,
            )
            return 2
        print("WARNING: Echte Anrufe — kostet Geld / Real calls — cost money.", file=sys.stderr)
        try:
            call_client = LiveCallClient.from_environment(
                confirmed=True, env_file=args.env_file
            )
        except SafetyError as err:
            print(f"SAFETY ERROR: {err}", file=sys.stderr)
            return 3
    else:
        if args.subcommand == "demo":
            scenario = "jury_30s_demo"
        else:
            scenario = getattr(args, "scenario", "success_direct")
        call_client = DryRunCallClient(scenario_name=scenario)

    # Build UserRequest
    if args.subcommand == "demo":
        req = UserRequest(
            mode=Mode.DELIVERY,
            customer_name=getattr(args, "customer_name", "Alex"),
            food_prompt="2x Döner Kebab & Drinks",
            max_budget_eur=35.0,
            delivery_address="Dorfstrasse 1, 16321 Bernau",
            requester_callback_number=callback_number or None,
        )
    elif args.subcommand == "delivery":
        req = UserRequest(
            mode=Mode.DELIVERY,
            customer_name=args.customer_name,
            food_prompt=args.food,
            max_budget_eur=args.budget,
            delivery_address=args.address,
            requester_callback_number=callback_number or None,
        )
    elif args.subcommand == "reservation":
        if args.seating == "custom" and not (args.seating_custom or "").strip():
            print("ERROR: --seating custom requires --seating-custom.", file=sys.stderr)
            return 2
        if args.seating != "custom" and args.seating_custom:
            print("ERROR: --seating-custom requires --seating custom.", file=sys.stderr)
            return 2
        if not math.isfinite(args.max_booking_fee_eur) or args.max_booking_fee_eur < 0:
            print("ERROR: --max-booking-fee-eur must be a finite non-negative amount.", file=sys.stderr)
            return 2
        req = UserRequest(
            mode=Mode.RESERVATION,
            customer_name=args.customer_name,
            food_prompt=args.food,
            reservation_date=args.date,
            reservation_time=args.time,
            party_size=args.party,
            seating=Seating(args.seating),
            seating_custom=(args.seating_custom or "").strip() or None,
            special_instructions=(args.note or "").strip() or None,
            earlier_hours=args.earlier_hours,
            later_hours=args.later_hours,
            earlier_minutes=args.earlier_minutes,
            later_minutes=args.later_minutes,
            max_booking_fee_eur=args.max_booking_fee_eur,
            day_of_week=weekday_key(args.date),
            requester_callback_number=callback_number or None,
        )
    elif args.subcommand == "pickup":
        req = UserRequest(
            mode=Mode.PICKUP,
            customer_name=args.customer_name,
            food_prompt=args.food,
            max_budget_eur=args.budget,
            pickup_time=args.pickup_time,
            requester_callback_number=callback_number or None,
        )
    else:
        print(f"Unknown subcommand {args.subcommand}", file=sys.stderr)
        return 1

    candidate_pool = SAMPLE_RESTAURANTS
    if args.live:
        # Fixture numbers belong to nobody we may dial. A live run either
        # carries the consenting field-trial number or refuses to start.
        try:
            candidate_pool, trial_number = field_trial.apply(candidate_pool)
        except SafetyError as err:
            print(f"SAFETY ERROR: {err}", file=sys.stderr)
            return 3
        if trial_number:
            print(f"FIELD TRIAL: every live call goes to {mask_phone(trial_number)}")

    engine = CascadeEngine(candidate_pool=candidate_pool, call_client=call_client)

    try:
        summary = engine.run(req)
    except SafetyError as err:
        print(f"SAFETY ERROR: {err}", file=sys.stderr)
        return 3
    except (CalleAPIError, RuntimeError, TimeoutError) as err:
        print(f"CALL-E ERROR: {err} Cascade stopped.", file=sys.stderr)
        return 4

    if args.json_output:
        out = {
            "success": summary.success,
            "mode": summary.mode.value,
            "message": summary.message,
            "attempts": [
                {
                    "restaurant": att.restaurant.name,
                    "phone": mask_phone(att.restaurant.phone),
                    "passed": att.passed_criteria,
                    "rejection_reason": att.rejection_reason,
                    "activity": att.call_result.activity if att.call_result else [],
                    "raw_transcript": att.call_result.raw_transcript_text if att.call_result else ""
                }
                for att in summary.attempts
            ]
        }
        print(json.dumps(out, indent=2, ensure_ascii=False))
        return 0 if summary.success else 1

    # Formatted CLI console output
    print("=" * 60)
    print("HUNGRYCALL — Cascade Agent Execution")
    print(f"Mode: {summary.mode.value.upper()} | Prompt: '{req.food_prompt}'")
    if req.max_budget_eur:
        print(f"Maximum Total Budget: {req.max_budget_eur:.2f} EUR (doorstep end price limit)")
    print(f"Execution Mode: {'LIVE' if args.live else 'DRY-RUN (Fixtures)'}")
    print("=" * 60)
    print(SINGAPORE_ENDPOINT_NOTICE)
    print("-" * 60)

    print("\nAttempt History & Activity Stream:")
    for idx, att in enumerate(summary.attempts, start=1):
        status_symbol = "[PASSED]" if att.passed_criteria else "[REJECTED]"
        masked_num = mask_phone(att.restaurant.phone)
        print(f"\n  Attempt #{idx}: {att.restaurant.name} ({masked_num}) -> {status_symbol}")
        if not att.passed_criteria and att.rejection_reason:
            print(f"    Reason: {att.rejection_reason}")
        if att.call_result and att.call_result.activity:
            print("    Live Activity Progress:")
            for act in att.call_result.activity:
                print(f"      * {act}")

    print("\n" + "=" * 60)
    if summary.success:
        print("RESULT: SUCCESS")
        print(f"SUMMARY: {summary.message}")
        if summary.final_result:
            if summary.final_result.raw_transcript_text:
                print("\nVerification Transcript (Order Proof):")
                for line in summary.final_result.raw_transcript_text.splitlines():
                    print(f"  {line}")
            elif summary.final_result.transcript:
                print("\nVerification Transcript (Order Proof):")
                for turn in summary.final_result.transcript:
                    print(f"  [{turn.get('ts', '')}] {turn.get('speaker', '')}: {turn.get('text', '')}")
    else:
        print("RESULT: FAILED")
        print(f"SUMMARY: {summary.message}")
    print("=" * 60)

    return 0 if summary.success else 1


if __name__ == "__main__":
    sys.exit(main())
