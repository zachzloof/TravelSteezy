"""ADK FunctionTools backed by the Google Places API (New).

Every tool here:
  * records itself in the per-turn ToolRecorder, so evals can assert that a real
    lookup happened rather than pattern-matching the model's prose
  * ranks results with the Bayesian weighted score, never raw rating order
  * degrades to ``configured: false`` with an empty list when no Places key is
    set, so the agent says it has no live data instead of the turn failing

Note on hostels: Places API (New) has no "hostel" type - ``lodging`` returns
hotels, which is the wrong answer for this app's users. Hostel search therefore
goes through text search, which does match the word, and then filters on it.
"""
from __future__ import annotations

from typing import Any

from backend.agents.tools import _record
from backend.config import settings
from backend.places import affiliate, client, clustering, ranking

# Places types we let the agent ask for, mapped to the API's type strings.
PLACE_TYPE_MAP: dict[str, list[str]] = {
    "lodging": ["lodging"],
    "hostel": ["lodging"],
    "food": ["restaurant", "cafe"],
    "restaurant": ["restaurant"],
    "cafe": ["cafe"],
    "bar": ["bar"],
    "nightlife": ["bar", "night_club"],
    "attraction": ["tourist_attraction"],
    "nature": ["park"],
    "market": ["market"],
    "museum": ["museum"],
    "laundry": ["laundry"],
    "pharmacy": ["pharmacy"],
    "atm": ["atm"],
}

HOSTEL_WORDS = ("hostel", "backpacker", "guesthouse", "guest house", "dorm")


def _unavailable(tool: str, args: dict[str, Any], reason: str) -> dict[str, Any]:
    result = {
        "configured": False,
        "results": [],
        "note": reason,
    }
    _record(tool, args, result)
    return result


def _shape(place: dict[str, Any]) -> dict[str, Any]:
    """Trim a ranked place to what the agent and UI actually need."""
    return {
        "name": place.get("name"),
        "address": place.get("address"),
        "rating": place.get("rating"),
        "user_rating_count": place.get("user_rating_count"),
        "price_level": place.get("price_level"),
        "weighted_score": place.get("weighted_score"),
        "maps_url": place.get("maps_url")
        or affiliate.maps_link(place.get("name") or "", place.get("address")),
    }


# --------------------------------------------------------------------------- #
# general place search
# --------------------------------------------------------------------------- #
def get_places_recommendations(
    location: str, place_type: str, radius_meters: int = 2000
) -> dict[str, Any]:
    """Find real, currently-operating places of a given type near a location.

    Results are ranked by a Bayesian weighted score, not by raw star rating, so a
    place with one five-star review cannot outrank a well-reviewed one.

    Args:
        location: Town or city to search in, e.g. "Chiang Mai".
        place_type: One of lodging, hostel, food, restaurant, cafe, bar,
            nightlife, attraction, nature, market, museum, laundry, pharmacy, atm.
        radius_meters: Search radius around the centre of that location, 50-50000.
    """
    args = {"location": location, "place_type": place_type, "radius_meters": radius_meters}
    if not settings.places_enabled:
        return _unavailable(
            "get_places_recommendations", args,
            "No live place data: GOOGLE_PLACES_API_KEY is not configured on this deployment.",
        )

    centre = client.geocode(location)
    if not centre or centre.get("latitude") is None:
        return _unavailable(
            "get_places_recommendations", args, f"Could not locate {location!r}."
        )

    types = PLACE_TYPE_MAP.get((place_type or "").strip().lower())
    if not types:
        return _unavailable(
            "get_places_recommendations", args,
            f"Unsupported place_type {place_type!r}. Supported: {', '.join(sorted(PLACE_TYPE_MAP))}.",
        )

    raw = client.search_nearby(
        centre["latitude"], centre["longitude"], types, radius_meters=radius_meters
    )
    ranked = ranking.rank_places(raw, min_reviews=settings.places_min_reviews, limit=8)

    result = {
        "configured": True,
        "location": centre.get("name") or location,
        "place_type": place_type,
        "radius_meters": radius_meters,
        "ranking_method": (
            "Bayesian weighted score: (v/(v+m))*R + (m/(v+m))*C, "
            f"m={settings.places_min_reviews}"
        ),
        "results": [_shape(p) for p in ranked],
    }
    _record("get_places_recommendations", args, {"count": len(result["results"])})
    return result


# --------------------------------------------------------------------------- #
# hostels
# --------------------------------------------------------------------------- #
def find_hostels(
    location: str, budget_band: str = "shoestring", radius_meters: int = 4000
) -> dict[str, Any]:
    """Find hostels and backpacker guesthouses in a town, ranked and with booking links.

    Use this rather than get_places_recommendations for accommodation: the Places
    "lodging" type is dominated by hotels, which is not what a backpacker wants.

    Args:
        location: Town or city, e.g. "Chiang Mai".
        budget_band: shoestring, mid or comfortable. Filters out pricier places.
        radius_meters: Search radius, 50-50000.
    """
    args = {"location": location, "budget_band": budget_band}
    if not settings.places_enabled:
        out = _unavailable(
            "find_hostels", args,
            "No live hostel data: GOOGLE_PLACES_API_KEY is not configured.",
        )
        # The booking links need no API key, so still give the traveller those.
        out["booking_links"] = affiliate.booking_links(location)
        return out

    centre = client.geocode(location)
    lat = centre.get("latitude") if centre else None
    lon = centre.get("longitude") if centre else None

    raw = client.search_text(
        f"hostels and backpacker guesthouses in {location}",
        latitude=lat, longitude=lon, radius_meters=radius_meters,
    )
    # Keep only things that actually read as budget accommodation.
    hostels = [
        p for p in raw
        if any(word in (p.get("name") or "").lower() for word in HOSTEL_WORDS)
        or "lodging" in (p.get("types") or [])
    ] or raw

    ranked = ranking.rank_places(
        hostels, min_reviews=settings.places_min_reviews, budget_band=budget_band, limit=8
    )
    result = {
        "configured": True,
        "location": (centre or {}).get("name") or location,
        "budget_band": budget_band,
        "ranking_method": (
            "Bayesian weighted score, not raw rating order; "
            f"m={settings.places_min_reviews}"
        ),
        "results": [_shape(p) for p in ranked],
        "booking_links": affiliate.booking_links(location),
    }
    _record("find_hostels", args, {"count": len(result["results"])})
    return result


# --------------------------------------------------------------------------- #
# food
# --------------------------------------------------------------------------- #
def find_food_near(
    location: str, craving: str = "cheap local food", radius_meters: int = 1500
) -> dict[str, Any]:
    """Find places to eat near a location, ranked by weighted score.

    Args:
        location: Town, city or area, e.g. "Chiang Mai Old City".
        craving: What they want, e.g. "khao soi", "vegetarian", "night market food".
        radius_meters: Search radius, 50-50000.
    """
    args = {"location": location, "craving": craving, "radius_meters": radius_meters}
    if not settings.places_enabled:
        return _unavailable(
            "find_food_near", args,
            "No live food data: GOOGLE_PLACES_API_KEY is not configured.",
        )

    centre = client.geocode(location)
    lat = centre.get("latitude") if centre else None
    lon = centre.get("longitude") if centre else None

    raw = client.search_text(
        f"{craving} in {location}", latitude=lat, longitude=lon, radius_meters=radius_meters
    )
    ranked = ranking.rank_places(raw, min_reviews=settings.places_min_reviews, limit=8)

    result = {
        "configured": True,
        "location": (centre or {}).get("name") or location,
        "craving": craving,
        "results": [_shape(p) for p in ranked],
    }
    _record("find_food_near", args, {"count": len(result["results"])})
    return result


# --------------------------------------------------------------------------- #
# areas to stay
# --------------------------------------------------------------------------- #
def suggest_areas_to_stay(location: str, radius_meters: int = 5000) -> dict[str, Any]:
    """Group a town's budget accommodation into geographic areas.

    Backpackers choose an area before a bed, so this answers "which part of town
    should I stay in" rather than listing individual properties.

    Args:
        location: Town or city, e.g. "Chiang Mai".
        radius_meters: How far out to look, 50-50000.
    """
    args = {"location": location, "radius_meters": radius_meters}
    if not settings.places_enabled:
        return _unavailable(
            "suggest_areas_to_stay", args,
            "No live area data: GOOGLE_PLACES_API_KEY is not configured.",
        )

    centre = client.geocode(location)
    lat = centre.get("latitude") if centre else None
    lon = centre.get("longitude") if centre else None

    raw = client.search_text(
        f"hostels and backpacker guesthouses in {location}",
        latitude=lat, longitude=lon, radius_meters=radius_meters,
    )
    ranked = ranking.rank_places(raw, min_reviews=settings.places_min_reviews)
    areas = clustering.cluster_places(ranked, radius_meters=800, min_cluster_size=2)

    result = {
        "configured": True,
        "location": (centre or {}).get("name") or location,
        "areas": [a for a in areas if not a["is_outlier"]][:4],
        "standalone_options": [a for a in areas if a["is_outlier"]][:3],
        "note": (
            "Area labels are derived from the street of the strongest listing, not "
            "official neighbourhood boundaries."
        ),
    }
    _record("suggest_areas_to_stay", args, {"areas": len(result["areas"])})
    return result


# --------------------------------------------------------------------------- #
# booking links
# --------------------------------------------------------------------------- #
def get_booking_links(
    location: str, checkin: str = "", checkout: str = "", guests: int = 1
) -> dict[str, Any]:
    """Build Booking.com and Hostelworld search links for a destination.

    Needs no API key. Always disclose to the traveller that these are affiliate
    links.

    Args:
        location: Town or city to search for accommodation in.
        checkin: Check-in date as YYYY-MM-DD. Empty for a default window.
        checkout: Check-out date as YYYY-MM-DD. Empty for a default window.
        guests: Number of guests.
    """
    links = affiliate.booking_links(location, checkin or None, checkout or None, guests)
    _record("get_booking_links", {"location": location}, {"built": True})
    return {"location": location, **links}
