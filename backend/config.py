"""Central configuration. Everything comes from environment variables so that
nothing secret is ever committed to the repo (this repo is public for the course)."""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

# Load .env for local development. On Railway the real env vars win.
load_dotenv()

REPO_ROOT = Path(__file__).resolve().parent.parent


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class Settings:
    """Runtime settings.

    Read once at import. Attributes are plain values so tests can monkeypatch them.
    """

    def __init__(self) -> None:
        # --- storage -------------------------------------------------------
        # DATA_DIR is the Railway volume mount point. Locally it falls back to
        # ./data inside the repo (git-ignored).
        self.data_dir: Path = Path(os.getenv("DATA_DIR", str(REPO_ROOT / "data")))
        self.db_path: Path = Path(
            os.getenv("DB_PATH", str(self.data_dir / "onward.sqlite3"))
        )

        # --- auth ----------------------------------------------------------
        self.jwt_secret: str = os.getenv("JWT_SECRET", "dev-only-insecure-secret")
        self.jwt_algorithm: str = "HS256"
        self.jwt_ttl_hours: int = int(os.getenv("JWT_TTL_HOURS", "720"))  # 30 days
        self.admin_password: str | None = os.getenv("ADMIN_PASSWORD")
        # Demo safety: when true, new registrations are approved immediately so a
        # cold marker in incognito is never blocked waiting on a human.
        self.admin_auto_approve: bool = _as_bool(os.getenv("ADMIN_AUTO_APPROVE"), False)
        # Optional shared secret. When set, a registration submitted with a matching
        # access code is approved instantly, same as ADMIN_AUTO_APPROVE but scoped to
        # people who have the code rather than everyone. Leave unset to gate purely
        # on admin approval.
        self.access_code: str | None = os.getenv("ACCESS_CODE") or None

        # --- llm -----------------------------------------------------------
        self.openai_api_key: str | None = os.getenv("OPENAI_API_KEY")
        # The shared default for every agent except the two overridden below:
        # turn_parser, concierge, local_guide, discovery_agent, the onboarding
        # extractor, and live_lookup's synthesis/verify/classify_season calls.
        # All of these are either structured extraction (schema-validated by
        # ADK) or narrow, already-grounded completions - well within a small
        # model's reliability, and called often enough per turn that
        # cost/latency actually matters.
        self.llm_model: str = os.getenv("LLM_MODEL", "gpt-4o-mini")
        # decision_weigher is the one agent that earned a stronger model first:
        # it is the single most complex reasoning step in the graph (synthesise
        # three specialist reports, hold five hard rules simultaneously,
        # produce internally-consistent verdicts, emit valid JSON) and is
        # called exactly once per turn, so a pricier model here barely moves
        # per-turn cost. It was also the direct source of the reliability bugs
        # traced in notes/03-rag-and-retrieval.md's later follow-ups -
        # manufacturing a verdict spread across ranked candidates, needing
        # multiple attempts because it answered in prose instead of JSON.
        self.weigher_model: str = os.getenv("WEIGHER_MODEL", "gpt-4o")
        # The three specialists (weather/logistics/recommendations) were
        # briefly moved to this tier too, then rolled back: this org's real
        # gpt-4o rate limit is 30,000 tokens/minute (OpenAI's default starting
        # tier), and putting four agents on gpt-4o per comparison turn (three
        # concurrent specialists plus the weigher) reliably tripped it under
        # completely ordinary load - reproduced at a 62% failure rate (5/8),
        # manifesting as a candidate's card silently disappearing or the whole
        # comparison coming back empty. Defaults back to LLM_MODEL's tier
        # (gpt-4o-mini) so the specialists share the weigher's rate-limit
        # budget for exactly one call per turn, not four. Still its own
        # separate setting, not deleted - if this org's gpt-4o limit is raised
        # later, opting back in is a one-line env var change, no code change.
        # See notes/01-agent-architecture.md's "Model selection" section.
        self.specialist_model: str = os.getenv("SPECIALIST_MODEL", "gpt-4o-mini")
        # Deliberately different from llm_model by default: a model grading
        # output from its own model family shares its blind spots, so the
        # judge is less likely to catch the exact class of mistake it would
        # make itself. Independent of any of the above upgrades.
        self.judge_model: str = os.getenv("JUDGE_MODEL", "gpt-4o")
        self.embedding_model: str = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")

        # --- "where next" candidate budget ----------------------------------
        # How many destinations a country-scoped "where next" turn may carry
        # into the specialist fan-out. The pool is the traveller's wishlist plus
        # the five nearest countries (coverage.COUNTRY_NEIGHBOURS), and the
        # wishlist has no upper bound - one account can hold twenty entries - so
        # something has to stop one turn from putting twenty destinations into
        # three specialist prompts at once. That is not just a cost worry: this
        # org's real gpt-4o limit is 30,000 tokens/minute, and the rollback
        # documented on specialist_model above is what tripping it looks like.
        #
        # Deliberately a setting rather than a constant. The right number
        # depends on the model tier and rate limit in front of it, and those
        # change without the code changing.
        #
        # runner.py splits this budget evenly between the two sources (10 -> 5
        # wishlist + 5 neighbours, 8 -> 4 + 4), then lets either side spend the
        # other's unused half, so a traveller with an empty wishlist still gets
        # all five neighbours. The decision_weigher ranks the survivors and
        # returns the best WEIGHER_TOP_N of them.
        self.max_comparison_candidates: int = int(
            os.getenv("MAX_COMPARISON_CANDIDATES", "10")
        )
        # How many ranked cards the weigher returns. The UI shows the top three
        # and hides the rest behind a "show 3 more" toggle, so this being a
        # multiple of three is not an accident.
        self.weigher_top_n: int = int(os.getenv("WEIGHER_TOP_N", "6"))
        # Logistics and Recommendations ask for far more per destination than
        # Weather does (visa + two route options + border notes; or a mandatory
        # budget/activities/transport/warning/citation block, versus Weather's
        # score line + 2-4 sentences). Reproduced live at max_comparison_candidates
        # =10 on specialist_model (gpt-4o-mini): both agents called their
        # required tool once per candidate every time, but silently stopped
        # WRITING about some of them - Logistics dropped one candidate per turn,
        # Recommendations as few as half of ten in one run, a different subset
        # each time. Weather, same model, same candidate count, dropped none -
        # it is candidate-count-times-output-load hitting the cheap model's
        # capacity, not a broken tool call. `runner._run_specialist_batched`
        # splits a specialist's candidate list into chunks of this size and
        # merges the reports, so no single call is ever asked to fully write up
        # more than this many destinations. Kept off gpt-4o rather than sized
        # down: notes/01-agent-architecture.md's "Model selection" section
        # already found that upgrading these three agents' model tier trips
        # this org's 30K TPM rate limit at a 62% failure rate, and that was
        # measured at a smaller candidate count than today's default of 10.
        self.specialist_batch_size: int = int(os.getenv("SPECIALIST_BATCH_SIZE", "5"))

        # --- rag -----------------------------------------------------------
        self.pinecone_api_key: str | None = os.getenv("PINECONE_API_KEY")
        self.pinecone_index: str = os.getenv("PINECONE_INDEX", "onward-rag")
        self.pinecone_cloud: str = os.getenv("PINECONE_CLOUD", "aws")
        self.pinecone_region: str = os.getenv("PINECONE_REGION", "us-east-1")
        # Local fallback index used when PINECONE_API_KEY is absent, so the app and
        # the eval suite still run end-to-end without the managed service.
        self.local_rag_path: Path = Path(
            os.getenv("LOCAL_RAG_PATH", str(self.data_dir / "local_rag_index.json"))
        )

        # --- live RAG-gap lookup (optional) ---------------------------------
        # When a scoped RAG search comes back empty, and this key is set, the
        # search tools fall back to a real web search + LLM synthesis pass
        # instead of just reporting "no data" - see backend/rag/live_lookup.py.
        # Absent this key the behaviour is unchanged: an empty scoped search
        # stays empty, honestly.
        self.tavily_api_key: str | None = os.getenv("TAVILY_API_KEY")

        # --- places / booking ----------------------------------------------
        self.google_places_api_key: str | None = os.getenv("GOOGLE_PLACES_API_KEY")
        # Places bills per call, so identical lookups are served from the SQLite
        # cache for this long. 24h: opening hours and ratings do not move fast.
        self.places_cache_ttl_seconds: int = int(
            os.getenv("PLACES_CACHE_TTL_SECONDS", str(24 * 3600))
        )
        self.places_min_reviews: int = int(os.getenv("PLACES_MIN_REVIEWS", "25"))
        self.booking_affiliate_id: str | None = os.getenv("BOOKING_AFFILIATE_ID")
        self.hostelworld_affiliate_id: str | None = os.getenv("HOSTELWORLD_AFFILIATE_ID")

        # --- tracing -------------------------------------------------------
        self.langfuse_public_key: str | None = os.getenv("LANGFUSE_PUBLIC_KEY")
        self.langfuse_secret_key: str | None = os.getenv("LANGFUSE_SECRET_KEY")
        self.langfuse_host: str = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")

        # --- memory policy -------------------------------------------------
        # See README "When you forget". Profiles persist indefinitely per account;
        # conversational working memory is capped at this many turns.
        self.working_memory_turns: int = int(os.getenv("WORKING_MEMORY_TURNS", "20"))

        # --- frontend ------------------------------------------------------
        self.cors_origins: list[str] = [
            o.strip()
            for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
            if o.strip()
        ]
        self.serve_frontend: bool = _as_bool(os.getenv("SERVE_FRONTEND"), True)

    # --- derived helpers ---------------------------------------------------
    @property
    def llm_enabled(self) -> bool:
        return bool(self.openai_api_key)

    @property
    def pinecone_enabled(self) -> bool:
        return bool(self.pinecone_api_key)

    @property
    def places_enabled(self) -> bool:
        return bool(self.google_places_api_key)

    @property
    def live_lookup_enabled(self) -> bool:
        # Needs both a search key (to find real sources) and an LLM (to
        # synthesise and then verify the answer against them).
        return bool(self.tavily_api_key) and self.llm_enabled

    @property
    def langfuse_enabled(self) -> bool:
        return bool(self.langfuse_public_key and self.langfuse_secret_key)

    def ensure_dirs(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
