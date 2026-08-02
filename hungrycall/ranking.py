"""Candidate filtering and ranking.

Two rules carry this module:

1. The current food prompt beats a favourite. Someone who wants a burger does
   not want their favourite Italian place.
2. The mode decides what distance is worth. Delivery, pickup and table are
   three different journeys, so they cannot share one weighting.
"""

from typing import List, Optional, Tuple

from hungrycall.geo import haversine_km
from hungrycall.models import Mode, Restaurant, Seating, UserRequest

# Penalty in score points per kilometre, per mode.
# Delivery is nearly flat on purpose: the driver covers the distance, and the
# price of that is already inside the doorstep total the user caps.
DISTANCE_PENALTY_PER_KM = {
    Mode.DELIVERY: 1.0,
    Mode.PICKUP: 12.0,
    Mode.RESERVATION: 5.0,
}


def annotate_distances(
    candidates: List[Restaurant],
    origin_lat: Optional[float],
    origin_lon: Optional[float],
) -> List[Restaurant]:
    """Fill in distance_km for every candidate, in place, and return the list."""
    if origin_lat is None or origin_lon is None:
        return candidates
    for candidate in candidates:
        candidate.distance_km = round(
            haversine_km(origin_lat, origin_lon, candidate.lat, candidate.lon), 2
        )
    return candidates


def score_restaurant(restaurant: Restaurant, request: UserRequest) -> float:
    """Calculate the ranking score for one candidate."""
    score = 0.0
    food_prompt_clean = request.food_prompt.lower().strip()

    # 1. Food prompt / cuisine keyword match (highest weight: +100 per match)
    prompt_words = [w for w in food_prompt_clean.replace(",", " ").split() if len(w) > 2]
    food_match_found = False

    for cuisine in restaurant.cuisines:
        cuisine_clean = cuisine.lower()
        if any(word in cuisine_clean or cuisine_clean in word for word in prompt_words):
            score += 100.0
            food_match_found = True

    if any(word in restaurant.name.lower() for word in prompt_words):
        score += 50.0
        food_match_found = True

    # 2. Favourite bonus (+20), but only when the food actually matches or the
    #    prompt is generic. Otherwise a small consolation bonus that a real food
    #    match still outweighs by far.
    is_fav = restaurant.is_favorite or (restaurant.id in request.favorite_restaurant_ids)
    if is_fav:
        is_generic_prompt = not prompt_words or any(
            w in food_prompt_clean for w in ["essen", "food", "dinner", "hunger"]
        )
        score += 20.0 if (food_match_found or is_generic_prompt) else 5.0

    # 3. Distance, weighted by what the mode actually asks of the user.
    if restaurant.distance_km is not None:
        score -= restaurant.distance_km * DISTANCE_PENALTY_PER_KM.get(request.mode, 1.0)

    # 4. Table wishes that rank rather than block.
    if request.mode == Mode.RESERVATION:
        if request.seating == Seating.OUTDOOR and restaurant.has_outdoor_seating:
            score += 40.0
        if request.party_size and restaurant.max_party_size >= request.party_size:
            # A place that seats the group comfortably beats one that just fits.
            score += min(20.0, (restaurant.max_party_size - request.party_size) * 2.0)

    return score


def filter_candidate(restaurant: Restaurant, request: UserRequest) -> Optional[str]:
    """Return a reason to skip this candidate before calling, or None to keep it.

    Everything decided here saves a real phone call, so the bar is: only skip on
    facts we already hold. Anything that would need asking belongs in the call.
    """
    if not restaurant.opening_hours.is_open(request.day_of_week, request.effective_time()):
        return "closed at the requested time"

    if request.mode == Mode.DELIVERY and not restaurant.supports_delivery:
        return "does not deliver"
    if request.mode == Mode.PICKUP and not restaurant.supports_pickup:
        return "no pickup offered"
    if request.mode == Mode.RESERVATION and not restaurant.supports_reservation:
        return "takes no reservations"

    if (
        request.max_distance_km is not None
        and restaurant.distance_km is not None
        and restaurant.distance_km > request.max_distance_km
    ):
        return f"{restaurant.distance_km:.1f} km away, beyond the {request.max_distance_km:.1f} km limit"

    # A group larger than the house can seat is a fact, not a negotiation.
    if (
        request.mode == Mode.RESERVATION
        and request.party_size
        and restaurant.max_party_size < request.party_size
    ):
        return f"seats at most {restaurant.max_party_size} people"

    return None


def filter_and_rank_restaurants(
    candidates: List[Restaurant],
    request: UserRequest,
) -> List[Tuple[Restaurant, float]]:
    """Drop candidates that cannot work, rank the rest, best first."""
    ranked: List[Tuple[Restaurant, float]] = [
        (candidate, score_restaurant(candidate, request))
        for candidate in candidates
        if filter_candidate(candidate, request) is None
    ]
    ranked.sort(key=lambda item: item[1], reverse=True)
    return ranked
