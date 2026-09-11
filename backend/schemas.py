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
