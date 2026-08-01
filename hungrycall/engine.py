"""Cascade Execution Engine for HungryCall sequential phone calls.

Executes candidate calls sequentially until one succeeds or all candidates are exhausted.
Enforces budget limits, exact price quotes, opening hours, and safety rules.
"""

import time
from typing import List, Optional, Tuple
from hungrycall.models import (
    AttemptRecord, CallResult, CallStatus, CascadeSummary,
    Mode, Restaurant, UserRequest
)
from hungrycall.ranking import filter_and_rank_restaurants
from hungrycall.safety import (
    generate_idempotency_key, verify_content_safety, verify_phone_safety
)
from hungrycall.phone_utils import mask_phone
from hungrycall.call_client import CallClient, DryRunCallClient


def build_call_goal(restaurant: Restaurant, request: UserRequest) -> str:
    """Build clear, explicit CALL-E goal text disclosing AI identity and task details."""
    intro = f"Hello, I am an automated assistant calling on behalf of {request.customer_name}."
    
    if request.mode == Mode.DELIVERY:
        return (
            f"{intro} We would like to order food for delivery to {request.delivery_address}. "
            f"Requested items: '{request.food_prompt}'. "
            f"Please verify: 1. Do you deliver to this address? "
            f"2. What is the EXACT total price in EUR including delivery fee and minimum order? "
            f"3. What is the estimated delivery time in minutes? "
            f"4. If total price is within our maximum budget limit of {request.max_budget_eur:.2f} EUR, "
            f"place the order and obtain a direct callback number."
        )
    elif request.mode == Mode.RESERVATION:
        return (
            f"{intro} We would like to reserve a table on {request.reservation_date} "
            f"at {request.reservation_time} for {request.party_size} people. "
            f"Requested area/cuisine preference: '{request.food_prompt}'. "
            f"Please verify table availability and confirm the reservation under the name {request.customer_name}. "
            f"Also obtain a direct callback phone number in case of modifications."
        )
    elif request.mode == Mode.PICKUP:
        return (
            f"{intro} We would like to place a pickup order. "
            f"Requested items: '{request.food_prompt}'. Preferred pickup time: {request.pickup_time}. "
            f"Please verify: 1. Can you prepare this for pickup? "
            f"2. What is the EXACT total price in EUR? "
            f"3. When will the order be ready? "
            f"4. If total price is within our limit of {request.max_budget_eur:.2f} EUR, confirm the pickup order."
        )
    return intro


class CascadeEngine:
    """Orchestrates sequential calling cascade across ranked candidates."""

    def __init__(self, candidate_pool: List[Restaurant], call_client: Optional[CallClient] = None):
        self.candidate_pool = candidate_pool
        self.call_client = call_client or DryRunCallClient()

    def run(self, request: UserRequest) -> CascadeSummary:
        """Run the sequential calling cascade for the given user request."""
        # 1. Content Safety Check
        verify_content_safety(request.food_prompt)

        # 2. Filter & Rank Candidates
        ranked_candidates = filter_and_rank_restaurants(self.candidate_pool, request)
        
        if not ranked_candidates:
            return CascadeSummary(
                success=False,
                mode=request.mode,
                user_request=request,
                attempts=[],
                message="No open or compatible restaurant candidates found for your request."
            )

        attempts: List[AttemptRecord] = []

        # 3. Sequential Cascade
        for restaurant, score in ranked_candidates:
            # Generate idempotency key
            ts = time.time()
            idempotency_key = generate_idempotency_key(request.mode.value, restaurant.id, ts)
            
            # Execute call via CallClient
            result = self.call_client.execute_candidate_call(restaurant, request, idempotency_key)
            
            passed, rejection_reason = self.evaluate_result(request, result)

            attempts.append(
                AttemptRecord(
                    restaurant=restaurant,
                    call_result=result,
                    passed_criteria=passed,
                    rejection_reason=rejection_reason,
                    timestamp=time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts))
                )
            )

            if passed:
                # Criteria met! Stop cascade immediately and return success.
                cb_number = result.structured_result.get("callback_number") or restaurant.phone
                masked_cb = mask_phone(cb_number)
                
                if request.mode == Mode.DELIVERY:
                    price = result.structured_result.get("total_price_eur", 0.0)
                    eta = result.structured_result.get("eta_minutes", 0)
                    success_msg = (
                        f"Ordered from {restaurant.name}: delivers in {eta} minutes, "
                        f"items '{request.food_prompt}', total {price:.2f} EUR. "
                        f"Callback at {masked_cb}."
                    )
                elif request.mode == Mode.RESERVATION:
                    success_msg = (
                        f"Table reserved at {restaurant.name} for {request.party_size} people "
                        f"on {request.reservation_date} at {request.reservation_time}. "
                        f"Callback at {masked_cb}."
                    )
                else:  # PICKUP
                    price = result.structured_result.get("total_price_eur", 0.0)
                    prep = result.structured_result.get("prep_time_minutes", 0)
                    success_msg = (
                        f"Pickup order placed at {restaurant.name}: ready in {prep} minutes, "
                        f"total {price:.2f} EUR. Callback at {masked_cb}."
                    )

                return CascadeSummary(
                    success=True,
                    mode=request.mode,
                    user_request=request,
                    attempts=attempts,
                    successful_restaurant=restaurant,
                    final_result=result,
                    message=success_msg
                )

        # 4. Exhausted list without success
        return CascadeSummary(
            success=False,
            mode=request.mode,
            user_request=request,
            attempts=attempts,
            message="Attempted all available candidates, but none satisfied the criteria."
        )

    def evaluate_result(self, request: UserRequest, result: CallResult) -> Tuple[bool, Optional[str]]:
        """Evaluate call result against mode criteria and budget limits."""
        if result.status != CallStatus.COMPLETED:
            return False, f"Call failed with status '{result.status.value}'"

        struct = result.structured_result

        if request.mode == Mode.DELIVERY:
            # 1. Delivers to address
            if not struct.get("delivers_to_address", False):
                return False, "Restaurant does not deliver to specified address"
                
            # 2. Price known (EXACT quote rule)
            if not struct.get("price_known", False):
                reason = struct.get("rejection_reason") or "Unclear price statement (vague or missing exact quote)"
                return False, reason

            # 3. Maximum total budget limit rule
            total_price = struct.get("total_price_eur")
            if total_price is None:
                return False, "Unclear price statement: total_price_eur missing"
                
            if request.max_budget_eur is not None and total_price > request.max_budget_eur:
                return False, (
                    f"Total price {total_price:.2f} EUR exceeds maximum budget limit "
                    f"of {request.max_budget_eur:.2f} EUR"
                )

            # 4. Order placed
            if not struct.get("order_placed", False):
                return False, struct.get("rejection_reason") or "Order was not placed"

            return True, None

        elif request.mode == Mode.RESERVATION:
            if not struct.get("table_available", False):
                return False, struct.get("rejection_reason") or "No table available for requested date and time"

            if not struct.get("reservation_confirmed", False):
                return False, struct.get("rejection_reason") or "Reservation was not confirmed"

            return True, None

        elif request.mode == Mode.PICKUP:
            if not struct.get("pickup_available", False):
                return False, "Pickup not available at restaurant"

            if not struct.get("price_known", False):
                reason = struct.get("rejection_reason") or "Unclear price statement"
                return False, reason

            total_price = struct.get("total_price_eur")
            if total_price is None:
                return False, "Unclear price statement: total_price_eur missing"

            if request.max_budget_eur is not None and total_price > request.max_budget_eur:
                return False, (
                    f"Total price {total_price:.2f} EUR exceeds maximum budget limit "
                    f"of {request.max_budget_eur:.2f} EUR"
                )

            if not struct.get("order_placed", False):
                return False, struct.get("rejection_reason") or "Pickup order was not placed"

            return True, None

        return False, f"Unknown mode {request.mode}"
