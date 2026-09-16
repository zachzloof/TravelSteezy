"""Knowledge-coverage guard.

Shipped in response to eval case ``honesty-unknown-destination``, which the
baseline run failed: asked about Mongolia and Uzbekistan, the assistant invented
visa rules, budgets and a seasonal verdict, and ranked Mongolia first.

This is a deterministic Python check that runs BEFORE the Decision-Weigher, not
another line of prompt hoping the model behaves. Candidate destinations are
checked against the two knowledge sources the app actually has - the climate table
and the RAG corpus - and anything outside both is passed to the weigher as an
explicitly unsupported destination it is forbidden to rank first.
"""
from __future__ import annotations

import re
from typing import Any, Iterable

from backend.agents.climate import CLIMATE_TABLE
from backend.rag.seed_data import KNOWN_DESTINATIONS

SUPPORTED: set[str] = set(CLIMATE_TABLE) | set(KNOWN_DESTINATIONS)


def resolve_to_covered(candidate: str) -> str | None:
    """Map a candidate to the covered country it belongs to, or None.

    Candidates arrive at town granularity ("Perhentian Islands, Malaysia") as well
    as country level. Treating a covered country's town as unsupported made the
    guard suppress a correct monsoon warning, so resolve through the city index
    and through any country named inside the string before giving up.
    """
    from backend.rag.route_data import KNOWN_CITIES

    key = (candidate or "").strip().lower()
    if not key:
        return None
    if key in SUPPORTED:
        return key
    if key in KNOWN_CITIES:
        return KNOWN_CITIES[key]

    # "perhentian islands, malaysia" or "bali, indonesia"
    for part in (p.strip() for p in key.replace("/", ",").split(",")):
        if part in SUPPORTED:
            return part
        if part in KNOWN_CITIES:
            return KNOWN_CITIES[part]
    for country in SUPPORTED:
        if country in key:
            return country
    for city, country in KNOWN_CITIES.items():
        if city in key:
            return country
    return None


def classify(candidates: list[str]) -> dict[str, Any]:
    """Split candidates into those we hold data for and those we do not."""
    supported, unsupported = [], []
    for candidate in candidates:
        key = (candidate or "").strip().lower()
        if not key:
            continue
        if resolve_to_covered(key):
            supported.append(key)
        else:
            unsupported.append(key)
    return {"supported": supported, "unsupported": unsupported}


def coverage_note(candidates: list[str], live_sourced: Iterable[str] | None = None) -> str:
    """The block injected into the specialist and Decision-Weigher prompts.

    ``live_sourced`` is the set of candidates for which a live web search +
    two-pass LLM verification actually succeeded THIS turn (see
    backend/rag/live_lookup.py). It is unknown - and always empty - when this
    is called for the specialists, since that call happens BEFORE any tool has
    run; it is known when called again for the Decision-Weigher, after the
    specialists' tool calls have completed (see runner.py::_run_comparison).

    A destination with no curated data but a genuine live-sourced hit this
    turn is treated as fully covered, same as curated data - no disclosure, no
    separate confidence tier. The two-pass search-and-verify pipeline in
    live_lookup.py IS the verification; once a candidate has passed it, it is
    real information, not a lesser guess to hedge in the reply. The only
    destinations this guard restricts are ones where NEITHER the curated
    corpus NOR a live search found anything at all THIS turn - seed_data.py's
    SUPPORTED set stays curated-only purely so this function knows who still
    needs the strict warning, not to mark live-sourced content as inferior.
    See the "live lookup is real information, not a hedge" section of
    notes/03-rag-and-retrieval.md.
    """
    split = classify(candidates)
    if not split["unsupported"]:
        return "All candidate destinations are covered by the knowledge base."

    live_sourced_set = {str(d).strip().lower() for d in (live_sourced or [])}
    genuinely_unknown = [d for d in split["unsupported"] if d not in live_sourced_set]

    if not genuinely_unknown:
        return "All candidate destinations are covered by the knowledge base."

    names = ", ".join(genuinely_unknown)
    return (
        f"COVERAGE WARNING - NO DATA HELD FOR: {names}.\n"
        f"Neither the curated knowledge base nor a live search this turn found "
        f"anything for {names}. The knowledge base covers only: "
        f"{', '.join(sorted(SUPPORTED))}.\n"
        f"You MUST NOT rank any of them first, and you MUST give each a verdict of "
        f"'unknown' with the missing-data warning in its cons.\n"
        f"You MUST NOT state ANY figure for them - no dorm prices, no daily budget "
        f"ranges, no visa fees, no journey times, not even approximate or "
        f"'typically around' ones. Quoting a plausible-sounding price you cannot "
        f"source is the exact failure this rule exists to stop.\n"
        f"EXCEPTION: if your OWN tool call for one of {names} finds real data (a "
        f"real passage, not an empty result), report exactly what it returned, "
        f"normally, the same as you would for curated data - that is the only "
        f"case in which stating a figure for {names} is allowed.\n"
        f"Absent that, say plainly that this assistant does not cover {names} and "
        f"they should check a source that does."
    )


def route_note(current_location: str | None) -> str:
    """Guard for the discovery agent: do we hold onward-route data for here?

    Shipped after the eval case ``discovery-honest-about-unknown-origin`` failed:
    the tool correctly reported found:false for Reykjavik, and the agent invented
    Icelandic destinations anyway. Telling it in a non-negotiable prompt block,
    computed in code, is stronger than hoping it reads the tool result.
    """
    from backend.rag.route_data import ROUTE_GRAPH

    origin = (current_location or "").strip().lower()
    if not origin:
        # Bug report #3 (2026-09-14, test1234): with no stored location the old
        # note was a polite suggestion ("ask where they are"), and the agent
        # simply picked a town out of the traveller's past route and answered
        # as though they were still in it - real curated hops for a town they
        # had not mentioned, which reads far more convincingly than a
        # hallucination. Nothing about "ask" is optional here.
        return (
            "CURRENT LOCATION UNKNOWN - no town and no country is recorded. You MUST "
            "NOT assume, infer or pick one: not from their route history, not from "
            "their wishlist, not from anywhere in this prompt. Do not call "
            "discover_next_destinations with a guessed origin. Ask which town or "
            "country they are in now, and answer nothing else this turn."
        )
    if origin in ROUTE_GRAPH:
        hops = ", ".join(ROUTE_GRAPH[origin])
        return f"Route data IS held for {origin}. Known onward hops: {hops}."

    # The route corpus is keyed by TOWN. A traveller whose stored location is a
    # whole country is not outside coverage - we just cannot give hop-by-hop
    # detail until we know which town they are in.
    if origin in SUPPORTED:
        # The list of every town held used to be spelled out here, which turned
        # a "we need one more detail" note into a menu to pick from - same bug
        # report #3: stored location "Thailand", answer delivered from Chiang
        # Mai. The traveller's own town is the only acceptable source.
        return (
            f"{origin.title()} is covered at country level, but the onward-route "
            f"corpus is town-level and no town is recorded. Ask which town they "
            f"are in before giving hop-by-hop detail. You MUST NOT choose a town "
            f"in {origin.title()} yourself, or answer as though they were in one."
        )
    return (
        f"NO CURATED ROUTE DATA HELD FOR {origin.upper()}. The curated route corpus "
        f"covers only these origins: {', '.join(sorted(ROUTE_GRAPH))}. You MUST call "
        f"discover_next_destinations anyway - it falls back to a live search when the "
        f"curated corpus has nothing. If it finds real onward destinations, report "
        f"them normally. Only if it finds nothing either (found: false) must you tell "
        f"the traveller plainly that this assistant has no data for where they are, "
        f"and not invent onward destinations, journey times, prices or attractions."
    )


# The five nearest countries to each origin we can be standing in, used when we
# know the country but not the town, so "where next" still gets a real answer.
#
# WHY THESE ARE NOT RESTRICTED TO THE CURATED CORPUS ANY MORE
# -----------------------------------------------------------
# This table used to hold at most three neighbours, and only ever countries the
# seed corpus already covered. Both limits were wrong in the same way: they let
# the shape of our knowledge base decide what counted as "nearby", so the answer
# to "which country next" silently excluded the country a traveller was most
# likely to actually cross into. Laos's real onward options include China;
# Myanmar's include Bangladesh and India; the Philippines' nearest neighbour by
# a wide margin is Taiwan. None of those could ever be offered.
#
# Six origins were worse than incomplete - Mongolia, Myanmar, South Korea,
# Japan, Australia and New Zealand were deliberately given NO neighbours at all,
# on the reasoning that they had no realistic *overland* pairing inside the
# corpus. That reasoning confused two different things. A backpacker in Japan
# asking where to go next has obvious answers (South Korea is a 1h flight or an
# overnight ferry); what they did not have was curated data, and the honest
# response to missing data is to go and find it, not to pretend the geography
# does not exist. Those six now have five entries each like everyone else.
#
# So these are the five genuinely nearest countries by realistic backpacker
# travel - land borders first, then short sea/air hops - regardless of whether
# the corpus covers them. Twenty of the countries named below are NOT in
# SUPPORTED, and that is deliberate and handled, not an oversight:
#
#   - coverage_note() still gags them by default: no figures, cannot rank first.
#   - backend/rag/live_lookup.py's two-pass search-and-verify fills the gap at
#     runtime, once per destination ever, and coverage_note treats a live hit as
#     fully covered - see notes/03's "live lookup is real information, not a
#     hedge". runner.py now runs that check for uncovered NEIGHBOURS as well as
#     uncovered wishlist entries, which is what makes this table safe to widen.
#   - With no TAVILY_API_KEY the degradation is honest rather than wrong: the
#     new countries stay gagged, say plainly that we hold nothing for them, and
#     lose to covered candidates. They are never described with invented
#     specifics. (See "Degradation is a feature" in CLAUDE.md.)
#
# Deliberately NOT curated here instead: writing seed corpus entries for twenty
# countries would have meant inventing dorm prices, visa fees and month-by-month
# climate ratings for Vanuatu, the Solomon Islands and Kazakhstan out of
# parametric memory. Every number in this repo's corpus was verified when it was
# written; the live pipeline is the mechanism that keeps that true here.
#
# North Korea is the one geographic neighbour omitted on purpose (it is among
# the five nearest to both South Korea and Japan): independent travel there is
# not available to the people this app is for, so offering it as a "where next"
# option would be actively unhelpful rather than merely uncovered.
COUNTRY_NEIGHBOURS: dict[str, list[str]] = {
    # --- Southeast Asia ---------------------------------------------------
    # Thailand, Cambodia and Vietnam's lists are the mainland overland circuit
    # already described in the route docs; China enters via the Boten (Laos) and
    # Hekou/Youyi Guan (Vietnam) crossings, both standard backpacker routes.
    "thailand": ["laos", "cambodia", "myanmar", "malaysia", "vietnam"],
    "laos": ["thailand", "vietnam", "cambodia", "myanmar", "china"],
    "vietnam": ["cambodia", "laos", "china", "thailand", "philippines"],
    "cambodia": ["thailand", "vietnam", "laos", "malaysia", "myanmar"],
    # Singapore is a causeway crossing from Johor Bahru, and Brunei a genuine
    # land border on Borneo - both nearer to Malaysia than anywhere curated.
    "malaysia": ["singapore", "thailand", "brunei", "indonesia", "vietnam"],
    "indonesia": ["singapore", "malaysia", "timor-leste", "brunei", "australia"],
    "philippines": ["taiwan", "malaysia", "brunei", "indonesia", "vietnam"],
    "myanmar": ["thailand", "laos", "bangladesh", "india", "china"],
    # --- South Asia -------------------------------------------------------
    "nepal": ["india", "china", "bhutan", "bangladesh", "pakistan"],
    "india": ["nepal", "bangladesh", "bhutan", "pakistan", "sri lanka"],
    "bhutan": ["india", "nepal", "bangladesh", "china", "myanmar"],
    "sri lanka": ["india", "maldives", "bangladesh", "nepal", "myanmar"],
    # --- East Asia --------------------------------------------------------
    # All four of these had no entry at all before. Japan/Korea/Mongolia are a
    # short hop from each other and from China; Russia is genuinely among
    # Mongolia's and Japan's nearest and is listed honestly, visa difficulty
    # being a fact for the Logistics specialist to report rather than a reason
    # to hide the option. China's own list leads with its two most-travelled
    # overland SE Asia crossings (Laos, Vietnam) and the Trans-Mongolian route,
    # all three curated in routes.py; Myanmar's land border is real but
    # currently unreliable for independent travel (see that route pair's own
    # note) and is still listed honestly rather than hidden. South Korea takes
    # the fifth slot over the genuinely-nearer Nepal specifically because
    # Nepal's only land route runs through Tibet, which requires an
    # agency-arranged permit and tour rather than being a real independent
    # crossing - a short flight/ferry hop beats a land border that isn't
    # actually usable as one.
    "china": ["vietnam", "laos", "mongolia", "myanmar", "south korea"],
    "japan": ["south korea", "taiwan", "china", "russia", "philippines"],
    "south korea": ["japan", "china", "taiwan", "mongolia", "russia"],
    "mongolia": ["china", "russia", "kazakhstan", "south korea", "japan"],
    # --- Oceania ----------------------------------------------------------
    "australia": [
        "indonesia",
        "timor-leste",
        "papua new guinea",
        "new zealand",
        "solomon islands",
    ],
    "new zealand": ["australia", "fiji", "tonga", "vanuatu", "new caledonia"],
    # --- South America ----------------------------------------------------
    # The classic overland "gringo trail" pairings are unchanged and still real,
    # commonly-used land crossings named in the route docs (Cusco -> La Paz,
    # Uyuni -> San Pedro de Atacama, Mendoza <-> Santiago, El Calafate <->
    # Puerto Natales, the Iguazu Falls Brazil/Argentina pairing, Quito ->
    # Bogota). What is new is the near neighbours the corpus never covered:
    # Uruguay and Paraguay in the Southern Cone, Panama and Venezuela off
    # Colombia.
    "peru": ["bolivia", "ecuador", "chile", "brazil", "colombia"],
    "bolivia": ["peru", "chile", "argentina", "paraguay", "brazil"],
    "chile": ["argentina", "bolivia", "peru", "paraguay", "uruguay"],
    "argentina": ["uruguay", "chile", "paraguay", "bolivia", "brazil"],
    "brazil": ["uruguay", "argentina", "paraguay", "bolivia", "peru"],
    "colombia": ["ecuador", "panama", "venezuela", "peru", "brazil"],
    "ecuador": ["colombia", "peru", "panama", "brazil", "bolivia"],
    # --- Africa -------------------------------------------------------------
    # South Africa's five nearest are its actual land-border neighbours (Lesotho
    # is a full enclave within South Africa, so Eswatini - a real border crossing
    # from the Kruger/Hazyview area described in the route docs - takes the fifth
    # slot instead as the more usable near-neighbour for an independent traveller).
    "south africa": ["namibia", "botswana", "zimbabwe", "mozambique", "eswatini"],
}

# Every origin above now carries five, so this is the number of neighbour slots
# a "where next" turn can contribute. runner.py splits its candidate budget
# evenly between these and the traveller's own wishlist.
NEARBY_COUNTRY_LIMIT = 5


def nearby_country_options(origin: str, limit: int = NEARBY_COUNTRY_LIMIT) -> list[str]:
    """The nearest countries to ``origin``, nearest first. Empty if unknown.

    Empty now means only "this origin is not a country we hold geography for" -
    it no longer means "this origin has no realistic onward country", which is
    what it used to mean for Japan, Australia and the other four (see the note
    on COUNTRY_NEIGHBOURS above).
    """
    return COUNTRY_NEIGHBOURS.get((origin or "").strip().lower(), [])[:limit]


# --------------------------------------------------------------------------- #
# question SCOPE: is this a "which country" question or a "which town" one?
# --------------------------------------------------------------------------- #
# Bug report #3 (2026-09-14, test1234): "which country should i go to next",
# asked three different ways, was answered three times with towns in the country
# the traveller was already in, once with their visa about to expire. The cause
# was structural, not a model failure: the scope of a "where next" answer was
# decided entirely by the granularity of the STORED location (town -> town-level
# discovery agent, country -> country-level comparison), and the word "country"
# in the question had no effect anywhere in the pipeline.
#
# Deterministic, code-computed, and applied as an override the same way the
# two-destinations-means-compare rule is (see runner.py) - not a line of prompt
# asking the classifier to be more careful.
_COUNTRY_SCOPE_RE = re.compile(
    r"""
    \b(?:which|what|another|different|new|next|other)\s+countr(?:y|ies)\b
  | \bcountr(?:y|ies)\s+(?:should|to|next|do|can|would|is|are)\b
  | \b(?:best|cheapest|safest|easiest|nearest|closest|warmest)\s+countr(?:y|ies)\b
  | \b(?:change|leave|leaving|exit|switch)\s+(?:the\s+|this\s+|a\s+)?countr(?:y|ies)\b
  | \b(?:cross|crossing)\s+(?:the\s+|a\s+)?border\b
  | \bborder\s+(?:run|hop|crossing)\b
  | \bvisa\s+run\b
  | \bout\s+of\s+(?:the\s+|this\s+)?country\b
  | \bvisa\s+(?:is\s+|has\s+)?(?:running\s+out|expir\w*|about\s+to\s+expire|runs\s+out|up)\b
  | \b(?:overstay|overstaying)\b
    """,
    re.IGNORECASE | re.VERBOSE,
)


def wants_country_scope(message: str) -> bool:
    """True when the message asks about leaving the country, not about the next town.

    Covers the two phrasings that mean the same thing operationally: naming the
    country granularity outright ("which country next", "I want to change
    country", "crossing the border"), and the constraint that forces it anyway
    ("my visa is running out"). A visa about to expire is a leave-the-country
    fact, and answering it with towns in the country being left is the single
    worst answer the app can give.

    Deliberately NOT matched: "countryside", and a bare mention of a country
    name - travellers name countries constantly in questions that are still
    about towns ("best bit of Thailand?"), and over-firing here would push
    ordinary town-level questions into a country comparison.
    """
    return bool(_COUNTRY_SCOPE_RE.search(message or ""))
