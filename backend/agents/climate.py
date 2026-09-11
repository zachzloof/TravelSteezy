"""Seasonal/climate knowledge table - the data behind the Weather/Timing agent.

SIMPLIFICATION, STATED PLAINLY: this is a curated seasonal-knowledge lookup, not a
live weather API call. That is a deliberate choice, not a shortcut taken to save
work. The question this app answers is "should I go to Laos in July", asked weeks
or months ahead; a forecast API only covers the next ~14 days and cannot answer
it. Climatological season boundaries are stable year to year, so a table gives a
better and more testable answer than a forecast endpoint would.

The consequence to be honest about: this cannot tell you about an anomalous year
(an unusually early monsoon, a specific storm). The agent prompt says so.

Because it is a table rather than a model, the eval suite can assert the exact
verdict for a (country, month) pair - see evals/cases.jsonl.
"""
from __future__ import annotations

from typing import Any

from backend.rag.route_data import resolve_country

# Canonical display names, indexed 1-12.
MONTH_NAMES = [
    "january", "february", "march", "april", "may", "june",
    "july", "august", "september", "october", "november", "december",
]

MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11,
    "december": 12,
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "jun": 6, "jul": 7, "aug": 8,
    "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dec": 12,
}

# rating vocabulary used everywhere downstream:
#   good  - prime/shoulder conditions
#   mixed - travellable but with a real caveat
#   avoid - monsoon peak, hazard season, or a closure
CLIMATE_TABLE: dict[str, dict[str, Any]] = {
    "thailand": {
        "summary": "Two systems: Andaman coast wet May-Oct, Gulf islands wet Nov-Dec, north hazy Mar-Apr.",
        "months": {
            1: ("good", "Peak dry season nationwide. Best month, and priced like it."),
            2: ("good", "Dry and warm everywhere. Excellent."),
            3: ("mixed", "Hot. Burning season starts in the north - Chiang Mai air quality drops sharply."),
            4: ("mixed", "Hottest month (38C+). Burning season peaks in the north. Songkran mid-month is busy and expensive."),
            5: ("mixed", "Southwest monsoon starts on the Andaman coast. Gulf islands still fine."),
            6: ("mixed", "Andaman coast wet; Gulf islands (Koh Tao, Samui, Phangan) are at their best."),
            7: ("mixed", "Andaman wet, Gulf good. Split your plan by coast."),
            8: ("mixed", "Andaman wet, Gulf good."),
            9: ("avoid", "Wettest month on the Andaman coast. Ferries cancelled, some islands effectively shut."),
            10: ("avoid", "Andaman monsoon peak continues. Gulf side starting to turn."),
            11: ("mixed", "Andaman clearing and excellent; Gulf islands now in their wet period."),
            12: ("good", "Dry and cool nationwide except lingering Gulf rain early in the month."),
        },
    },
    "vietnam": {
        "summary": "No single national season. Central coast floods Sep-Nov; north cold Dec-Feb.",
        "months": {
            1: ("mixed", "South and centre good; the north (Hanoi, Sapa) is cold and misty."),
            2: ("good", "Good countrywide window opens; north still chilly."),
            3: ("good", "Best all-country month. Dry in the centre and south, warming in the north."),
            4: ("good", "Excellent countrywide."),
            5: ("mixed", "Southern wet season begins; north and centre still good."),
            6: ("mixed", "Hot. South has afternoon downpours. Sapa rice terraces are green."),
            7: ("mixed", "Wet in the south, hot in the centre."),
            8: ("mixed", "Wet in the south; Ha Giang and Sapa at their greenest."),
            9: ("avoid", "Typhoon and flood season begins on the central coast. Hoi An floods most years."),
            10: ("avoid", "Peak central-coast flooding and typhoon risk."),
            11: ("mixed", "Central flooding tailing off; north turning cold; south drying out."),
            12: ("mixed", "South is good and dry; north is cold."),
        },
    },
    "cambodia": {
        "summary": "Wet May-Oct peaking Sep-Oct; Mar-May brutally hot; Nov-Feb peak season.",
        "months": {
            1: ("good", "Dry, comfortable, peak season."),
            2: ("good", "Dry and pleasant."),
            3: ("mixed", "Getting hot."),
            4: ("avoid", "38-40C at Angkor. Genuinely punishing if you are cycling the temples."),
            5: ("mixed", "Wet season begins, still very hot."),
            6: ("mixed", "Afternoon rain. Green, cheap, quiet."),
            7: ("mixed", "Wet but travellable; Angkor is green and uncrowded."),
            8: ("mixed", "Wet but travellable."),
            9: ("avoid", "Wettest month. Rural roads in Ratanakiri and Mondulkiri become impassable."),
            10: ("avoid", "Flooding continues; Tonle Sap at maximum."),
            11: ("good", "Dry season begins. Excellent, and the moats are still full."),
            12: ("good", "Dry, cool, peak season."),
        },
    },
    "laos": {
        "summary": "Wet May-Oct; burning season Mar-Apr; northern hills genuinely cold Dec-Jan.",
        "months": {
            1: ("good", "Dry and clear. Cold at night in the northern hills - bring a layer."),
            2: ("good", "Dry and clear, warming up."),
            3: ("avoid", "Burning season. Hill haze obscures the Luang Prabang views people come for; air quality poor."),
            4: ("avoid", "Burning season peak plus extreme heat."),
            5: ("mixed", "Rains begin, haze clears."),
            6: ("mixed", "Wet but green; slow boat still runs."),
            7: ("mixed", "Wet season. Afternoon rain, humid."),
            8: ("mixed", "Wettest stretch; some rural roads difficult."),
            9: ("avoid", "Heavy rain, river levels high, road travel unreliable."),
            10: ("mixed", "Rains ending, countryside at its greenest."),
            11: ("good", "Ideal - dry, clear, comfortable."),
            12: ("good", "Dry and clear; cold nights in the north."),
        },
    },
    "indonesia": {
        "summary": "Wet Nov-Mar (peak Jan-Feb); dry Apr-Oct with Jul-Aug the busiest.",
        "months": {
            1: ("avoid", "Wet season peak. Heavy afternoon rain, road flooding, rough Gili crossings."),
            2: ("avoid", "Wet season peak continues. Poor diving visibility."),
            3: ("mixed", "Rains easing off through the month."),
            4: ("good", "Dry season begins. Excellent and not yet crowded."),
            5: ("good", "Excellent - dry, and the best value month of the dry season."),
            6: ("good", "Dry and reliable."),
            7: ("mixed", "Perfect weather but peak crowds and peak prices in Canggu, Ubud and the Gilis."),
            8: ("mixed", "Perfect weather, worst crowds and prices of the year."),
            9: ("good", "Dry, quieter than August."),
            10: ("good", "Dry, good value, end of the good window."),
            11: ("mixed", "Wet season starting."),
            12: ("avoid", "Wet, plus Christmas/New Year price spike."),
        },
    },
    "malaysia": {
        "summary": "East coast islands shut Nov-Feb; west coast and Borneo fine year round.",
        "months": {
            1: ("mixed", "East coast monsoon - Perhentians closed. West coast (Penang, Langkawi) fine."),
            2: ("mixed", "East coast still closed; west coast good."),
            3: ("good", "Good nationwide; east coast islands reopening."),
            4: ("good", "Good nationwide."),
            5: ("good", "Good nationwide - east coast islands at their best."),
            6: ("good", "Good nationwide."),
            7: ("good", "Good nationwide, peak for the east coast islands."),
            8: ("good", "Good nationwide."),
            9: ("mixed", "Heavier rain on the west coast; haze possible from regional fires."),
            10: ("mixed", "Wetter on the west coast."),
            11: ("avoid", "Northeast monsoon begins - Perhentian and Redang boats stop, guesthouses shut."),
            12: ("avoid", "East coast islands closed. West coast still workable."),
        },
    },
    "philippines": {
        "summary": "Typhoon season Jun-Nov peaking Aug-Oct; dry and reliable Dec-May.",
        "months": {
            1: ("good", "Dry season. Reliable ferries and flights."),
            2: ("good", "Dry and excellent."),
            3: ("good", "Excellent - El Nido and Coron at their best."),
            4: ("good", "Excellent, hot, peak for island hopping."),
            5: ("good", "Good, hot, end of the dry window."),
            6: ("mixed", "Typhoon season begins. Risk is still moderate."),
            7: ("mixed", "Wet, rising typhoon risk."),
            8: ("avoid", "Typhoon peak. Ferry and domestic flight cancellations strand people for days."),
            9: ("avoid", "Typhoon peak continues."),
            10: ("avoid", "Typhoon peak continues; highest historical landfall month."),
            11: ("mixed", "Typhoon risk falling away; conditions improving."),
            12: ("good", "Dry season returns."),
        },
    },
    "nepal": {
        "summary": "Trek Oct-Nov (best) or Mar-May; monsoon Jun-Sep is genuinely bad for trekking.",
        "months": {
            1: ("mixed", "Clear but bitterly cold at altitude; high passes such as Thorong La can be snowed shut."),
            2: ("mixed", "Cold at altitude, clearing; lower treks fine."),
            3: ("good", "Second trekking season opens. Rhododendrons in bloom."),
            4: ("good", "Warm, good trekking, slightly hazy views."),
            5: ("mixed", "Warm and increasingly hazy; pre-monsoon storms build."),
            6: ("avoid", "Monsoon arrives. Leeches, landslides, cloud-covered mountains."),
            7: ("avoid", "Monsoon peak. Trekking is miserable and in places dangerous; Lukla flights cancelled."),
            8: ("avoid", "Monsoon peak continues."),
            9: ("mixed", "Monsoon ending; trails clearing late in the month."),
            10: ("good", "The prime month. Stable weather, clear mountain views, busy trails."),
            11: ("good", "Prime season continues, colder and quieter than October."),
            12: ("mixed", "Clear but cold; shorter and lower treks only."),
        },
    },
    "sri lanka": {
        "summary": "Two opposing monsoons - there is nearly always a good coast, just not both.",
        "months": {
            1: ("good", "South and west coasts (Mirissa, Galle, Unawatuna) at their best."),
            2: ("good", "South and west excellent; hill country good."),
            3: ("good", "South and west good; whale watching season."),
            4: ("good", "Good most places - the brief window where both coasts are workable."),
            5: ("mixed", "Southwest monsoon starts - south and west wet, but Arugam Bay surf season opens."),
            6: ("mixed", "East coast (Arugam Bay, Trincomalee) excellent; south and west wet."),
            7: ("mixed", "East coast excellent; south and west wet."),
            8: ("mixed", "East coast excellent, peak surf; south and west wet."),
            9: ("mixed", "East coast still good; season winding down."),
            10: ("avoid", "Inter-monsoon - both coasts unsettled. The worst month to visit."),
            11: ("mixed", "Northeast monsoon on the east coast; south and west improving."),
            12: ("good", "South and west coasts good again; east shut."),
        },
    },
}

BAD_RATINGS = {"avoid"}


def normalise_month(value: str | int | None) -> int | None:
    """Accept 'July', 'jul', 7, '2026-07-14' and return a month number."""
    if value is None:
        return None
    if isinstance(value, int):
        return value if 1 <= value <= 12 else None
    text = str(value).strip().lower()
    if text.isdigit():
        number = int(text)
        return number if 1 <= number <= 12 else None
    if text in MONTHS:
        return MONTHS[text]
    # ISO-ish date
    parts = text.replace("/", "-").split("-")
    if len(parts) >= 2 and parts[0].isdigit() and parts[1].isdigit():
        number = int(parts[1])
        return number if 1 <= number <= 12 else None
    for name, number in MONTHS.items():
        if name in text:
            return number
    return None


def assess(destination: str, month: str | int | None) -> dict[str, Any]:
    """Return the seasonal verdict for a destination in a given month."""
    key = (destination or "").strip().lower()
    entry = CLIMATE_TABLE.get(key)
    if entry is None:
        # Candidates arrive at town granularity too. The table is keyed by
        # country, and an exact lookup silently returned "unknown" for
        # "Perhentian Islands, Malaysia" - throwing away a correct monsoon
        # warning for a country that is fully covered.
        resolved = resolve_country(key)
        if resolved:
            entry = CLIMATE_TABLE.get(resolved)
            if entry is not None:
                key = resolved
    if entry is None:
        return {
            "destination": destination,
            "known": False,
            "rating": "unknown",
            "note": f"No seasonal data held for {destination!r}.",
        }

    month_number = normalise_month(month)
    if month_number is None:
        return {
            "destination": key,
            "known": True,
            "rating": "unknown",
            "month": None,
            "note": "No travel month supplied - ask the user when they plan to travel.",
            "year_summary": entry["summary"],
        }

    rating, note = entry["months"][month_number]
    # Index MONTH_NAMES directly. A previous version reverse-searched MONTHS for a
    # name longer than three characters, which found nothing for May (its full
    # name IS three letters) and raised StopIteration inside the agent coroutine,
    # killing the Weather specialist for any May query. Caught by the eval suite.
    month_name = MONTH_NAMES[month_number - 1]
    return {
        "destination": key,
        "known": True,
        "month": month_name,
        "month_number": month_number,
        "rating": rating,
        "note": note,
        "year_summary": entry["summary"],
        "is_bad_season": rating in BAD_RATINGS,
    }
