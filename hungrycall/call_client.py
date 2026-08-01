"""CALL-E Client abstraction supporting Dry-Run fixture mode and optional Live mode."""

import time
from typing import Dict, Any, Optional
from hungrycall.models import CallResult, CallStatus, Mode, Restaurant, UserRequest
from hungrycall.schemas import get_result_schema
from hungrycall.fixtures import SCENARIO_FIXTURES
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
        mock_entry = self.scenario_data.get(restaurant.id)
        
        if not mock_entry:
            # Fallback default mock result
            mock_entry = {
                "status": CallStatus.FAILED,
                "structured_result": {
                    "delivers_to_address": False,
                    "price_known": False,
                    "order_placed": False,
                    "rejection_reason": "No response / busy line"
                },
                "post_summary": "Call failed to connect.",
                "transcript": []
            }

        status = mock_entry.get("status", CallStatus.COMPLETED)
        structured = mock_entry.get("structured_result", {})
        post_summary = mock_entry.get("post_summary", "")
        transcript = mock_entry.get("transcript", [])
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
            rejection_reason=rejection_reason
        )


class LiveCallClient(CallClient):
    """Live CALL-E client. Requires account and --live confirmation."""

    def __init__(self, confirmed: bool = False):
        if not confirmed:
            raise SafetyError("Live calls strictly require explicit user confirmation!")
        self.confirmed = confirmed

    def execute_candidate_call(
        self,
        restaurant: Restaurant,
        user_request: UserRequest,
        idempotency_key: str
    ) -> CallResult:
        verify_phone_safety(restaurant.phone)
        raise NotImplementedError(
            "Live CALL-E API execution is intentionally disabled in this environment per AGENTS.md rules."
        )
