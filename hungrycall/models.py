"""Data models for HungryCall agent cascade."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class Mode(str, Enum):
    DELIVERY = "delivery"
    RESERVATION = "reservation"
    PICKUP = "pickup"


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
        return self.open_time <= time_str <= self.close_time


@dataclass
class Restaurant:
    id: str
    name: str
    phone: str  # E.164 format, e.g. +491701234567
    cuisines: List[str]  # e.g. ["Burger", "American"]
    opening_hours: OpeningHours
    is_favorite: bool = False
    supports_delivery: bool = True
    supports_pickup: bool = True
    supports_reservation: bool = True
    address: str = ""
    email: Optional[str] = None


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
    pickup_time: Optional[str] = None       # Preferred pickup time (HH:MM)
    day_of_week: str = "Fri"
    time_of_request: str = "19:00"
    favorite_restaurant_ids: List[str] = field(default_factory=list)


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


@dataclass
class AttemptRecord:
    restaurant: Restaurant
    call_result: Optional[CallResult]
    passed_criteria: bool
    rejection_reason: Optional[str]
    timestamp: str


@dataclass
class CascadeSummary:
    success: bool
    mode: Mode
    user_request: UserRequest
    attempts: List[AttemptRecord]
    successful_restaurant: Optional[Restaurant] = None
    final_result: Optional[CallResult] = None
    message: str = ""
