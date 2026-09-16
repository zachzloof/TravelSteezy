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
    # Optional; checked against settings.access_code. A match auto-approves the
    # account even when ADMIN_AUTO_APPROVE is off. Never required at the schema
    # level - registration without one just falls back to the normal pending flow.
    access_code: Optional[str] = None

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
    # Every passport held, primary first. `nationality` mirrors passports[0], so
    # anything written against the single-passport shape keeps working.
    passports: list[str] = []
    social_style: Optional[str] = None
    budget_band: Optional[str] = None
    travel_style: Optional[str] = None
    climate_preference: Optional[str] = None
    current_location: Optional[str] = None
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
    budget_band: Optional[
        Literal["shoestring", "budget", "mid", "comfortable", "luxury"]
    ] = None
    travel_style: Optional[
        Literal["very_slow", "slow", "balanced", "fast", "very_fast"]
    ] = None
    climate_preference: Optional[
        Literal["cold", "cool", "temperate", "warm", "hot"]
    ] = None
    social_style: Optional[Literal["solo", "couple", "group"]] = None
    # Replaces the whole list. Sent by the About You panel, which edits passports
    # as a set rather than one at a time.
    passports: Optional[list[str]] = None
    # Fields to blank. Named explicitly rather than inferred from an empty
    # string, so a partial form can still never wipe a field it did not show.
    clear: list[str] = []
    current_location: Optional[str] = None
    # No "interests" field here on purpose: interests are structured rows
    # (backend.memory.travel), not a trip_profile column a generic PATCH can
    # write. Writing a raw string here would blow away the KEY/other tiering
    # that travel.set_interests maintains - see POST /travel/me/interests and
    # POST /travel/me/interests/key for the real write paths.


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
    # True when this is somewhere they have already been - a deliberate second
    # visit, not a bookkeeping error.
    revisit: bool = False


class OnboardingState(BaseModel):
    status: str = "not_started"
    step: str = "history"
    turns: int = 0
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    missing: list[str] = []
    answered: list[str] = []


class TravelSnapshotResponse(BaseModel):
    travel_history: list[TravelEntry] = []
    wishlist: list[WishlistEntry] = []
    # Every interest, key ones first - kept for callers that only want one list.
    interests: list[str] = []
    # The same list, split: 3-5 declared top priorities, and everything else.
    # Recommendations and country comparisons weight key_interests heavily.
    key_interests: list[str] = []
    other_interests: list[str] = []
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


class OnboardingQuestion(BaseModel):
    """One question on the welcome page. Served from the backend so the UI, the
    extractor prompt and the eval suite cannot drift apart."""

    id: str
    title: str
    prompt: str
    hint: str = ""
    placeholder: str = ""
    captures: list[str] = []
    optional: bool = False


class OnboardingStartResponse(BaseModel):
    questions: list[OnboardingQuestion]
    state: OnboardingState
    next_step: Optional[str] = None
    profile: TripProfile
    travel_history: list[TravelEntry] = []
    wishlist: list[WishlistEntry] = []
    interests: list[str] = []
    key_interests: list[str] = []
    other_interests: list[str] = []


class OnboardingAnswerRequest(BaseModel):
    step: str = Field(min_length=1, max_length=40)
    text: str = Field(default="", max_length=4000)
    # A question the traveller chose not to answer is marked done, not left to
    # reappear. Skipping is a legitimate answer, and pretending otherwise is how
    # onboarding flows become walls.
    skipped: bool = False


class OnboardingAnswerResponse(BaseModel):
    step: str
    next_step: Optional[str] = None
    captured: list[MemoryWriteEntry] = []
    note: Optional[str] = None
    state: OnboardingState
    profile: TripProfile
    travel_history: list[TravelEntry] = []
    wishlist: list[WishlistEntry] = []
    interests: list[str] = []
    key_interests: list[str] = []
    other_interests: list[str] = []


class RatingRequest(BaseModel):
    location: str = Field(min_length=1, max_length=120)
    # None clears the rating, for a star tapped by mistake.
    rating: Optional[int] = Field(default=None, ge=1, le=5)


class ReviewRequest(BaseModel):
    location: str = Field(min_length=1, max_length=120)
    rating: Optional[int] = Field(default=None, ge=1, le=5)
    notes: Optional[str] = Field(default=None, max_length=2000)
    # False keeps the review private to this account rather than feeding the
    # shared RAG experience namespace.
    share: bool = True


class CatchupStatus(BaseModel):
    """"Here's where we left off - what's changed?" - whether it is due, and
    the short human summary to show alongside it."""

    due: bool = False
    last_active_date: Optional[str] = None
    days_since: Optional[int] = None
    summary: str = ""


class CatchupUpdateRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


# --------------------------------------------------------------------------- #
# bug reports
# --------------------------------------------------------------------------- #
class BugReportCreate(BaseModel):
    description: str = Field(min_length=1, max_length=4000)
    # Where in the app they were, and what browser they were using - both
    # supplied by the frontend since the backend has no way to know either.
    page: Optional[str] = Field(default=None, max_length=200)
    user_agent: Optional[str] = Field(default=None, max_length=500)
    # The most recent /chat trace id the frontend has seen, if any. Lets the
    # report link straight to the Langfuse trace for that turn.
    trace_id: Optional[str] = Field(default=None, max_length=200)


class BugReportCreated(BaseModel):
    id: int
    created_at: str


class BugReportAdmin(BaseModel):
    id: int
    username: str
    description: str
    page: Optional[str] = None
    status: str
    created_at: str
    trace_url: Optional[str] = None
    # Fully-formatted, ready to paste straight into Claude Code.
    trace_text: str


# --------------------------------------------------------------------------- #
# memory debug page
#
# Deliberately loose (dict[str, Any] rows rather than strict per-field models):
# this page's whole purpose is showing precisely what is in the database,
# including columns and shapes the ordinary UI never surfaces. Pinning every
# field to a schema would fight that rather than serve it.
# --------------------------------------------------------------------------- #
class MemoryDebugResponse(BaseModel):
    # The EXACT text injected into every agent prompt this turn - not a summary
    # of it. If something is wrong with what the assistant "knows", this is the
    # first place to look.
    memory_block: str
    travel_block: str

    profile_row: dict[str, Any]
    passports: list[str]
    travel_history: list[dict[str, Any]]
    wishlist: list[dict[str, Any]]
    interests: list[dict[str, Any]]
    onboarding_state: dict[str, Any]
    recommendation_feedback: list[dict[str, Any]]
    memory_writes: list[dict[str, Any]]

    # Stored, but NOT fed into any agent prompt - this app does not replay chat
    # history into the model. Shown so that fact is verifiable rather than
    # merely claimed.
    conversation_turns: list[dict[str, Any]]

    # What this account has actually published to the shared RAG experience
    # store, fetched by id rather than trusted from what was submitted - a
    # review that was too short to index, or kept private, will not appear.
    published_experience_documents: list[dict[str, Any]]


# Resolve the forward references used by ChatResponse above.
ChatResponse.model_rebuild()
