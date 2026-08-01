"""Unit tests for restaurant ranking logic.

Verifies rule: Current food prompt BEATS favorite restaurant.
"""

from hungrycall.models import Restaurant, OpeningHours, UserRequest, Mode
from hungrycall.ranking import filter_and_rank_restaurants, score_restaurant


def build_sample_candidates():
    open_hours = OpeningHours(
        days=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        open_time="10:00",
        close_time="23:00"
    )
    
    burger_house = Restaurant(
        id="rest_burger",
        name="Dorf Burger Joint",
        phone="+441632960000",
        cuisines=["Burger", "American"],
        opening_hours=open_hours,
        is_favorite=False
    )
    
    favorite_italian = Restaurant(
        id="rest_italian",
        name="Mama Mia Pizza",
        phone="+441632960001",
        cuisines=["Italian", "Pizza"],
        opening_hours=open_hours,
        is_favorite=True
    )
    
    closed_restaurant = Restaurant(
        id="rest_closed",
        name="Closed Diner",
        phone="+441632960002",
        cuisines=["Burger"],
        opening_hours=OpeningHours(days=["Mon"], open_time="10:00", close_time="12:00"),
        is_favorite=False
    )
    
    return [burger_house, favorite_italian, closed_restaurant]


def test_food_prompt_beats_favorite():
    candidates = build_sample_candidates()
    
    # User requests "Burger". Favorite restaurant is Italian.
    request = UserRequest(
        mode=Mode.DELIVERY,
        customer_name="Alex",
        food_prompt="Burger",
        max_budget_eur=35.0,
        delivery_address="Hauptstraße 1",
        day_of_week="Fri",
        time_of_request="19:00"
    )
    
    ranked = filter_and_rank_restaurants(candidates, request)
    
    # Closed restaurant excluded
    assert len(ranked) == 2
    
    # Burger House MUST be ranked #1 above Favorite Italian because food prompt beats favorite
    top_restaurant, top_score = ranked[0]
    second_restaurant, second_score = ranked[1]
    
    assert top_restaurant.id == "rest_burger"
    assert second_restaurant.id == "rest_italian"
    assert top_score > second_score


def test_favorite_wins_when_cuisine_matches():
    candidates = build_sample_candidates()
    
    # User requests "Pizza". Favorite Italian serves Pizza.
    request = UserRequest(
        mode=Mode.DELIVERY,
        customer_name="Alex",
        food_prompt="Pizza",
        max_budget_eur=35.0,
        delivery_address="Hauptstraße 1",
        day_of_week="Fri",
        time_of_request="19:00"
    )
    
    ranked = filter_and_rank_restaurants(candidates, request)
    top_restaurant, top_score = ranked[0]
    
    # Favorite Italian wins when food prompt matches cuisine
    assert top_restaurant.id == "rest_italian"


def test_closed_restaurant_filtered_out():
    candidates = build_sample_candidates()
    
    request = UserRequest(
        mode=Mode.DELIVERY,
        customer_name="Alex",
        food_prompt="Burger",
        day_of_week="Sun",
        time_of_request="20:00"
    )
    
    ranked = filter_and_rank_restaurants(candidates, request)
    candidate_ids = [r[0].id for r in ranked]
    
    assert "rest_closed" not in candidate_ids
