"""Restaurant candidate filtering and ranking engine.

Rule: The current food prompt ALWAYS beats a favorite restaurant if the favorite
does not match the requested food category.
"""

from typing import List, Tuple
from hungrycall.models import Restaurant, UserRequest, Mode


def score_restaurant(restaurant: Restaurant, request: UserRequest) -> float:
    """Calculate ranking score for a candidate restaurant based on request."""
    score = 0.0
    food_prompt_clean = request.food_prompt.lower().strip()
    
    # 1. Food prompt cuisine / keyword matching (highest priority: +100 per match)
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
        
    # 2. Favorite bonus (+20), but only if food match exists OR prompt is generic ("food", "dinner")
    is_fav = restaurant.is_favorite or (restaurant.id in request.favorite_restaurant_ids)
    if is_fav:
        is_generic_prompt = not prompt_words or any(w in food_prompt_clean for w in ["essen", "food", "dinner", "hunger"])
        if food_match_found or is_generic_prompt:
            score += 20.0
        else:
            # Minor fallback bonus (+5) for favorite if completely different food requested, but food match still vastly outweighs it
            score += 5.0
            
    return score


def filter_and_rank_restaurants(
    candidates: List[Restaurant],
    request: UserRequest
) -> List[Tuple[Restaurant, float]]:
    """Filter closed or incompatible restaurants and rank remaining candidates descending by score."""
    ranked: List[Tuple[Restaurant, float]] = []
    
    req_time = request.reservation_time or request.pickup_time or request.time_of_request
    
    for candidate in candidates:
        # Check opening hours
        if not candidate.opening_hours.is_open(request.day_of_week, req_time):
            continue
            
        # Check mode capabilities
        if request.mode == Mode.DELIVERY and not candidate.supports_delivery:
            continue
        if request.mode == Mode.RESERVATION and not candidate.supports_reservation:
            continue
        if request.mode == Mode.PICKUP and not candidate.supports_pickup:
            continue
            
        score = score_restaurant(candidate, request)
        ranked.append((candidate, score))
        
    # Sort descending by score
    ranked.sort(key=lambda item: item[1], reverse=True)
    return ranked
