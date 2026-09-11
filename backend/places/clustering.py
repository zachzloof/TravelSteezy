"""Neighbourhood clustering for "which area should I stay in".

Backpackers do not pick a hostel first, they pick an *area* first - Old City vs
Nimman in Chiang Mai, Pham Ngu Lao vs District 1 in Saigon. Given a set of ranked
hostels with coordinates, this groups them into geographic clusters so the agent
can talk about areas rather than reciting twenty individual properties.

Deliberately a small centroid-based clustering rather than importing
scikit-learn: the input is tens of points, not thousands, and an extra heavy
dependency on the deploy image is not worth it. No network, no key, so it is
unit-testable.
"""
from __future__ import annotations

import math
import re
from typing import Any

EARTH_RADIUS_M = 6_371_000

# Leading house numbers: "27", "5/10", "47/5", "12-14", "229/2".
_HOUSE_NUMBER = re.compile(r"^\d+\s*[/-]?\s*\d*[A-Za-z]?$")


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in metres."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(a))


def cluster_places(
    places: list[dict[str, Any]],
    radius_meters: int = 700,
    min_cluster_size: int = 2,
    max_spread_meters: int | None = None,
) -> list[dict[str, Any]]:
    """Group places into walkable areas.

    A place joins a cluster when it is within ``radius_meters`` of that cluster's
    CENTROID and joining would not stretch the cluster past ``max_spread_meters``.

    Centroid distance rather than single-linkage nearest-member: with
    single-linkage, a chain of hostels 700m apart merges an entire city into one
    "area" spanning several kilometres, which is useless advice. The spread cap is
    the backstop that keeps an area genuinely walkable.
    """
    located = [
        p for p in places
        if p.get("latitude") is not None and p.get("longitude") is not None
    ]
    if not located:
        return []

    if max_spread_meters is None:
        max_spread_meters = radius_meters * 2

    # Strongest places first, so clusters form around the best options rather than
    # around whichever result the API happened to return first.
    ordered_input = sorted(
        located, key=lambda p: p.get("weighted_score") or 0.0, reverse=True
    )

    clusters: list[list[dict[str, Any]]] = []
    centroids: list[tuple[float, float]] = []

    for place in ordered_input:
        best_index, best_distance = None, None
        for index, (clat, clon) in enumerate(centroids):
            distance = haversine_m(place["latitude"], place["longitude"], clat, clon)
            if distance <= radius_meters and (best_distance is None or distance < best_distance):
                candidate = clusters[index] + [place]
                if _spread(candidate) <= max_spread_meters:
                    best_index, best_distance = index, distance

        if best_index is None:
            clusters.append([place])
            centroids.append((place["latitude"], place["longitude"]))
        else:
            clusters[best_index].append(place)
            members = clusters[best_index]
            centroids[best_index] = (
                sum(m["latitude"] for m in members) / len(members),
                sum(m["longitude"] for m in members) / len(members),
            )

    summaries = [_summarise(c, min_cluster_size) for c in clusters]
    summaries.sort(
        key=lambda c: (c["place_count"] >= min_cluster_size, c["mean_score"]), reverse=True
    )
    return summaries


def _summarise(cluster: list[dict[str, Any]], min_cluster_size: int) -> dict[str, Any]:
    lat = sum(p["latitude"] for p in cluster) / len(cluster)
    lon = sum(p["longitude"] for p in cluster) / len(cluster)
    scores = [p.get("weighted_score") or 0.0 for p in cluster]
    ratings = [p["rating"] for p in cluster if p.get("rating")]

    ordered = sorted(cluster, key=lambda p: p.get("weighted_score") or 0.0, reverse=True)
    return {
        "label": _label_from(ordered),
        "centroid": {"latitude": round(lat, 6), "longitude": round(lon, 6)},
        "place_count": len(cluster),
        "is_outlier": len(cluster) < min_cluster_size,
        "mean_score": round(sum(scores) / len(scores), 4) if scores else 0.0,
        "mean_rating": round(sum(ratings) / len(ratings), 2) if ratings else None,
        "spread_meters": _spread(cluster),
        "top_places": [
            {
                "name": p.get("name"),
                "rating": p.get("rating"),
                "user_rating_count": p.get("user_rating_count"),
                "weighted_score": p.get("weighted_score"),
                "maps_url": p.get("maps_url"),
            }
            for p in ordered[:4]
        ],
    }


def _label_from(ordered: list[dict[str, Any]]) -> str:
    """Name the area after the street of its strongest member.

    Places has no "neighbourhood" field on a nearby search, so the address line is
    the best available handle. It is a label, not a claim about official boundaries.
    """
    for place in ordered:
        for component in (place.get("address") or "").split(","):
            street = component.strip()
            if not street:
                continue
            # Drop a leading house number so we get a street, not an address.
            parts = street.split(" ", 1)
            if _HOUSE_NUMBER.match(parts[0]):
                if len(parts) == 1:
                    continue  # the component was only a number - try the next one
                street = parts[1].strip()
            # Skip postcodes and anything still purely numeric.
            if not street or _HOUSE_NUMBER.match(street.replace(" ", "")):
                continue
            return f"Around {street}"
    return "Unnamed area"


def _spread(cluster: list[dict[str, Any]]) -> int:
    if len(cluster) < 2:
        return 0
    return int(
        max(
            haversine_m(p["latitude"], p["longitude"], q["latitude"], q["longitude"])
            for p in cluster
            for q in cluster
        )
    )
