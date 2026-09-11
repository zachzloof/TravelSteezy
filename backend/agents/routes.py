"""Overland vs flight route knowledge - the data behind the Logistics/Route agent.

SIMPLIFICATION, STATED PLAINLY: these are curated indicative figures for the main
backpacker legs, not a live flight/bus search API. Live pricing would need a paid
aggregator (Skyscanner/Kiwi partner APIs are not open), and a live price is the
wrong answer to "roughly how long and how much to get from here to there" asked
weeks ahead. Figures are ranges and the agent presents them as indicative.

Legs are symmetric: lookup normalises the country pair order.
"""
from __future__ import annotations

from typing import Any

# key: tuple(sorted country pair) -> connection facts
ROUTES: dict[tuple[str, str], dict[str, Any]] = {
    ("cambodia", "thailand"): {
        "overland": "Bangkok - Siem Reap bus, 8-9h, USD 12-25. Poipet border is slow and scam-prone.",
        "overland_hours": 9,
        "overland_cost_usd": 18,
        "flight": "Bangkok - Siem Reap or Phnom Penh, 1h15, USD 60-120.",
        "flight_hours": 1.25,
        "flight_cost_usd": 85,
        "border_notes": "Poipet: officials often ask for an extra 'processing fee'. Carry exact USD 30 for the visa.",
    },
    ("cambodia", "vietnam"): {
        "overland": "Ho Chi Minh City - Phnom Penh bus, 6-7h, USD 12-18. Easy, well-run border at Bavet/Moc Bai.",
        "overland_hours": 6.5,
        "overland_cost_usd": 15,
        "flight": "HCMC - Phnom Penh, 1h, USD 70-110.",
        "flight_hours": 1.0,
        "flight_cost_usd": 90,
        "border_notes": "One of the smoothest land borders in the region. Bus companies handle the paperwork.",
    },
    ("cambodia", "laos"): {
        "overland": "Si Phan Don (4000 Islands) - Stung Treng bus, 6-8h, USD 20-30.",
        "overland_hours": 7,
        "overland_cost_usd": 25,
        "flight": "No direct budget route; via Bangkok, ~USD 150+.",
        "flight_hours": 6.0,
        "flight_cost_usd": 160,
        "border_notes": "Nong Nok Khiene/Trapeang Kriel border charges an unofficial USD 2 stamp fee both ways.",
    },
    ("laos", "thailand"): {
        "overland": "Bangkok - Nong Khai sleeper train then Friendship Bridge to Vientiane, 12h, USD 30-45. Or Chiang Rai - Huay Xai then the 2-day Mekong slow boat to Luang Prabang, USD 35.",
        "overland_hours": 12,
        "overland_cost_usd": 38,
        "flight": "Bangkok - Luang Prabang or Vientiane, 1h45, USD 80-150.",
        "flight_hours": 1.75,
        "flight_cost_usd": 110,
        "border_notes": "Visa on arrival at Friendship Bridge and Huay Xai. Bring USD cash and a passport photo.",
    },
    ("laos", "vietnam"): {
        "overland": "Hanoi - Luang Prabang bus, a punishing 24h+, USD 40-60. Most people fly.",
        "overland_hours": 24,
        "overland_cost_usd": 50,
        "flight": "Hanoi - Luang Prabang, 1h, USD 90-140.",
        "flight_hours": 1.0,
        "flight_cost_usd": 110,
        "border_notes": "The overland route is genuinely rough. Flying is the standard advice despite the cost.",
    },
    ("malaysia", "thailand"): {
        "overland": "Bangkok - Butterworth/Penang train or bus, 20h, USD 30-50. Hat Yai - Penang minivan 4-5h, USD 15.",
        "overland_hours": 20,
        "overland_cost_usd": 40,
        "flight": "Bangkok - Kuala Lumpur or Penang, 2h, USD 40-90 (AirAsia).",
        "flight_hours": 2.0,
        "flight_cost_usd": 60,
        "border_notes": "Straightforward. Classic visa-run route for long Thailand stays. Complete the MDAC online first.",
    },
    ("indonesia", "malaysia"): {
        "overland": "No land route. Ferry Melaka - Dumai (Sumatra) exists but is slow and awkward.",
        "overland_hours": None,
        "overland_cost_usd": None,
        "flight": "Kuala Lumpur - Bali or Jakarta, 3h, USD 60-120.",
        "flight_hours": 3.0,
        "flight_cost_usd": 90,
        "border_notes": "Flying is effectively the only sensible option. Buy the e-VOA before you fly.",
    },
    ("indonesia", "thailand"): {
        "overland": "Not practical - would be several days via Malaysia and a ferry.",
        "overland_hours": None,
        "overland_cost_usd": None,
        "flight": "Bangkok - Bali, 4h direct, USD 120-220; cheaper via Kuala Lumpur.",
        "flight_hours": 4.0,
        "flight_cost_usd": 170,
        "border_notes": "Long-haul by regional standards. Book ahead for the direct AirAsia route.",
    },
    ("indonesia", "singapore"): {
        "overland": "Ferry Singapore - Batam/Bintan, 1h, USD 25.",
        "overland_hours": 1,
        "overland_cost_usd": 25,
        "flight": "Singapore - Bali, 2h40, USD 60-110.",
        "flight_hours": 2.7,
        "flight_cost_usd": 80,
        "border_notes": "Singapore is expensive - transit rather than linger on a shoestring budget.",
    },
    ("philippines", "thailand"): {
        "overland": "No overland route - the Philippines is an archipelago.",
        "overland_hours": None,
        "overland_cost_usd": None,
        "flight": "Bangkok - Manila, 3h20, USD 90-180. Onward domestic flight usually needed.",
        "flight_hours": 3.3,
        "flight_cost_usd": 130,
        "border_notes": "Budget for a domestic connection on top; airlines enforce proof of onward travel strictly.",
    },
    ("philippines", "vietnam"): {
        "overland": "No overland route.",
        "overland_hours": None,
        "overland_cost_usd": None,
        "flight": "HCMC or Hanoi - Manila, 3h, USD 100-190.",
        "flight_hours": 3.0,
        "flight_cost_usd": 140,
        "border_notes": "Add a domestic hop to reach Palawan or Siargao.",
    },
    ("thailand", "vietnam"): {
        "overland": "Possible via Laos or Cambodia but takes 3-4 days. Nobody does it directly.",
        "overland_hours": 72,
        "overland_cost_usd": 70,
        "flight": "Bangkok - Hanoi or HCMC, 1h50, USD 60-130.",
        "flight_hours": 1.85,
        "flight_cost_usd": 90,
        "border_notes": "Flying is standard. Remember the Vietnam e-visa needs 3-5 working days.",
    },
    ("nepal", "thailand"): {
        "overland": "Not practical - would cross India and Myanmar.",
        "overland_hours": None,
        "overland_cost_usd": None,
        "flight": "Bangkok - Kathmandu, 3h30, USD 180-300.",
        "flight_hours": 3.5,
        "flight_cost_usd": 230,
        "border_notes": "The most expensive regional hop on this list. Visa on arrival in Kathmandu, USD cash.",
    },
    ("nepal", "sri lanka"): {
        "overland": "No overland route.",
        "overland_hours": None,
        "overland_cost_usd": None,
        "flight": "Kathmandu - Colombo, 3h30, USD 200-320, usually via Delhi.",
        "flight_hours": 3.5,
        "flight_cost_usd": 250,
        "border_notes": "Sri Lanka ETA must be arranged online before departure.",
    },
    ("sri lanka", "thailand"): {
        "overland": "No overland route.",
        "overland_hours": None,
        "overland_cost_usd": None,
        "flight": "Bangkok - Colombo, 3h30, USD 160-280.",
        "flight_hours": 3.5,
        "flight_cost_usd": 210,
        "border_notes": "ETA required in advance; apply at eta.gov.lk, approved in a day or two.",
    },
    ("malaysia", "vietnam"): {
        "overland": "Not practical overland.",
        "overland_hours": None,
        "overland_cost_usd": None,
        "flight": "Kuala Lumpur - HCMC or Hanoi, 2h, USD 50-110.",
        "flight_hours": 2.0,
        "flight_cost_usd": 75,
        "border_notes": "Cheap AirAsia route. Vietnam e-visa lead time still applies.",
    },
    ("indonesia", "vietnam"): {
        "overland": "Not practical overland.",
        "overland_hours": None,
        "overland_cost_usd": None,
        "flight": "Bali - HCMC, 4h, usually via Kuala Lumpur or Singapore, USD 120-220.",
        "flight_hours": 4.5,
        "flight_cost_usd": 165,
        "border_notes": "Rarely a direct flight; budget a layover.",
    },
    ("cambodia", "malaysia"): {
        "overland": "Via Thailand, 2+ days.",
        "overland_hours": 48,
        "overland_cost_usd": 60,
        "flight": "Phnom Penh - Kuala Lumpur, 2h, USD 70-130.",
        "flight_hours": 2.0,
        "flight_cost_usd": 95,
        "border_notes": "Straightforward AirAsia route.",
    },
}


def _key(a: str, b: str) -> tuple[str, str]:
    pair = sorted([(a or "").strip().lower(), (b or "").strip().lower()])
    return (pair[0], pair[1])


def lookup(origin: str, destination: str) -> dict[str, Any]:
    """Return connection facts between two countries, or a clear 'unknown'."""
    origin_key = (origin or "").strip().lower()
    dest_key = (destination or "").strip().lower()

    if not origin_key:
        return {
            "origin": origin,
            "destination": destination,
            "known": False,
            "note": "Current location unknown - ask the user where they are now.",
        }
    if origin_key == dest_key:
        return {
            "origin": origin_key,
            "destination": dest_key,
            "known": True,
            "note": "Already in this country - no international leg required.",
        }

    route = ROUTES.get(_key(origin_key, dest_key))
    if route is None:
        return {
            "origin": origin_key,
            "destination": dest_key,
            "known": False,
            "note": (
                f"No curated route data for {origin_key} to {dest_key}. Treat travel time "
                "and cost as unverified and say so rather than inventing figures."
            ),
        }

    cheapest = "overland"
    if route.get("overland_cost_usd") is None:
        cheapest = "flight"
    elif route.get("flight_cost_usd") is not None and route["flight_cost_usd"] < route["overland_cost_usd"]:
        cheapest = "flight"

    return {
        "origin": origin_key,
        "destination": dest_key,
        "known": True,
        "overland": route["overland"],
        "overland_hours": route.get("overland_hours"),
        "overland_cost_usd": route.get("overland_cost_usd"),
        "flight": route["flight"],
        "flight_hours": route.get("flight_hours"),
        "flight_cost_usd": route.get("flight_cost_usd"),
        "border_notes": route.get("border_notes"),
        "cheaper_option": cheapest,
    }
