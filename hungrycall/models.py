"""Data models for HungryCall agent cascade."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class Mode(str, Enum):
    DELIVERY = "delivery"
    RESERVATION = "reservation"
    PICKUP = "pickup"


class Branch(str, Enum):
    """The two things a user can start from on the landing page.

    A branch is not a mode: FOOD covers both DELIVERY and PICKUP, because
    the switch between them happens inside the branch, not before it.
    """
    FOOD = "food"
    TABLE = "table"

    @property
    def modes(self) -> List[Mode]:
        if self is Branch.FOOD:
            return [Mode.DELIVERY, Mode.PICKUP]
        return [Mode.RESERVATION]


class Seating(str, Enum):
    """Where the guest wants to sit. ANY means the criterion does not apply."""
    ANY = "any"
    INDOOR = "indoor"
    OUTDOOR = "outdoor"


class CallStatus(str, Enum):
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    NO_ANSWER = "NO_ANSWER"
    DECLINED = "DECLINED"
    CANCELED = "CANCELED"
    VOICEMAIL = "VOICEMAIL"
    BUSY = "BUSY"
    EXPIRED = "EXPIRED"


@dataclass
class OpeningHours:
    days: List[str]  # e.g. ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    open_time: str   # "11:00"
    close_time: str  # "22:00"

    def is_open(self, day: str, time_str: str) -> bool:
        if day not in self.days:
            return False
        if self.close_time <= self.open_time:
            # Crosses midnight (22:00–04:00). A plain range check reports such
            # a place as closed at 23:00, which is exactly when it is open.
            return time_str >= self.open_time or time_str <= self.close_time
        return self.open_time <= time_str <= self.close_time


@dataclass
class Concession:
    """Something the user is willing to give — but not right away.

    From MUSTER.md: "auch privat, bis 30 Euro — aber biete das nicht zuerst an."
    A concession is a card the agent may play only after the plain attempt has
    failed. It is an *authorisation*, exactly like max_budget_eur is one: the
    agent may not invent it, and a result that used an unauthorised concession
    is rejected by the engine.
    """
    key: str        # machine key, e.g. "outdoor_ok" — must match tier_applied
    label: str      # sentence handed to the voice agent
    tier: int = 1   # 1 is played first, 2 only after 1 failed


@dataclass
class Restaurant:
    id: str
    name: str
    phone: str  # E.164 format, e.g. +441632960090
    cuisines: List[str]  # e.g. ["Burger", "American"]
    opening_hours: OpeningHours
    is_favorite: bool = False
    supports_delivery: bool = True
    supports_pickup: bool = True
    supports_reservation: bool = True
    address: str = ""
    email: Optional[str] = None
    lat: float = 52.5200
    lon: float = 13.4050
    has_outdoor_seating: bool = False
    max_party_size: int = 8
    distance_km: Optional[float] = None  # filled in by the search, not by hand


@dataclass
class UserRequest:
    mode: Mode
    customer_name: str
    food_prompt: str
    max_budget_eur: Optional[float] = None  # Mandatory for delivery and pickup
    delivery_address: Optional[str] = None  # Mandatory for delivery
    reservation_date: Optional[str] = None  # Mandatory for reservation (YYYY-MM-DD)
    reservation_time: Optional[str] = None  # HH:MM
    party_size: Optional[int] = None        # Number of guests
    seating: Seating = Seating.ANY          # indoor / outdoor wish for a table
    pickup_time: Optional[str] = None       # Preferred pickup time (HH:MM)
    max_distance_km: Optional[float] = None  # hard cut-off, matters for pickup
    day_of_week: str = "Fri"
    time_of_request: str = "19:00"
    favorite_restaurant_ids: List[str] = field(default_factory=list)
    concessions: List[Concession] = field(default_factory=list)

    def granted_concession_keys(self) -> List[str]:
        return [c.key for c in self.concessions]

    def effective_time(self) -> str:
        """The clock time this request is about — not the time it was typed."""
        if self.mode == Mode.RESERVATION and self.reservation_time:
            return self.reservation_time
        if self.mode == Mode.PICKUP and self.pickup_time:
            return self.pickup_time
        return self.time_of_request


@dataclass
class CallResult:
    call_id: str
    run_id: str
    status: CallStatus
    task_completed: bool
    completion_confidence: float
    structured_result: Dict[str, Any]
    transcript: List[Dict[str, Any]]
    post_summary: str
    rejection_reason: Optional[str] = None
    activity: List[str] = field(default_factory=list)
    raw_transcript_text: Optional[str] = None


@dataclass
class AttemptRecord:
    restaurant: Restaurant
    call_result: Optional[CallResult]
    passed_criteria: bool
    rejection_reason: Optional[str]
    timestamp: str
    concession_used: Optional[str] = None  # key of the concession the agent played


@dataclass
class CascadeSummary:
    success: bool
    mode: Mode
    user_request: UserRequest
    attempts: List[AttemptRecord]
    successful_restaurant: Optional[Restaurant] = None
    final_result: Optional[CallResult] = None
    message: str = ""
    concession_used: Optional[str] = None
