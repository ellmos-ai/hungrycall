"""CALL-E Client abstraction supporting Dry-Run fixture mode and optional Live mode."""

import os
import time
from typing import Dict, Any, Optional, List
from hungrycall.models import CallResult, CallStatus, Mode, Restaurant, UserRequest
from hungrycall.schemas import get_result_schema
from hungrycall.fixtures import SCENARIO_FIXTURES, render_fixture_data, deduplicate_activity
from hungrycall.safety import SafetyError, generate_idempotency_key, verify_phone_safety


class CallClient:
    """Base abstract class for CALL-E interaction."""

    def execute_candidate_call(
        self,
        restaurant: Restaurant,
        user_request: UserRequest,
        idempotency_key: str
    ) -> CallResult:
        raise NotImplementedError


class DryRunCallClient(CallClient):
    """Dry-run client using local fixtures without network or CALL-E account."""

    def __init__(self, scenario_name: str = "success_direct"):
        self.scenario_name = scenario_name
        self.scenario_data = SCENARIO_FIXTURES.get(scenario_name, {})

    def execute_candidate_call(
        self,
        restaurant: Restaurant,
        user_request: UserRequest,
        idempotency_key: str
    ) -> CallResult:
        # Validate E.164 phone safety before dry-run execution as well
        verify_phone_safety(restaurant.phone)

        # Retrieve fixture data for this restaurant ID if available
        raw_mock_entry = self.scenario_data.get(restaurant.id)
        
        if not raw_mock_entry:
            # Fallback default mock result
            raw_mock_entry = {
                "status": CallStatus.FAILED,
                "structured_result": {
                    "delivers_to_address": False,
                    "price_known": False,
                    "order_placed": False,
                    "rejection_reason": "No response / busy line"
                },
                "post_summary": "Call failed to connect.",
                "transcript": [],
                "activity": ["Call initiated", "No response"]
            }

        # Render dynamic fixture interpolated with actual user inputs (address, food, budget, name)
        rendered = render_fixture_data(raw_mock_entry, user_request, restaurant)

        status = rendered.get("status", CallStatus.COMPLETED)
        structured = rendered.get("structured_result", {})
        post_summary = rendered.get("post_summary", "")
        transcript = rendered.get("transcript", [])
        raw_activity = rendered.get("activity", [])
        activity = deduplicate_activity(raw_activity)
        raw_transcript_text = rendered.get("raw_transcript_text", "")
        rejection_reason = structured.get("rejection_reason")

        return CallResult(
            call_id=f"dry_call_{restaurant.id}_{int(time.time())}",
            run_id=f"dry_run_{idempotency_key}",
            status=status,
            task_completed=(status == CallStatus.COMPLETED),
            completion_confidence=0.95,
            structured_result=structured,
            transcript=transcript,
            post_summary=post_summary,
            rejection_reason=rejection_reason,
            activity=activity,
            raw_transcript_text=raw_transcript_text
        )


class LiveCallClient(CallClient):
    """
    Live CALL-E client via REST API (POST /v1/calls).
    Requires explicit --confirm-live flag and CALLE_API_KEY environment variable.
    Note: Schema-validated results require the REST API, not MCP/CLI (Finding 5).
    """

    REST_ENDPOINT = "https://seleven-mcp-sg.airudder.com/v1/calls"

    def __init__(self, confirmed: bool = False):
        if not confirmed:
            raise SafetyError("Live calls strictly require explicit user confirmation!")
        self.confirmed = confirmed
        # Read API key strictly from environment variable, never hardcoded
        self.api_key = os.getenv("CALLE_API_KEY") or os.getenv("IAM_API_KEY")

    def execute_candidate_call(
        self,
        restaurant: Restaurant,
        user_request: UserRequest,
        idempotency_key: str
    ) -> CallResult:
        verify_phone_safety(restaurant.phone)
        if not self.api_key:
            raise SafetyError("CALLE_API_KEY environment variable is not set!")
            
        raise NotImplementedError(
            "Live CALL-E REST API execution is intentionally disabled in this environment per AGENTS.md rules. "
            "To run live calls in production: POST /v1/calls with Bearer $CALLE_API_KEY and result_schema."
        )
