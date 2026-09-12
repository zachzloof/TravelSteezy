"""Onboarding: fixed questions, an LLM extractor, and deterministic writes.

The shape of this is the whole point, so it is worth stating plainly.

The FIRST version of onboarding was a conversation: one agent decided what to ask
next, another pulled structured facts out of the answer. It asked the same
question twice, invented a step it had already completed, and - because the
question itself came from a model - there was no stable thing to write an eval
against. The conversation was the least reliable part of the feature and also the
part that added the least.

So the questions are now DATA, not a model output. They live in ``QUESTIONS``
below, they are the same every time, and the frontend renders them. The model has
exactly one job left: turn one plain-English answer into structured fields. That
is the job LLMs are genuinely good at, and it is the only job here a human could
not have written a rule for.

Everything after extraction is Python:

* free-text bands ("dirt cheap", "as slow as possible") are mapped onto the five
  point scales by ``store.normalise_band``, not by trusting the model to emit a
  valid token;
* place names are resolved to a country and a granularity through the same
  gazetteer the rest of the app uses, so "koh tao" and "Koh Tao, Thailand" become
  one row, not two;
* ratings are clamped and validated;
* every write is an explicit call that lands in the ``memory_writes`` audit log.

The result is that "did onboarding capture this correctly" is a question about
stored rows, which is exactly what the eval cases assert.
"""
from __future__ import annotations

import logging
from datetime import date
from typing import Any

from backend.config import settings
from backend.memory import store, travel
from backend.rag.route_data import COUNTRIES, resolve_country

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# the questions
# --------------------------------------------------------------------------- #
# Ordered, fixed, and served to the frontend from here, so the UI, the extractor
# prompt and the eval suite can never disagree about what was asked.
#
# Each question targets a small number of fields. Asking one thing at a time is
# not only friendlier - it measurably improves extraction, because the model is
# told what to look for instead of scanning for eleven unrelated fields at once.
QUESTIONS: list[dict[str, Any]] = [
    {
        "id": "route",
        "title": "Where have you been so far?",
        "prompt": "Walk me through this trip in order - and tell me what you made of each place.",
        "hint": (
            "Plain English is fine. If you rate somewhere out of 5 I will remember it, "
            "and what you did not enjoy is just as useful as what you loved."
        ),
        "placeholder": (
            "Started in Bangkok - fine but I would not rush back, 3/5. Koh Tao next, did "
            "my Open Water there, loved it, 5. Hanoi was too loud for me, 2/5. Been in "
            "Chiang Mai about a week now."
        ),
        "captures": ["travel_history", "ratings", "current_location"],
        "optional": False,
        "rules": (
            "Every place named here has ALREADY been visited, so it belongs in "
            "\"travel_history\". Leave \"wishlist\" empty unless they clearly "
            "say they have not been somewhere yet."
        ),
    },
    {
        "id": "timing",
        "title": "How long have you got?",
        "prompt": "When did this trip start, when does it end, and is anything about to expire?",
        "hint": (
            "A visa or permit deadline matters more than almost anything else here - it "
            "can rule a whole country out on lead time alone."
        ),
        "placeholder": (
            "Left home in early January, flying out of Singapore on 14 June. My Thai visa "
            "exemption runs out on the 3rd of next month."
        ),
        "captures": ["trip_start_date", "trip_end_date", "visa_deadline"],
        "optional": True,
    },
    {
        "id": "passports",
        "title": "Which passport do you travel on?",
        "prompt": "Tell me every passport you hold - if you have two, that changes the answer.",
        "hint": (
            "Visa rules are nationality-specific. A second passport can turn a five-day "
            "e-visa into a stamp on arrival, so it is worth listing both."
        ),
        "placeholder": "British, and I also have an Irish one.",
        "captures": ["passports"],
        "optional": False,
    },
    {
        "id": "wishlist",
        "title": "Where do you want to get to?",
        "prompt": "Anywhere you are set on, curious about, or want to go back to.",
        "hint": "Somewhere you have already been is fine - wanting a second go at a place counts.",
        "placeholder": (
            "Really want to do Pai and then the slow boat into Laos. Vietnam at some "
            "point. And I would go back to Koh Tao in a heartbeat."
        ),
        "captures": ["wishlist"],
        "optional": True,
        # Question-specific, because the general rules were not enough on their
        # own: an eval case answering "I'd go back to Koh Tao in a heartbeat"
        # had Koh Tao filed as history (which it already was) and dropped from
        # the wishlist entirely, losing the actual intent in the sentence.
        "rules": (
            "Every place named in this answer goes in \"wishlist\" and NOWHERE "
            "else. That includes somewhere they have already been: \"I would go "
            "back to X\", \"X again\", \"another go at X\" are wishlist "
            "entries, not travel history. Leave \"travel_history\" empty for "
            "this question unless they explicitly describe a NEW stop they have "
            "already made."
        ),
    },
    {
        "id": "style",
        "title": "How do you travel?",
        "prompt": "Money, pace, weather, company, and what you actually enjoy doing.",
        "hint": (
            'Rough is fine - "cheap, slow, hate the heat, travelling alone, mostly '
            'hiking" tells me everything I need.'
        ),
        "placeholder": (
            "Pretty tight budget, dorms and street food. I like staying put for a while "
            "rather than moving every night. I wilt in proper heat. Travelling solo. "
            "Mostly hiking, diving and eating."
        ),
        "captures": [
            "budget_band", "travel_style", "climate_preference",
            "social_style", "interests",
        ],
        "optional": False,
    },
]

QUESTION_IDS: tuple[str, ...] = tuple(q["id"] for q in QUESTIONS)

# Answering these is what makes a profile usable. The other two are genuinely
# optional, and the UI says so rather than pretending everything is mandatory.
REQUIRED_STEPS: tuple[str, ...] = tuple(q["id"] for q in QUESTIONS if not q["optional"])


def get_question(step_id: str) -> dict[str, Any] | None:
    return next((q for q in QUESTIONS if q["id"] == step_id), None)


def next_step(answered: list[str]) -> str | None:
    """The first question not yet answered, or None when the set is complete."""
    done = {str(a) for a in answered or []}
    return next((q["id"] for q in QUESTIONS if q["id"] not in done), None)


# --------------------------------------------------------------------------- #
# extraction prompt
# --------------------------------------------------------------------------- #
EXTRACTION_SCHEMA = """{{
  "travel_history": [
    {{"location": "Koh Tao", "country": "Thailand", "order": 2,
     "rating": 5, "review_notes": "did my Open Water here, loved it"}}
  ],
  "wishlist": [{{"location": "Pai", "country": "Thailand", "priority": 1}}],
  "interests": [],
  "passports": [],
  "budget_band": null,
  "travel_style": null,
  "climate_preference": null,
  "social_style": null,
  "current_location": null,
  "trip_start_date": null,
  "trip_end_date": null,
  "visa_deadline_date": null,
  "visa_deadline_note": null,
  "nothing_to_extract": false
}}"""

EXTRACTOR_INSTRUCTION = """You extract structured travel facts from ONE answer a
traveller typed into an onboarding form. You never speak to the user and you
never ask anything.

Today's date is {today}.

THE QUESTION THEY WERE ASKED:
  {question}
  ({hint})

THIS QUESTION IS ABOUT: {captures}
{extra_rules}

Return ONLY a raw JSON object in exactly this shape - no code fences, no prose:

{schema}

RULES

Scope
- Extract only what THIS answer states or clearly implies. Use null or [] for
  anything it does not mention. Never carry anything over from the example above.
- The question tells you which fields matter most, but if they volunteer
  something else, capture that too. People answer more than they were asked.
- Set "nothing_to_extract" to true only if the answer holds no usable fact at all
  (for example "skip", "not sure", "n/a").

travel_history - places they HAVE been on this trip
- One entry per place, in the order they travelled, "order" starting at 1.
- Include the place they are in NOW, and also put it in "current_location".
- Include a place mentioned only in passing ("then Koh Tao for a few days").
- Prefer town or city granularity. If they name only a country, use the country.
- "rating" is 1-5 and ONLY when they actually express how they felt about it.
  Map their words honestly: "loved it" 5, "great" 4, "fine" or "ok" 3, "meh" or
  "would not go back" 2, "hated it" 1. An explicit score they give ("3/5", "a
  solid 4") always wins. If they say nothing about how a place was, "rating" is
  null - do not guess a middling score to fill the field.
- "review_notes" is their own reason in their own words, trimmed. Null if none.

wishlist - places they have NOT been, or want to return to
- "priority" is 1 if they sound set on it, 2 if interested, 3 if idle curiosity.
- A place they say they would go back to belongs here even if it is also in
  travel_history. That is a revisit, not a mistake.
- Never add a place because you think they would enjoy it. Only if they said so.

Preference fields
- Copy the traveller's OWN WORDS into "budget_band", "travel_style",
  "climate_preference" and "social_style" when they do not use one of the
  standard terms. Do not leave a field null just because their phrasing is
  unusual - "dirt cheap", "as slow as I can", "I melt in the heat" and "just me"
  are all usable answers. Code downstream maps them onto the scale.
- Standard terms, if they happen to use one:
    budget_band: shoestring, budget, mid, comfortable, luxury
    travel_style: very_slow, slow, balanced, fast, very_fast
    climate_preference: cold, cool, temperate, warm, hot
    social_style: solo, couple, group
- Record what they WANT, not what they are complaining about. "I melt in the
  heat" is a preference for somewhere cooler, so write "cool" or "hate the heat",
  never "hot". Getting this backwards is the worst mistake you can make here.
- If they explicitly say they have no preference, use the words "no preference".

Other fields
- "passports" is every nationality they say they hold, most-used first. Write the
  country, not the adjective: "British" becomes "United Kingdom", "Irish"
  becomes "Ireland", "Aussie" becomes "Australia".
- "interests" are lowercase single words where possible: nature, food, nightlife,
  trekking, diving, history, beaches, surfing, culture, photography, wildlife,
  markets, climbing, yoga, festivals.
- Dates are ISO yyyy-mm-dd, resolved against today's date. If they give a month
  with no year, choose the nearest future occurrence. If you cannot work a date
  out confidently, use null rather than guessing.
- "visa_deadline_date" is the next hard expiry - a visa, a permit, a flight they
  must be on. "visa_deadline_note" says what expires, in a few words.

THE TRAVELLER'S ANSWER IS THE MESSAGE YOU HAVE BEEN GIVEN."""


def build_extractor(step_id: str):
    """One extractor agent, specialised to the question that was asked.

    Built per call rather than cached because the instruction embeds the
    question, and that context carries real weight: whether a place belongs in
    history or on the wishlist is decided almost entirely by which question
    prompted the answer, and a generic extractor has to guess it from tense.
    """
    from google.adk.agents import LlmAgent

    from backend.agents.graph import build_model

    question = get_question(step_id) or {
        "prompt": "Tell me about your trip.", "hint": "", "captures": [],
    }
    extra = question.get("rules")
    instruction = EXTRACTOR_INSTRUCTION.format(
        today=date.today().isoformat(),
        question=question["prompt"],
        hint=question.get("hint", ""),
        captures=", ".join(question.get("captures", [])) or "anything stated",
        extra_rules=f"\nFOR THIS QUESTION SPECIFICALLY: {extra}\n" if extra else "",
        schema=EXTRACTION_SCHEMA.format(),
    )
    return LlmAgent(
        name="onboarding_extractor",
        model=build_model(),
        description="Turns one plain-text onboarding answer into structured travel fields.",
        instruction=instruction,
        output_key="onboarding_capture",
    )


# --------------------------------------------------------------------------- #
# deterministic clean-up of what the model returned
# --------------------------------------------------------------------------- #
# Adjectives people actually type, mapped to the country name the visa corpus is
# keyed on. Anything not listed is kept verbatim - a passport we do not recognise
# is still the user's passport, and dropping it would be worse than storing it.
NATIONALITY_TO_COUNTRY: dict[str, str] = {
    "british": "United Kingdom", "uk": "United Kingdom", "u.k.": "United Kingdom",
    "english": "United Kingdom", "scottish": "United Kingdom",
    "welsh": "United Kingdom", "northern irish": "United Kingdom",
    "gb": "United Kingdom", "great britain": "United Kingdom",
    "irish": "Ireland", "eire": "Ireland",
    "american": "United States", "usa": "United States", "us": "United States",
    "u.s.": "United States", "united states of america": "United States",
    "australian": "Australia", "aussie": "Australia", "aus": "Australia",
    "new zealander": "New Zealand", "kiwi": "New Zealand", "nz": "New Zealand",
    "canadian": "Canada", "german": "Germany", "french": "France",
    "dutch": "Netherlands", "holland": "Netherlands", "spanish": "Spain",
    "italian": "Italy", "portuguese": "Portugal", "polish": "Poland",
    "swedish": "Sweden", "norwegian": "Norway", "danish": "Denmark",
    "finnish": "Finland", "swiss": "Switzerland", "austrian": "Austria",
    "belgian": "Belgium", "czech": "Czechia", "israeli": "Israel",
    "south african": "South Africa", "brazilian": "Brazil", "argentine": "Argentina",
    "argentinian": "Argentina", "chilean": "Chile", "mexican": "Mexico",
    "japanese": "Japan", "korean": "South Korea", "south korean": "South Korea",
    "chinese": "China", "indian": "India", "singaporean": "Singapore",
    "malaysian": "Malaysia", "filipino": "Philippines", "indonesian": "Indonesia",
    "thai": "Thailand", "vietnamese": "Vietnam",
}


def normalise_passport(value: Any) -> str:
    """"British" -> "United Kingdom"; anything unrecognised is title-cased as given."""
    text = str(value or "").strip()
    if not text:
        return ""
    key = text.lower().removeprefix("a ").removesuffix(" passport").strip()
    if key in NATIONALITY_TO_COUNTRY:
        return NATIONALITY_TO_COUNTRY[key]
    if key in COUNTRIES:
        return key.title()
    return text


def normalise_place(value: Any) -> tuple[str, str, str | None]:
    """Return ``(location, location_type, country)`` for a free-form place string.

    Uses the same gazetteer as the coverage guard and the route corpus, so a
    place captured at onboarding resolves identically to one detected mid-chat.
    Deliberately tolerant: an unknown place is kept, with country None, rather
    than discarded - the corpus does not cover the world and the user's own
    history is not the place to enforce that.
    """
    text = str(value or "").strip().strip(".,;")
    if not text:
        return "", "city", None
    # "Koh Tao, Thailand" -> the town is the informative half.
    head = text.split(",")[0].strip() or text
    country = resolve_country(text)
    if head.lower() in COUNTRIES:
        return head.title(), "country", head.title()
    label = head if any(c.isupper() for c in head) else head.title()
    return label, "city", (country.title() if country else None)


def clamp_rating(value: Any) -> int | None:
    try:
        rating = int(value)
    except (TypeError, ValueError):
        return None
    return rating if 1 <= rating <= 5 else None


# --------------------------------------------------------------------------- #
# applying a capture
# --------------------------------------------------------------------------- #
def apply_capture(
    user_id: int, captured: dict[str, Any], source: str = "onboarding"
) -> list[dict[str, Any]]:
    """Write what one answer yielded. Explicit calls, one per field.

    Returns the list of writes performed, which the UI echoes back to the user as
    "here is what I took from that" - the single most important trust affordance
    in the whole flow. If extraction misreads something, they see it immediately
    on the next screen and can fix it there, rather than discovering months later
    that the assistant thinks they hated Hanoi.
    """
    writes: list[dict[str, Any]] = []
    if not isinstance(captured, dict) or not captured:
        return writes

    # ---- route ------------------------------------------------------------
    for index, entry in enumerate(captured.get("travel_history") or [], start=1):
        if not isinstance(entry, dict):
            continue
        location, location_type, country = normalise_place(entry.get("location"))
        if not location:
            continue
        try:
            order = int(entry["order"]) if entry.get("order") is not None else index
        except (TypeError, ValueError):
            order = index
        result = travel.add_travel_history(
            user_id,
            location=location,
            location_type=entry.get("location_type") or location_type,
            country=entry.get("country") or country,
            arrival_date=entry.get("arrival_date"),
            departure_date=entry.get("departure_date"),
            source=source,
            order_index=order,
        )
        if not result.get("ok"):
            continue
        payload: dict[str, Any] = {"location": location, "order": order}
        rating = clamp_rating(entry.get("rating"))
        notes = str(entry.get("review_notes") or "").strip() or None
        if rating is not None or notes:
            # The rating is the whole reason we asked "what did you make of it",
            # so it is saved in the same breath as the stop itself.
            travel.save_review(
                user_id, location=location, rating=rating,
                review_notes=notes, source=source,
            )
            if rating is not None:
                payload["rating"] = rating
        if result.get("created") or result.get("changed") or rating is not None or notes:
            writes.append(
                {"operation": "add_travel_history", "payload": payload, "source": source}
            )

    # ---- wishlist ---------------------------------------------------------
    for entry in captured.get("wishlist") or []:
        if not isinstance(entry, dict):
            continue
        location, location_type, country = normalise_place(entry.get("location"))
        if not location:
            continue
        try:
            priority = int(entry.get("priority") or 2)
        except (TypeError, ValueError):
            priority = 2
        result = travel.add_wishlist(
            user_id,
            location=location,
            location_type=entry.get("location_type") or location_type,
            country=entry.get("country") or country,
            priority=priority if priority in (1, 2, 3) else 2,
            note=str(entry.get("note") or "").strip() or None,
            source=source,
        )
        if result.get("ok"):
            writes.append(
                {
                    "operation": "add_wishlist",
                    "payload": {
                        "location": location,
                        "priority": result.get("priority", priority),
                        **({"revisit": True} if result.get("revisit") else {}),
                    },
                    "source": source,
                }
            )

    # ---- passports --------------------------------------------------------
    passports = [
        normalise_passport(p) for p in (captured.get("passports") or []) if str(p).strip()
    ]
    passports = [p for p in passports if p]
    if passports:
        existing = store.get_passports(user_id)
        merged = existing + [
            p for p in passports if p.lower() not in {e.lower() for e in existing}
        ]
        if merged != existing:
            store.set_passports(user_id, merged, source=source)
            writes.append(
                {"operation": "set_passports", "payload": {"passports": merged}, "source": source}
            )

    # ---- interests --------------------------------------------------------
    interests = [str(i).strip() for i in (captured.get("interests") or []) if str(i).strip()]
    if interests:
        travel.set_interests(user_id, interests, source=source)
        writes.append(
            {"operation": "set_interests", "payload": {"interests": interests}, "source": source}
        )

    # ---- social style -----------------------------------------------------
    if captured.get("social_style"):
        style = _social_style(str(captured["social_style"]))
        if style and travel.set_social_style(user_id, style, source=source):
            writes.append(
                {
                    "operation": "set_social_style",
                    "payload": {"social_style": style},
                    "source": source,
                }
            )

    # ---- the trip profile --------------------------------------------------
    profile_updates: dict[str, Any] = {}
    for key in ("budget_band", "travel_style", "climate_preference"):
        if captured.get(key):
            # The model was told it may answer in the traveller's own words;
            # this is where those words become one of the five scale points.
            banded = store.normalise_band(key, captured[key])
            if banded:
                profile_updates[key] = banded
    for key in (
        "current_location", "trip_start_date", "trip_end_date",
        "visa_deadline_date", "visa_deadline_note",
    ):
        if captured.get(key):
            profile_updates[key] = str(captured[key]).strip()
    if profile_updates.get("current_location"):
        location, _, _ = normalise_place(profile_updates["current_location"])
        if location:
            profile_updates["current_location"] = location
    if profile_updates:
        store.update_profile(user_id, profile_updates, source=source)
        writes.append(
            {"operation": "update_profile", "payload": profile_updates, "source": source}
        )
    return writes


_SOCIAL_SYNONYMS = {
    "solo": "solo", "alone": "solo", "on my own": "solo", "just me": "solo",
    "by myself": "solo", "myself": "solo", "single": "solo",
    "couple": "couple", "partner": "couple", "girlfriend": "couple",
    "boyfriend": "couple", "wife": "couple", "husband": "couple", "two of us": "couple",
    "group": "group", "friends": "group", "mates": "group", "family": "group",
}


def _social_style(value: str) -> str | None:
    text = value.strip().lower()
    if text in _SOCIAL_SYNONYMS:
        return _SOCIAL_SYNONYMS[text]
    for phrase in sorted(_SOCIAL_SYNONYMS, key=len, reverse=True):
        if phrase in text:
            return _SOCIAL_SYNONYMS[phrase]
    return None


# --------------------------------------------------------------------------- #
# running one step
# --------------------------------------------------------------------------- #
async def answer_step(user_id: int, step_id: str, text: str) -> dict[str, Any]:
    """Extract one onboarding answer and write it. Returns what was captured.

    Failure is never fatal to the flow: if the model is unavailable or returns
    something unusable, the step still advances and the user still reaches the
    review screen, where every field is editable by hand. Onboarding must not be
    a wall someone can get stuck behind.
    """
    from backend.agents import graph
    from backend.agents.runner import _run_agent

    answer = (text or "").strip()
    if not answer:
        return {"captured": {}, "writes": [], "extracted": False, "note": "no answer given"}

    captured: dict[str, Any] = {}
    error: str | None = None
    if settings.llm_enabled:
        try:
            raw, _, _ = await _run_agent(
                build_extractor(step_id),
                {"today": date.today().isoformat()},
                answer,
                str(user_id),
                f"onboard-{step_id}-{user_id}",
            )
            captured = graph.parse_json_block(raw) or {}
        except Exception as exc:  # noqa: BLE001
            logger.warning("onboarding extraction failed on step %s: %s", step_id, exc)
            error = "extraction unavailable"
    else:
        error = "the assistant is not configured, so nothing could be read from that"

    writes = apply_capture(user_id, captured)
    return {
        "captured": captured,
        "writes": writes,
        "extracted": bool(writes),
        "note": error,
    }
