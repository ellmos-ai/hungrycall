"""Unit tests for restaurant ranking logic.

Verifies rule: Current food prompt BEATS favorite restaurant.
"""

from hungrycall.models import Mode, OpeningHours, Restaurant, UserRequest
from hungrycall.ranking import (
    filter_and_rank_restaurants,
    filter_candidate,
)


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
    top_restaurant, _top_score = ranked[0]

    # Favorite Italian wins when food prompt matches cuisine
    assert top_restaurant.id == "rest_italian"


def test_distance_weighs_differently_per_mode():
    """The mode switch has to reach the ranking, or it is only a label.

    Same two places, same food: a nearby plain restaurant against a favourite
    four kilometres away. Delivered, the favourite wins — the driver covers the
    distance. Collected, the near one wins, because now the user drives.
    """
    hours = OpeningHours(days=["Fri"], open_time="10:00", close_time="23:00")
    near = Restaurant(
        id="near", name="Ecke", phone="+441632960000", cuisines=["Pizza"],
        opening_hours=hours, lat=52.5200, lon=13.4050, distance_km=0.2,
    )
    far_favorite = Restaurant(
        id="far", name="Mama Mia", phone="+441632960001", cuisines=["Pizza"],
        opening_hours=hours, is_favorite=True,
        lat=52.5560, lon=13.4050, distance_km=4.0,
    )
    candidates = [near, far_favorite]

    def order_for(mode, **extra):
        request = UserRequest(
            mode=mode, customer_name="Alex", food_prompt="Pizza",
            max_budget_eur=35.0, delivery_address="Hauptstraße 1",
            day_of_week="Fri", time_of_request="19:00", **extra,
        )
        return [r.id for r, _ in filter_and_rank_restaurants(candidates, request)]

    assert order_for(Mode.DELIVERY)[0] == "far"
    assert order_for(Mode.PICKUP, pickup_time="19:00")[0] == "near"


def test_distance_limit_removes_candidates_before_any_call():
    hours = OpeningHours(days=["Fri"], open_time="10:00", close_time="23:00")
    far = Restaurant(
        id="far", name="Weit weg", phone="+441632960001", cuisines=["Pizza"],
        opening_hours=hours, distance_km=9.0,
    )
    request = UserRequest(
        mode=Mode.PICKUP, customer_name="Alex", food_prompt="Pizza",
        max_budget_eur=35.0, pickup_time="19:00", max_distance_km=5.0,
        day_of_week="Fri", time_of_request="19:00",
    )
    assert filter_and_rank_restaurants([far], request) == []
    assert "beyond the 5.0 km limit" in filter_candidate(far, request)


def test_place_open_past_midnight_counts_as_open():
    """22:00–04:00 used to read as closed all night, which is backwards."""
    night = OpeningHours(days=["Fri"], open_time="22:00", close_time="04:00")
    assert night.is_open("Fri", "23:30") is True
    assert night.is_open("Fri", "02:00") is True
    assert night.is_open("Fri", "18:00") is False


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
