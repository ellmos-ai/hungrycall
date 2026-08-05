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
    CUSTOM = "custom"


class CallStatus(str, Enum):
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    NO_ANSWER = "NO_ANSWER"
    DECLINED = "DECLINED"
    CANCELED = "CANCELED"
    VOICEMAIL = "VOICEMAIL"
    BUSY = "BUSY"
    EXPIRED = "EXPIRED"


class ProductKind(str, Enum):
    """The two product kinds named by the approved order-chain blueprint."""

    FOOD = "essen"
    DRINK = "getraenk"


class CriterionKind(str, Enum):
    MAX_PRICE = "hoechstpreis"
    SPECIAL_REQUEST = "sonderwunsch"
    QUESTION = "rueckfrage"


class CriterionReaction(str, Enum):
    ACCEPT = "annehmen"
    NEXT_REPLACEMENT = "naechster_ersatz"
    REJECT = "ablehnen"


class NothingAvailableRule(str, Enum):
    SKIP_ITEM = "posten_weglassen"
    ABORT_ORDER = "bestellung_abbrechen"


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
class OrderCriterion:
    """One condition attached to one possible product cell.

    All criterion kinds use the same two reaction slots. For a price or a
    special request, ``on_yes`` means the limit/request was met and ``on_no``
    means it was not. For a question they map literally to yes and no.
    """

    kind: CriterionKind
    value: Any
    on_yes: CriterionReaction = CriterionReaction.ACCEPT
    on_no: CriterionReaction = CriterionReaction.NEXT_REPLACEMENT

    def to_dict(self) -> Dict[str, Any]:
        return {
            "art": self.kind.value,
            "wert": self.value,
            "reaktion_ja": self.on_yes.value,
            "reaktion_nein": self.on_no.value,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OrderCriterion":
        kind = CriterionKind(data.get("art"))
        value = data.get("wert")
        if kind is CriterionKind.MAX_PRICE:
            try:
                value = float(value)
            except (TypeError, ValueError) as exc:
                raise ValueError("hoechstpreis requires a numeric wert") from exc
            if value < 0:
                raise ValueError("hoechstpreis cannot be negative")
        elif not isinstance(value, str) or not value.strip():
            raise ValueError(f"{kind.value} requires non-empty text")
        return cls(
            kind=kind,
            value=value,
            on_yes=CriterionReaction(data.get("reaktion_ja", "annehmen")),
            on_no=CriterionReaction(data.get("reaktion_nein", "naechster_ersatz")),
        )


@dataclass
class OrderCell:
    quantity: int
    product: str
    kind: ProductKind = ProductKind.FOOD
    criteria: List[OrderCriterion] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "menge": self.quantity,
            "produkt": self.product,
            "art": self.kind.value,
            "kriterien": [criterion.to_dict() for criterion in self.criteria],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OrderCell":
        try:
            quantity = int(data.get("menge", 1))
        except (TypeError, ValueError) as exc:
            raise ValueError("menge must be an integer") from exc
        if quantity < 1:
            raise ValueError("menge must be at least 1")
        product = str(data.get("produkt") or "").strip()
        if not product:
            raise ValueError("produkt is required")
        return cls(
            quantity=quantity,
            product=product,
            kind=ProductKind(data.get("art", "essen")),
            criteria=[OrderCriterion.from_dict(item) for item in data.get("kriterien", [])],
        )


@dataclass
class OrderPosition:
    cells: List[OrderCell]
    tags: List[str] = field(default_factory=list)
    if_nothing_available: NothingAvailableRule = NothingAvailableRule.SKIP_ITEM

    def to_dict(self) -> Dict[str, Any]:
        return {
            "zellen": [cell.to_dict() for cell in self.cells],
            "tags": self.tags,
            "wenn_nichts_verfuegbar": self.if_nothing_available.value,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OrderPosition":
        cells = [OrderCell.from_dict(item) for item in data.get("zellen", [])]
        if not cells:
            raise ValueError("each posten requires at least one zelle")
        tags: List[str] = []
        for raw in data.get("tags", []):
            tag = str(raw).strip()
            if tag and tag not in tags:
                tags.append(tag)
        return cls(
            cells=cells,
            tags=tags,
            if_nothing_available=NothingAvailableRule(
                data.get("wenn_nichts_verfuegbar", "posten_weglassen")
            ),
        )


@dataclass
class OrderChain:
    """The single config shared by the UI, call goal and result evaluator."""

    positions: List[OrderPosition]

    def to_dict(self) -> Dict[str, Any]:
        return {"version": 1, "posten": [position.to_dict() for position in self.positions]}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OrderChain":
        if not isinstance(data, dict):
            raise ValueError("order chain must be an object")
        positions = [OrderPosition.from_dict(item) for item in data.get("posten", [])]
        if not positions:
            raise ValueError("an order requires at least one posten")
        return cls(positions=positions)

    def summary(self) -> str:
        return ", ".join(
            f"{position.cells[0].quantity}x {position.cells[0].product}"
            for position in self.positions
        )

    def all_tags(self) -> List[str]:
        seen: List[str] = []
        for position in self.positions:
            for tag in position.tags:
                if tag not in seen:
                    seen.append(tag)
        return seen


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
    order_chain: Optional[OrderChain] = None
    # ``customer_name`` remains the compatibility carrier used by existing
    # CLI/dry-run callers.  The web flow collects the two parts separately so
    # restaurants receive an unambiguous booking/order name.
    first_name: str = ""
    last_name: str = ""
    # Intentionally transient: web.py carries this through the form steps but
    # never writes it to HungryCall's database or result history.
    requester_callback_number: Optional[str] = None
    seating_custom: Optional[str] = None
    special_instructions: Optional[str] = None
    # Reservation fallbacks are explicit upper bounds. The minute fields add
    # precision to the selected whole-hour allowance (for example 1 h 30 m).
    earlier_hours: int = 0
    later_hours: int = 0
    earlier_minutes: int = 0
    later_minutes: int = 0
    max_booking_fee_eur: float = 0.0

    def granted_concession_keys(self) -> List[str]:
        return [c.key for c in self.concessions]

    def requester_name(self) -> str:
        """Return the split web name, falling back to the legacy carrier."""
        split_name = " ".join(
            part.strip() for part in (self.first_name, self.last_name) if part.strip()
        )
        return split_name or self.customer_name

    def earlier_tolerance_minutes(self) -> int:
        """Maximum explicitly granted earlier shift."""
        return self.earlier_hours * 60 + self.earlier_minutes

    def later_tolerance_minutes(self) -> int:
        """Maximum explicitly granted later shift."""
        return self.later_hours * 60 + self.later_minutes

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
