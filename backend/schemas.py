"""Request/response models for the API."""
from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, field_validator


# --------------------------------------------------------------------------- #
# auth
# --------------------------------------------------------------------------- #
class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=40)
    password: str = Field(min_length=8, max_length=72)

    @field_validator("username")
    @classmethod
    def clean_username(cls, v: str) -> str:
        v = v.strip()
        if not v.replace("_", "").replace("-", "").replace(".", "").isalnum():
            raise ValueError("Username may contain letters, digits, and . _ - only.")
        return v


class LoginRequest(BaseModel):
    username: str
    password: str


class AdminLoginRequest(BaseModel):
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: Optional[str] = None
    status: Optional[str] = None


class RegisterResponse(BaseModel):
    username: str
    status: str
    message: str
    # Populated only when ADMIN_AUTO_APPROVE is on, so the UI can log the user
    # straight in instead of showing an "awaiting approval" screen.
    access_token: Optional[str] = None


# --------------------------------------------------------------------------- #
# admin
# --------------------------------------------------------------------------- #
class PendingUser(BaseModel):
    id: int
    username: str
    status: str
    created_at: Optional[str] = None
    last_seen_at: Optional[str] = None


class AdminActionResponse(BaseModel):
    id: int
    username: str
    status: str


# --------------------------------------------------------------------------- #
# profile / memory
# --------------------------------------------------------------------------- #
class TripProfile(BaseModel):
    nationality: Optional[str] = None
    budget_band: Optional[str] = None
    travel_style: Optional[str] = None
    climate_preference: Optional[str] = None
    current_location: Optional[str] = None
    trip_start_date: Optional[str] = None
    trip_end_date: Optional[str] = None
    visa_deadline_date: Optional[str] = None
    visa_deadline_note: Optional[str] = None
    interests: Optional[str] = None
    updated_at: Optional[str] = None


class VisitedEntry(BaseModel):
    country: str
    arrival_date: Optional[str] = None
    departure_date: Optional[str] = None
    notes: Optional[str] = None
    logged_at: Optional[str] = None


class MemoryWriteEntry(BaseModel):
    operation: str
    payload: dict[str, Any]
    source: str
    created_at: Optional[str] = None


class ProfileResponse(BaseModel):
    username: str
    profile: TripProfile
    visited_history: list[VisitedEntry] = []
    recent_writes: list[MemoryWriteEntry] = []


class ProfilePatch(BaseModel):
    """Every field optional: a PATCH only touches what the user actually changed."""

    nationality: Optional[str] = None
    budget_band: Optional[Literal["shoestring", "mid", "comfortable"]] = None
    travel_style: Optional[Literal["slow", "balanced", "fast"]] = None
    climate_preference: Optional[Literal["cool", "temperate", "hot", "no_preference"]] = None
    current_location: Optional[str] = None
    trip_start_date: Optional[str] = None
    trip_end_date: Optional[str] = None
    visa_deadline_date: Optional[str] = None
    visa_deadline_note: Optional[str] = None
    interests: Optional[str] = None


class DepartureRequest(BaseModel):
    country: str
    departure_date: Optional[str] = None
    arrival_date: Optional[str] = None
    notes: Optional[str] = None


# --------------------------------------------------------------------------- #
# chat
# --------------------------------------------------------------------------- #
class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


class DestinationVerdict(BaseModel):
    """One card in the structured comparison the frontend renders."""

    destination: str
    rank: Optional[int] = None
    verdict: Optional[str] = None
    rationale: Optional[str] = None
    pros: list[str] = []
    cons: list[str] = []
    season_flag: Optional[str] = None
    visa_flag: Optional[str] = None
    est_cost_note: Optional[str] = None
    # Concrete, RAG-grounded specifics for this destination, plus the passage ids
    # they came from. Added after the eval run showed the synthesis step was
    # discarding everything the Recommendations specialist retrieved.
    backpacker_notes: list[str] = []
    source_ids: list[str] = []


class AgentTrace(BaseModel):
    name: str
    status: str
    summary: Optional[str] = None
    duration_ms: Optional[int] = None


class ChatResponse(BaseModel):
    reply: str
    comparison: list[DestinationVerdict] = []
    agents_fired: list[AgentTrace] = []
    memory_writes: list[MemoryWriteEntry] = []
    retrieved_sources: list[dict[str, Any]] = []
    trace_id: Optional[str] = None
    profile: Optional[TripProfile] = None
    visited_history: list[VisitedEntry] = []
    # structured travel state, so the UI reflects a tracked visit immediately
    intent: Optional[str] = None
    travel_history: list["TravelEntry"] = []
    wishlist: list["WishlistEntry"] = []
    review_prompt: Optional[dict[str, Any]] = None
    onboarding: Optional["OnboardingState"] = None


# --------------------------------------------------------------------------- #
# structured travel memory (onboarding, tracking, reviews)
# --------------------------------------------------------------------------- #
class TravelEntry(BaseModel):
    id: Optional[int] = None
    location: str
    location_type: str = "city"
    country: Optional[str] = None
    order_index: int = 0
    arrival_date: Optional[str] = None
    departure_date: Optional[str] = None
    source: str = "manual"
    notes: Optional[str] = None
    rating: Optional[int] = None
    review_notes: Optional[str] = None
    reviewed_at: Optional[str] = None
    review_prompted_at: Optional[str] = None
    last_mentioned_at: Optional[str] = None


class WishlistEntry(BaseModel):
    id: Optional[int] = None
    location: str
    location_type: str = "city"
    country: Optional[str] = None
    priority: int = 2
    status: str = "open"
    source: str = "manual"
    note: Optional[str] = None
    added_at: Optional[str] = None
    resolved_at: Optional[str] = None


class OnboardingState(BaseModel):
    status: str = "not_started"
    step: str = "history"
    turns: int = 0
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    missing: list[str] = []


class TravelSnapshotResponse(BaseModel):
    travel_history: list[TravelEntry] = []
    wishlist: list[WishlistEntry] = []
    interests: list[str] = []
    pending_reviews: list[str] = []
    onboarding: OnboardingState = OnboardingState()


class VisitRequest(BaseModel):
    location: str = Field(min_length=1, max_length=120)
    location_type: Literal["country", "city", "town", "region"] = "city"
    country: Optional[str] = None
    arrival_date: Optional[str] = None
    departure_date: Optional[str] = None
    notes: Optional[str] = None


class WishlistRequest(BaseModel):
    location: str = Field(min_length=1, max_length=120)
    location_type: Literal["country", "city", "town", "region"] = "city"
    country: Optional[str] = None
    priority: int = Field(default=2, ge=1, le=3)
    note: Optional[str] = None


class ReviewRequest(BaseModel):
    location: str = Field(min_length=1, max_length=120)
    rating: Optional[int] = Field(default=None, ge=1, le=5)
    notes: Optional[str] = Field(default=None, max_length=2000)
    # False keeps the review private to this account rather than feeding the
    # shared RAG experience namespace.
    share: bool = True


# Resolve the forward references used by ChatResponse above.
ChatResponse.model_rebuild()
