"""Location geocoding and OpenStreetMap Overpass restaurant search module."""

import copy
import logging
import threading
import time

import httpx

from hungrycall.fixtures import SAMPLE_RESTAURANTS
from hungrycall.models import OpeningHours, Restaurant
from hungrycall.phone_utils import normalize_e164, validate_e164

logger = logging.getLogger(__name__)

# Both public OpenStreetMap services require callers to identify their
# application.  Overpass rejects the generic httpx default user agent with
# HTTP 406, so keep one honest identifier on every request.
OSM_USER_AGENT = "HungryCall/0.1.0 (+https://github.com/ellmos-ai/hungrycall)"

# Both services occasionally answer a timeout, a dropped connection, or a
# rate-limit/server-busy status on an otherwise fine query -- and recover
# within a second or two. One retry catches that without turning a real
# outage into a long wait: a query that fails twice in a row fails for real,
# and a malformed query or a genuinely unresolvable address is never retried
# (it would just repeat the same wrong answer).
_RETRY_ATTEMPTS = 2
_RETRY_BACKOFF_SECONDS = 0.3
_RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


def _request_with_retry(request_fn, url, **kwargs):
    """Call ``request_fn(url, **kwargs)``, retrying once on a failure mode
    the service itself recovers from."""
    for attempt in range(1, _RETRY_ATTEMPTS + 1):
        try:
            response = request_fn(url, **kwargs)
        except (httpx.TimeoutException, httpx.RequestError):
            if attempt == _RETRY_ATTEMPTS:
                raise
            time.sleep(_RETRY_BACKOFF_SECONDS)
            continue
        if response.status_code in _RETRYABLE_STATUS_CODES and attempt < _RETRY_ATTEMPTS:
            time.sleep(_RETRY_BACKOFF_SECONDS)
            continue
        return response
    raise AssertionError("unreachable: the loop above always returns or raises")


# A short-lived cache of the last geocoding and restaurant search per query.
# The web UI runs the identical search twice for one order in the normal
# case -- once to show candidates (/api/search), again immediately before
# actually dialing (/api/start-cascade), which re-queries OSM with the same
# postcode/city/radius carried forward in the form. Reusing that answer for
# a couple of minutes removes one of the two chances for a transient OSM
# hiccup to surface to the user, and halves the load this free public
# service sees per order. This is not the session state the /api/search
# route deliberately avoids (see its comment on form_state): the cache key
# is the search parameters, not who is asking.
_SEARCH_CACHE_TTL_SECONDS = 120.0
_SEARCH_CACHE_MAX_ENTRIES = 32

_cache_lock = threading.Lock()
_geocode_cache: dict[tuple[str, str, str], tuple[float, tuple[float, float]]] = {}
_overpass_cache: dict[tuple[float, float, float], tuple[float, list[Restaurant]]] = {}


def clear_search_cache() -> None:
    """Drop every cached geocode/search result. Mainly for test isolation."""
    with _cache_lock:
        _geocode_cache.clear()
        _overpass_cache.clear()


def _cache_get(cache: dict, key):
    with _cache_lock:
        entry = cache.get(key)
        if entry is None:
            return None
        cached_at, value = entry
        if time.monotonic() - cached_at > _SEARCH_CACHE_TTL_SECONDS:
            del cache[key]
            return None
        return value


def _cache_put(cache: dict, key, value) -> None:
    with _cache_lock:
        if len(cache) >= _SEARCH_CACHE_MAX_ENTRIES and key not in cache:
            oldest_key = min(cache, key=lambda k: cache[k][0], default=None)
            if oldest_key is not None:
                del cache[oldest_key]
        cache[key] = (time.monotonic(), value)


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
OFFLINE_LOCATIONS: dict[str, tuple[float, float]] = {
    "singapore": (1.3521, 103.8198),
    "london": (51.5074, -0.1278),
    "new york": (40.7128, -74.0060),
    "berlin": (52.5200, 13.4050),
    "munich": (48.1351, 11.5820),
    "dorfstadt": (52.5200, 13.4050),
    "default": (52.5200, 13.4050)
}

# Rich offline fixtures per location for offline demo presentation
OFFLINE_RESTAURANTS_BY_LOC: dict[str, list[Restaurant]] = {
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
    # The German village pool lives in fixtures.SAMPLE_RESTAURANTS. Keeping a
    # second copy here is how the two lists drifted apart in the first place.
    "default": SAMPLE_RESTAURANTS,
}


def geocode_location(
    postcode: str,
    city: str,
    country: str,
    test_mode: bool = False,
) -> tuple[float, float]:
    """Resolve a location through Nominatim, or fixtures in explicit test mode."""
    city_clean = city.strip().lower()
    country_clean = country.strip().lower()

    if test_mode:
        for key, coords in OFFLINE_LOCATIONS.items():
            if key != "default" and (key in city_clean or key in country_clean):
                return coords
        return OFFLINE_LOCATIONS["default"]

    cache_key = (postcode.strip(), city_clean, country_clean)
    cached = _cache_get(_geocode_cache, cache_key)
    if cached is not None:
        return cached

    query = f"{postcode} {city} {country}".strip()
    try:
        url = "https://nominatim.openstreetmap.org/search"
        headers = {"User-Agent": OSM_USER_AGENT, "Accept": "application/json"}
        params = {"q": query, "format": "json", "limit": 1}
        resp = _request_with_retry(httpx.get, url, headers=headers, params=params, timeout=3.0)
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
        coords = (float(data[0]["lat"]), float(data[0]["lon"]))
    except (KeyError, TypeError, ValueError, IndexError) as exc:
        logger.warning("Nominatim response did not contain usable coordinates: %s", exc)
        raise SearchServiceUnavailable("Nominatim returned unusable coordinates") from exc

    _cache_put(_geocode_cache, cache_key, coords)
    return coords


def search_overpass_restaurants(
    lat: float,
    lon: float,
    radius_km: float = 3.0,
    test_mode: bool = False,
    city: str = ""
) -> list[Restaurant]:
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

    cache_key = (round(lat, 6), round(lon, 6), radius_km)
    cached = _cache_get(_overpass_cache, cache_key)
    if cached is not None:
        return copy.deepcopy(cached)

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
        resp = _request_with_retry(
            httpx.post,
            overpass_url,
            headers={"User-Agent": OSM_USER_AGENT, "Accept": "application/json"},
            data={"data": query},
            timeout=5.0,
        )
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
    restaurants: list[Restaurant] = []

    for idx, elem in enumerate(elements):
        if not isinstance(elem, dict):
            continue
        tags = elem.get("tags", {})
        name = tags.get("name")
        phone = tags.get("phone") or tags.get("contact:phone")
        if not name or not phone:
            continue
        normalized_phone = normalize_e164(str(phone))
        if not validate_e164(normalized_phone):
            logger.info("Skipping OSM restaurant %s with unusable phone metadata", elem.get("id", idx))
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
                phone=normalized_phone,
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
    annotated = annotate_distances(restaurants, lat, lon)
    _cache_put(_overpass_cache, cache_key, annotated)
    return copy.deepcopy(annotated)


def get_offline_restaurants(city: str = "") -> list[Restaurant]:
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
