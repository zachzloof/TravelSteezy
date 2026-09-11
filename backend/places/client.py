"""Google Places API (New) client.

Covers the three lookups the Recommendations agent needs - geocoding a place
name, nearby search by type, and text search - with:

  * a SQLite response cache (Places bills per call, and a demo re-asking the same
    question should not re-bill or re-rate-limit)
  * bounded retries with exponential backoff on 429/5xx/timeouts
  * graceful degradation: with no GOOGLE_PLACES_API_KEY every call returns
    ``configured: False`` and an empty result rather than raising, so the agent
    says it has no live place data instead of the turn dying

Uses the *New* Places API (``places.googleapis.com/v1``), which is POST-based and
requires an explicit X-Goog-FieldMask naming the fields you want billed.
"""
from __future__ import annotations

import hashlib
import json
import logging
import random
import time
from typing import Any

import httpx

from backend.config import settings
from backend.db import get_conn

logger = logging.getLogger(__name__)

BASE_URL = "https://places.googleapis.com/v1"
NEARBY_URL = f"{BASE_URL}/places:searchNearby"
TEXT_URL = f"{BASE_URL}/places:searchText"

PLACE_FIELDS = ",".join(
    f"places.{f}"
    for f in (
        "id", "displayName", "formattedAddress", "rating", "userRatingCount",
        "priceLevel", "location", "googleMapsUri", "types", "businessStatus",
    )
)

MAX_ATTEMPTS = 3
TIMEOUT_SECONDS = 12.0
RETRY_STATUS = {408, 429, 500, 502, 503, 504}


class PlacesUnavailable(RuntimeError):
    """Raised internally when Places cannot answer; callers degrade gracefully."""


# --------------------------------------------------------------------------- #
# cache
# --------------------------------------------------------------------------- #
def _cache_key(kind: str, payload: dict[str, Any]) -> str:
    blob = json.dumps({"kind": kind, **payload}, sort_keys=True, default=str)
    return hashlib.blake2b(blob.encode("utf-8"), digest_size=16).hexdigest()


def cache_get(key: str) -> Any | None:
    ttl = settings.places_cache_ttl_seconds
    with get_conn() as conn:
        row = conn.execute(
            "SELECT payload FROM places_cache WHERE cache_key = ? "
            "AND (strftime('%s','now') - strftime('%s', created_at)) < ?",
            (key, ttl),
        ).fetchone()
    if row is None:
        return None
    try:
        return json.loads(row["payload"])
    except json.JSONDecodeError:
        return None


def cache_put(key: str, value: Any) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO places_cache (cache_key, payload, created_at) "
            "VALUES (?,?, datetime('now')) "
            "ON CONFLICT(cache_key) DO UPDATE SET payload = excluded.payload, "
            "  created_at = excluded.created_at",
            (key, json.dumps(value, default=str)),
        )


def clear_cache() -> int:
    with get_conn() as conn:
        return conn.execute("DELETE FROM places_cache").rowcount


# --------------------------------------------------------------------------- #
# HTTP
# --------------------------------------------------------------------------- #
def is_configured() -> bool:
    return bool(settings.google_places_api_key)


def _post(url: str, body: dict[str, Any], field_mask: str) -> dict[str, Any]:
    """POST with bounded retries. Raises PlacesUnavailable when it cannot succeed."""
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": settings.google_places_api_key or "",
        "X-Goog-FieldMask": field_mask,
    }

    last_detail = "unknown error"
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response = httpx.post(url, json=body, headers=headers, timeout=TIMEOUT_SECONDS)
        except httpx.RequestError as exc:
            last_detail = f"network error: {exc}"
            logger.warning("Places attempt %d/%d failed: %s", attempt, MAX_ATTEMPTS, exc)
        else:
            if response.status_code == 200:
                return response.json()

            last_detail = f"HTTP {response.status_code}: {response.text[:200]}"
            # 4xx other than rate limiting will not improve on retry.
            if response.status_code not in RETRY_STATUS:
                logger.warning("Places returned %s, not retrying", response.status_code)
                raise PlacesUnavailable(last_detail)
            logger.warning(
                "Places attempt %d/%d got %s", attempt, MAX_ATTEMPTS, response.status_code
            )

        if attempt < MAX_ATTEMPTS:
            # exponential backoff with jitter, so concurrent agents do not sync up
            time.sleep((2 ** (attempt - 1)) * 0.6 + random.uniform(0, 0.3))

    raise PlacesUnavailable(last_detail)


def _normalise(place: dict[str, Any]) -> dict[str, Any]:
    """Flatten one Places result into the shape the rest of the app uses."""
    location = place.get("location") or {}
    return {
        "place_id": place.get("id"),
        "name": (place.get("displayName") or {}).get("text"),
        "address": place.get("formattedAddress"),
        "rating": place.get("rating"),
        "user_rating_count": place.get("userRatingCount"),
        "price_level": place.get("priceLevel"),
        "latitude": location.get("latitude"),
        "longitude": location.get("longitude"),
        "maps_url": place.get("googleMapsUri"),
        "types": place.get("types") or [],
        "business_status": place.get("businessStatus"),
    }


# --------------------------------------------------------------------------- #
# public lookups
# --------------------------------------------------------------------------- #
def geocode(location: str) -> dict[str, Any] | None:
    """Resolve a place name to coordinates using a text search.

    Uses Places rather than the separate Geocoding API so the app needs one key.
    """
    location = (location or "").strip()
    if not location or not is_configured():
        return None

    key = _cache_key("geocode", {"location": location.lower()})
    cached = cache_get(key)
    if cached is not None:
        return cached or None

    try:
        data = _post(
            TEXT_URL,
            {"textQuery": location, "maxResultCount": 1},
            "places.id,places.displayName,places.formattedAddress,places.location",
        )
    except PlacesUnavailable as exc:
        logger.warning("geocode(%s) failed: %s", location, exc)
        return None

    places = data.get("places") or []
    if not places:
        cache_put(key, {})
        return None

    first = places[0]
    coords = first.get("location") or {}
    result = {
        "name": (first.get("displayName") or {}).get("text") or location,
        "address": first.get("formattedAddress"),
        "latitude": coords.get("latitude"),
        "longitude": coords.get("longitude"),
    }
    cache_put(key, result)
    return result


def search_nearby(
    latitude: float,
    longitude: float,
    included_types: list[str],
    radius_meters: int = 2000,
    max_results: int = 20,
) -> list[dict[str, Any]]:
    """Nearby search around a coordinate, filtered by Places type."""
    if not is_configured():
        return []

    radius_meters = max(50, min(int(radius_meters), 50000))
    max_results = max(1, min(int(max_results), 20))

    key = _cache_key(
        "nearby",
        {
            "lat": round(float(latitude), 4),
            "lng": round(float(longitude), 4),
            "types": sorted(included_types),
            "radius": radius_meters,
            "max": max_results,
        },
    )
    cached = cache_get(key)
    if cached is not None:
        return cached

    body = {
        "includedTypes": included_types,
        "maxResultCount": max_results,
        "locationRestriction": {
            "circle": {
                "center": {"latitude": float(latitude), "longitude": float(longitude)},
                "radius": float(radius_meters),
            }
        },
    }
    try:
        data = _post(NEARBY_URL, body, PLACE_FIELDS)
    except PlacesUnavailable as exc:
        logger.warning("search_nearby failed: %s", exc)
        return []

    results = [_normalise(p) for p in (data.get("places") or [])]
    cache_put(key, results)
    return results


def search_text(
    query: str,
    latitude: float | None = None,
    longitude: float | None = None,
    radius_meters: int = 5000,
    max_results: int = 20,
) -> list[dict[str, Any]]:
    """Free-text search, optionally biased to a coordinate."""
    query = (query or "").strip()
    if not query or not is_configured():
        return []

    max_results = max(1, min(int(max_results), 20))
    key = _cache_key(
        "text",
        {
            "q": query.lower(),
            "lat": round(float(latitude), 4) if latitude is not None else None,
            "lng": round(float(longitude), 4) if longitude is not None else None,
            "radius": radius_meters,
            "max": max_results,
        },
    )
    cached = cache_get(key)
    if cached is not None:
        return cached

    body: dict[str, Any] = {"textQuery": query, "maxResultCount": max_results}
    if latitude is not None and longitude is not None:
        body["locationBias"] = {
            "circle": {
                "center": {"latitude": float(latitude), "longitude": float(longitude)},
                "radius": float(max(50, min(int(radius_meters), 50000))),
            }
        }

    try:
        data = _post(TEXT_URL, body, PLACE_FIELDS)
    except PlacesUnavailable as exc:
        logger.warning("search_text(%s) failed: %s", query, exc)
        return []

    results = [_normalise(p) for p in (data.get("places") or [])]
    cache_put(key, results)
    return results
