"""Affiliate deep-link construction for Booking.com and Hostelworld.

URL building only - no API, no key, no network. Both sites accept a search URL
with query parameters, so a correctly-shaped link drops the traveller straight
into the right search with their dates prefilled.

Affiliate ids come from env (``BOOKING_AFFILIATE_ID`` / ``HOSTELWORLD_AFFILIATE_ID``)
and are simply omitted when unset, which yields a plain, still-working link.

Honesty note for the UI: these are affiliate links, and the frontend labels them
as such rather than passing them off as neutral recommendations.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from urllib.parse import quote_plus, urlencode

from backend.config import settings

BOOKING_BASE = "https://www.booking.com/searchresults.html"
HOSTELWORLD_BASE = "https://www.hostelworld.com/search"


def _valid_date(value: str | None) -> str | None:
    """Accept only YYYY-MM-DD, so a malformed date never lands in a URL."""
    if not value:
        return None
    try:
        return datetime.strptime(value.strip(), "%Y-%m-%d").date().isoformat()
    except (ValueError, AttributeError):
        return None


def _default_window(checkin: str | None, checkout: str | None) -> tuple[str, str]:
    """Fall back to a sensible 3-night window starting tomorrow."""
    start = _valid_date(checkin)
    end = _valid_date(checkout)
    if start and end and end > start:
        return start, end
    if start and not end:
        return start, (date.fromisoformat(start) + timedelta(days=3)).isoformat()
    tomorrow = date.today() + timedelta(days=1)
    return tomorrow.isoformat(), (tomorrow + timedelta(days=3)).isoformat()


def booking_link(
    location: str,
    checkin: str | None = None,
    checkout: str | None = None,
    adults: int = 1,
    property_type: str | None = "hostels",
) -> str:
    """Booking.com search URL for a destination."""
    start, end = _default_window(checkin, checkout)
    params: dict[str, str | int] = {
        "ss": location,
        "checkin": start,
        "checkout": end,
        "group_adults": max(1, int(adults)),
        "no_rooms": 1,
        "group_children": 0,
    }
    if property_type == "hostels":
        # Booking's property-type facet for hostels.
        params["nflt"] = "ht_id=203"
    if settings.booking_affiliate_id:
        params["aid"] = settings.booking_affiliate_id
    return f"{BOOKING_BASE}?{urlencode(params)}"


def hostelworld_link(
    location: str,
    checkin: str | None = None,
    checkout: str | None = None,
    guests: int = 1,
) -> str:
    """Hostelworld search URL for a destination."""
    start, end = _default_window(checkin, checkout)
    params: dict[str, str | int] = {
        "search_keywords": location,
        "date_from": start,
        "date_to": end,
        "number_of_guests": max(1, int(guests)),
    }
    if settings.hostelworld_affiliate_id:
        params["affiliate"] = settings.hostelworld_affiliate_id
    return f"{HOSTELWORLD_BASE}?{urlencode(params)}"


def maps_link(name: str, address: str | None = None) -> str:
    """Google Maps search link, for places whose API response lacked a URI."""
    query = f"{name} {address}" if address else name
    return f"https://www.google.com/maps/search/?api=1&query={quote_plus(query)}"


def booking_links(
    location: str,
    checkin: str | None = None,
    checkout: str | None = None,
    guests: int = 1,
) -> dict[str, str]:
    """Both booking links for one destination, as returned to the agent and UI."""
    return {
        "booking_com": booking_link(location, checkin, checkout, guests),
        "hostelworld": hostelworld_link(location, checkin, checkout, guests),
        "disclosure": "Affiliate links. They cost you nothing extra.",
    }
