"""Location geocoding and OpenStreetMap Overpass restaurant search module."""

import json
import logging
from typing import Dict, Any, List, Tuple, Optional
import httpx
from hungrycall.models import Restaurant, OpeningHours
from hungrycall.fixtures import SAMPLE_RESTAURANTS

logger = logging.getLogger(__name__)

# Preset geocoding coordinates for offline/fixture mode (International support)
OFFLINE_LOCATIONS: Dict[str, Tuple[float, float]] = {
    "singapore": (1.3521, 103.8198),
    "london": (51.5074, -0.1278),
    "new york": (40.7128, -74.0060),
    "berlin": (52.5200, 13.4050),
    "munich": (48.1351, 11.5820),
    "dorfstadt": (52.5200, 13.4050),
    "default": (52.5200, 13.4050)
}

# Rich offline fixtures per location for offline demo presentation
OFFLINE_RESTAURANTS_BY_LOC: Dict[str, List[Restaurant]] = {
    "singapore": [
        Restaurant(
            id="rest_sg_hawker",
            name="Lau Pa Sat Hawker Center",
            phone="+6500000001",
            cuisines=["Asian", "Satay", "Singaporean"],
            opening_hours=OpeningHours(days=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"], open_time="08:00", close_time="23:30"),
            is_favorite=True,
            supports_delivery=True,
            supports_pickup=True,
            address="18 Raffles Quay, Singapore",
            lat=1.2806,
            lon=103.8504
        ),
        Restaurant(
            id="rest_sg_din_tai",
            name="Din Tai Fung Marina Bay",
            phone="+6500000002",
            cuisines=["Asian", "Dim Sum", "Dumplings"],
            opening_hours=OpeningHours(days=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"], open_time="11:00", close_time="21:30"),
            is_favorite=False,
            supports_delivery=True,
            supports_pickup=True,
            address="2 Bayfront Ave, Singapore",
            lat=1.2838,
            lon=103.8591
        ),
        Restaurant(
            id="rest_sg_closed_bistro",
            name="Midnight Hainan Chicken",
            phone="+6500000003",
            cuisines=["Asian", "Chicken Rice"],
            opening_hours=OpeningHours(days=["Fri", "Sat"], open_time="23:00", close_time="04:00"),
            is_favorite=False,
            supports_delivery=True,
            supports_pickup=True,
            address="Geylang Road 12, Singapore",
            lat=1.3140,
            lon=103.8820
        )
    ],
    "london": [
        Restaurant(
            id="rest_uk_dishoom",
            name="Dishoom Covent Garden",
            phone="+442079460930",
            cuisines=["Indian", "Curry", "Grill"],
            opening_hours=OpeningHours(days=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"], open_time="08:00", close_time="23:00"),
            is_favorite=True,
            supports_delivery=True,
            supports_pickup=True,
            address="12 Upper St Martin's Ln, London",
            lat=51.5126,
            lon=-0.1265
        ),
        Restaurant(
            id="rest_uk_burger",
            name="Honest Burgers Soho",
            phone="+442079460931",
            cuisines=["Burger", "British"],
            opening_hours=OpeningHours(days=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"], open_time="11:30", close_time="22:30"),
            is_favorite=False,
            supports_delivery=True,
            supports_pickup=True,
            address="4A Meard St, London",
            lat=51.5134,
            lon=-0.1325
        )
    ],
    "default": [
        Restaurant(
            id="rest_burger_house",
            name="Burger House Dorfstadt",
            phone="+441632960000",
            cuisines=["Burger", "American", "Fast Food"],
            opening_hours=OpeningHours(days=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"], open_time="11:00", close_time="23:00"),
            is_favorite=False,
            supports_delivery=True,
            supports_pickup=True,
            supports_reservation=True,
            address="Dorfstraße 5, 12345 Dorfstadt",
            lat=52.5220,
            lon=13.4080
        ),
        Restaurant(
            id="rest_trattoria_luigi",
            name="Trattoria Bella Luigi",
            phone="+441632960001",
            cuisines=["Italian", "Pizza", "Pasta"],
            opening_hours=OpeningHours(days=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"], open_time="12:00", close_time="22:00"),
            is_favorite=True,
            supports_delivery=True,
            supports_pickup=True,
            supports_reservation=True,
            address="Marktplatz 1, 12345 Dorfstadt",
            lat=52.5180,
            lon=13.4020
        ),
        Restaurant(
            id="rest_asian_wok",
            name="Asia Wok Express",
            phone="+441632960002",
            cuisines=["Asian", "Chinese", "Noodles"],
            opening_hours=OpeningHours(days=["Wed", "Thu", "Fri", "Sat", "Sun"], open_time="16:00", close_time="22:00"),
            is_favorite=False,
            supports_delivery=True,
            supports_pickup=True,
            supports_reservation=False,
            address="Bahnhofstraße 12, 12345 Dorfstadt",
            lat=52.5240,
            lon=13.3980
        ),
        Restaurant(
            id="rest_closed_diner",
            name="Late Night Snack Shack",
            phone="+441632960003",
            cuisines=["Burger", "Snack"],
            opening_hours=OpeningHours(days=["Fri", "Sat"], open_time="22:00", close_time="04:00"),
            is_favorite=False,
            supports_delivery=True,
            supports_pickup=True,
            supports_reservation=False,
            address="Industriestraße 8, 12345 Dorfstadt",
            lat=52.5150,
            lon=13.4120
        )
    ]
}


def geocode_location(postcode: str, city: str, country: str) -> Tuple[float, float]:
    """Resolve location to lat/lon using Nominatim API with offline fallback."""
    city_clean = city.strip().lower()
    country_clean = country.strip().lower()

    # Check offline presets first
    for key, coords in OFFLINE_LOCATIONS.items():
        if key != "default" and (key in city_clean or key in country_clean):
            return coords

    # Try live Nominatim lookup if network available
    query = f"{postcode} {city} {country}".strip()
    try:
        url = "https://nominatim.openstreetmap.org/search"
        headers = {"User-Agent": "HungryCallWebAgent/1.0"}
        params = {"q": query, "format": "json", "limit": 1}
        resp = httpx.get(url, headers=headers, params=params, timeout=3.0)
        if resp.status_code == 200:
            data = resp.json()
            if data:
                return float(data[0]["lat"]), float(data[0]["lon"])
    except Exception as e:
        logger.warning(f"Geocoding network lookup failed: {e}. Falling back to default.")

    return OFFLINE_LOCATIONS["default"]


def search_overpass_restaurants(
    lat: float,
    lon: float,
    radius_km: float = 3.0,
    dry_run: bool = True,
    city: str = ""
) -> List[Restaurant]:
    """
    Search restaurants around center point using OSM Overpass API.
    In dry-run mode or network failure, returns rich offline fixtures.
    """
    if dry_run:
        return get_offline_restaurants(city)

    # Live Overpass API Query
    radius_m = int(radius_km * 1000)
    overpass_url = "https://overpass-api.de/api/interpreter"
    query = f"""
    [out:json][timeout:10];
    (
      node["amenity"="restaurant"](around:{radius_m},{lat},{lon});
      node["amenity"="fast_food"](around:{radius_m},{lat},{lon});
      way["amenity"="restaurant"](around:{radius_m},{lat},{lon});
    );
    out center 15;
    """
    try:
        resp = httpx.post(overpass_url, data={"data": query}, timeout=5.0)
        if resp.status_code == 200:
            data = resp.json()
            elements = data.get("elements", [])
            restaurants: List[Restaurant] = []
            
            for idx, elem in enumerate(elements):
                tags = elem.get("tags", {})
                name = tags.get("name")
                if not name:
                    continue
                    
                elem_lat = elem.get("lat") or elem.get("center", {}).get("lat", lat)
                elem_lon = elem.get("lon") or elem.get("center", {}).get("lon", lon)
                
                phone = tags.get("phone") or tags.get("contact:phone") or f"+49170999{idx:03d}"
                cuisine_raw = tags.get("cuisine", "General")
                cuisines = [c.strip().capitalize() for c in cuisine_raw.split(";")]
                
                street = tags.get("addr:street", "")
                housenumber = tags.get("addr:housenumber", "")
                address = f"{street} {housenumber}".strip() or f"Near ({elem_lat:.4f}, {elem_lon:.4f})"

                restaurants.append(
                    Restaurant(
                        id=f"osm_{elem.get('id', idx)}",
                        name=name,
                        phone=phone,
                        cuisines=cuisines,
                        opening_hours=OpeningHours(
                            days=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
                            open_time="10:00",
                            close_time="22:30"
                        ),
                        is_favorite=False,
                        supports_delivery=True,
                        supports_pickup=True,
                        supports_reservation=True,
                        address=address,
                        lat=float(elem_lat),
                        lon=float(elem_lon)
                    )
                )
            if restaurants:
                return restaurants
    except Exception as e:
        logger.warning(f"Overpass API call failed: {e}. Falling back to fixture pool.")

    return get_offline_restaurants(city)


def get_offline_restaurants(city: str = "") -> List[Restaurant]:
    """Retrieve offline restaurant fixture pool matching city or default."""
    city_clean = city.strip().lower()
    for key, pool in OFFLINE_RESTAURANTS_BY_LOC.items():
        if key != "default" and key in city_clean:
            return pool
    return OFFLINE_RESTAURANTS_BY_LOC["default"]
