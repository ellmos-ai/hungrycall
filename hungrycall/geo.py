"""Distance and calendar helpers.

Distance is not decoration here. It changes the decision:

* Delivery — the restaurant drives. Distance is the restaurant's problem, so it
  barely moves the ranking. What the user pays for it is already inside the
  doorstep total.
* Pickup — the user drives. Every kilometre is the user's time and fuel, so
  distance becomes a first-class ranking criterion and can be a hard cut-off.
* Table — the user drives too, but a booked table is worth a detour, so the
  weight sits between the two.
"""

from datetime import date, datetime
from math import asin, cos, radians, sin, sqrt
from typing import Optional

EARTH_RADIUS_KM = 6371.0

WEEKDAY_KEYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in kilometres between two WGS84 points."""
    d_lat = radians(lat2 - lat1)
    d_lon = radians(lon2 - lon1)
    a = (
        sin(d_lat / 2) ** 2
        + cos(radians(lat1)) * cos(radians(lat2)) * sin(d_lon / 2) ** 2
    )
    return 2 * EARTH_RADIUS_KM * asin(sqrt(min(1.0, a)))


def weekday_key(date_str: Optional[str], fallback: str = "Fri") -> str:
    """Map an ISO date (YYYY-MM-DD) to the three-letter key used by OpeningHours.

    A reservation for next Tuesday must be checked against Tuesday's opening
    hours, not against whatever day the form happened to default to.
    """
    if not date_str:
        return fallback
    try:
        parsed = datetime.strptime(date_str.strip(), "%Y-%m-%d").date()
    except (ValueError, AttributeError):
        return fallback
    return WEEKDAY_KEYS[parsed.weekday()]


def today_weekday_key() -> str:
    return WEEKDAY_KEYS[date.today().weekday()]
