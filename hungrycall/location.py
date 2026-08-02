"""Location geocoding and OpenStreetMap Overpass restaurant search module."""

import copy
import logging
from typing import Dict, List, Tuple, Optional
import httpx
from hungrycall.models import Restaurant, OpeningHours
from hungrycall.fixtures import SAMPLE_RESTAURANTS

logger = logging.getLogger(__name__)


class RestaurantSearchError(RuntimeError):
    """Base class for an honest, user-visible restaurant search failure."""

    code = "search_failed"


class SearchServiceUnavailable(RestaurantSearchError):
    """Nominatim or Overpass could not be reached or returned an invalid response."""

    code = "service_unavailable"


class AddressNotFound(RestaurantSearchError):
    """Nominatim completed the request but could not resolve the location."""

    code = "address_not_found"


class NoRestaurantsFound(RestaurantSearchError):
    """Overpass completed the request but returned no callable restaurants."""

    code = "no_restaurants"


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
            phone="+6562202138",
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
            phone="+6566349969",
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
            phone="+6567331188",
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
            phone="+442074209320",
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
            phone="+442077348895",
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
    # The German village pool lives in fixtures.SAMPLE_RESTAURANTS. Keeping a
    # second copy here is how the two lists drifted apart in the first place.
    "default": SAMPLE_RESTAURANTS,
}


def geocode_location(
    postcode: str,
    city: str,
    country: str,
    test_mode: bool = False,
) -> Tuple[float, float]:
    """Resolve a location through Nominatim, or fixtures in explicit test mode."""
    city_clean = city.strip().lower()
    country_clean = country.strip().lower()

    if test_mode:
        for key, coords in OFFLINE_LOCATIONS.items():
            if key != "default" and (key in city_clean or key in country_clean):
                return coords
        return OFFLINE_LOCATIONS["default"]

    query = f"{postcode} {city} {country}".strip()
    try:
        url = "https://nominatim.openstreetmap.org/search"
        headers = {"User-Agent": "HungryCallWebAgent/1.0"}
        params = {"q": query, "format": "json", "limit": 1}
        resp = httpx.get(url, headers=headers, params=params, timeout=3.0)
    except (httpx.TimeoutException, httpx.RequestError) as exc:
        logger.warning("Nominatim request failed: %s", exc)
        raise SearchServiceUnavailable("Nominatim request failed") from exc

    if resp.status_code != 200:
        logger.warning("Nominatim returned HTTP %s", resp.status_code)
        raise SearchServiceUnavailable(f"Nominatim returned HTTP {resp.status_code}")

    try:
        data = resp.json()
    except (TypeError, ValueError) as exc:
        logger.warning("Nominatim returned invalid JSON: %s", exc)
        raise SearchServiceUnavailable("Nominatim returned invalid JSON") from exc

    if not isinstance(data, list) or not data:
        raise AddressNotFound(f"Nominatim could not resolve {query!r}")

    try:
        return float(data[0]["lat"]), float(data[0]["lon"])
    except (KeyError, TypeError, ValueError, IndexError) as exc:
        logger.warning("Nominatim response did not contain usable coordinates: %s", exc)
        raise SearchServiceUnavailable("Nominatim returned unusable coordinates") from exc


def search_overpass_restaurants(
    lat: float,
    lon: float,
    radius_km: float = 3.0,
    test_mode: bool = False,
    city: str = ""
) -> List[Restaurant]:
    """
    Search restaurants around center point using OSM Overpass API.
    Only explicit test mode returns offline fixtures. Live lookup failures raise
    a typed error and never substitute example restaurants.

    Every candidate comes back with distance_km filled in, because pickup
    ranking and the distance cut-off are meaningless without it.
    """
    from hungrycall.ranking import annotate_distances  # local: avoids an import cycle

    if test_mode:
        return annotate_distances(get_offline_restaurants(city), lat, lon)

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
    except (httpx.TimeoutException, httpx.RequestError) as exc:
        logger.warning("Overpass request failed: %s", exc)
        raise SearchServiceUnavailable("Overpass request failed") from exc

    if resp.status_code != 200:
        logger.warning("Overpass returned HTTP %s", resp.status_code)
        raise SearchServiceUnavailable(f"Overpass returned HTTP {resp.status_code}")

    try:
        data = resp.json()
    except (TypeError, ValueError) as exc:
        logger.warning("Overpass returned invalid JSON: %s", exc)
        raise SearchServiceUnavailable("Overpass returned invalid JSON") from exc

    if not isinstance(data, dict) or not isinstance(data.get("elements"), list):
        logger.warning("Overpass response did not contain an elements list")
        raise SearchServiceUnavailable("Overpass returned an invalid response shape")

    elements = data["elements"]
    restaurants: List[Restaurant] = []
            
    for idx, elem in enumerate(elements):
        if not isinstance(elem, dict):
            continue
        tags = elem.get("tags", {})
        name = tags.get("name")
        phone = tags.get("phone") or tags.get("contact:phone")
        if not name or not phone:
            continue
                    
        elem_lat = elem.get("lat") or elem.get("center", {}).get("lat", lat)
        elem_lon = elem.get("lon") or elem.get("center", {}).get("lon", lon)
                
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

    if not restaurants:
        raise NoRestaurantsFound(
            f"Overpass returned no callable restaurants within {radius_km:g} km"
        )
    return annotate_distances(restaurants, lat, lon)


def get_offline_restaurants(city: str = "") -> List[Restaurant]:
    """Retrieve the offline candidate pool for a city, or the default village.

    Returns deep copies. The search annotates each candidate with its distance
    to the caller, and handing out the shared module-level objects would leak
    one visitor's distances into the next one's results.
    """
    city_clean = city.strip().lower()
    for key, pool in OFFLINE_RESTAURANTS_BY_LOC.items():
        if key != "default" and key in city_clean:
            return copy.deepcopy(pool)
    return copy.deepcopy(OFFLINE_RESTAURANTS_BY_LOC["default"])
