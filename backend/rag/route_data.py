"""City-level backpacker route knowledge for the ``routes`` namespace.

The original seed corpus is country-level, which answers "Laos or Vietnam" but
not "where next from Chiang Mai". This holds the actual hop-by-hop circuit
knowledge: which places people go to next, how long the leg takes, and why you
would pick one over another.

Each document's ``destination`` metadata is the ORIGIN city, so a query scoped to
where the traveller is now retrieves the onward options from there.
"""
from __future__ import annotations

from typing import Any


def _route(
    origin: str,
    country: str,
    next_hops: list[str],
    text: str,
    region: str = "southeast asia",
) -> dict[str, Any]:
    return {
        "id": f"route-{origin.lower().replace(' ', '-')}",
        "text": text.strip(),
        "metadata": {
            "content_type": "routes",
            "destination": origin.lower(),
            "country": country.lower(),
            "region": region,
            "next_hops": [h.lower() for h in next_hops],
        },
    }


ROUTE_DOCS: list[dict[str, Any]] = [
    _route(
        "Chiang Mai", "Thailand", ["Pai", "Chiang Rai", "Mae Hong Son", "Bangkok", "Luang Prabang"],
        """
        Onward from Chiang Mai. The three standard moves: Pai (3h north by minibus,
        762 curves, around 150-200 THB - a small hippie town in a valley that people
        plan two nights in and leave a week later); Chiang Rai (3h by bus, ~150 THB,
        for the White Temple and as the staging post for the Laos border); or the Mae
        Hong Son loop, a 4-7 day motorbike circuit through Pai, Mae Hong Son and Mae
        Sariang that is the best riding in Thailand if you can already handle a bike.
        For leaving Thailand, Chiang Rai then Huay Xai puts you on the two-day Mekong
        slow boat to Luang Prabang. Going south, the overnight train or a cheap AirAsia
        hop to Bangkok. Do not ride to Pai if you have never ridden - the hospital in
        Pai treats a steady stream of foreigners with gravel rash from that road.
        """,
    ),
    _route(
        "Pai", "Thailand", ["Chiang Mai", "Mae Hong Son", "Chiang Rai"],
        """
        Onward from Pai. Most people backtrack to Chiang Mai (3h) because Pai is a
        dead end unless you continue the Mae Hong Son loop westward to Mae Hong Son
        town (4h, quieter, far fewer travellers, better for hill-tribe trekking).
        The loop then returns via Mae Sariang to Chiang Mai. Pai itself is a 2-4 day
        stop: the canyon at sunset, Pam Bok waterfall, the hot springs, and a walking
        street that is the whole nightlife scene. Budget 500-800 THB a day.
        """,
    ),
    _route(
        "Bangkok", "Thailand", ["Ayutthaya", "Kanchanaburi", "Chiang Mai", "Koh Tao", "Siem Reap"],
        """
        Onward from Bangkok. North: Ayutthaya is an easy 1.5h train day trip or
        overnight stop for the ruins by bicycle (20-80 THB by third-class train).
        West: Kanchanaburi, 3h, for the Death Railway, Erawan falls and cheap
        river-raft guesthouses. South: overnight bus-and-boat combos to Koh Tao for
        the cheapest open-water dive certification in the world, or Krabi and Koh
        Lanta on the Andaman side. Far north: overnight sleeper train to Chiang Mai,
        800-1,000 THB in second-class sleeper, which saves a night of accommodation.
        East: the 8-9h bus to Siem Reap via the Poipet border. Bangkok itself is
        worth 3 days, not more, unless you are waiting on a visa.
        """,
    ),
    _route(
        "Luang Prabang", "Laos", ["Vang Vieng", "Nong Khiaw", "Vientiane", "Huay Xai"],
        """
        Onward from Luang Prabang. The China-Laos high-speed railway has rewritten
        this: Vang Vieng is now under 2 hours by train instead of six by road, and
        Vientiane under 2 hours after that. Tickets sell out days ahead in peak
        season and are easiest bought through a guesthouse agent. North instead:
        Nong Khiaw, 3-4h by minibus, a river village between limestone karsts that is
        what Vang Vieng was 20 years ago, and onward by boat to Muang Ngoi which has
        no road at all. Most people spend 3 days in Luang Prabang and wish they had
        gone north rather than straight to Vang Vieng.
        """,
    ),
    _route(
        "Vang Vieng", "Laos", ["Vientiane", "Luang Prabang"],
        """
        Onward from Vang Vieng. Vientiane is under 2h by high-speed rail and is
        mostly a transit stop - a day for the COPE visitor centre, which is the most
        worthwhile thing in the capital, then out by bus to Thailand over the
        Friendship Bridge or south to the 4000 Islands. Vang Vieng itself has shifted
        from the old tubing scene to kayaking, the Blue Lagoons, caves and
        hot-air ballooning at sunrise; two nights is the usual stay.
        """,
    ),
    _route(
        "Hanoi", "Vietnam", ["Ha Giang", "Ninh Binh", "Sapa", "Cat Ba", "Phong Nha"],
        """
        Onward from Hanoi. The Ha Giang loop is the thing people name as the highlight
        of Vietnam: 3-4 days by motorbike through the far northern mountains, around
        USD 100-150 all in, and you can ride pillion with an "easy rider" driver if
        you cannot ride yourself. Ninh Binh (2h) is the inland version of Ha Long Bay
        by bicycle and rowboat, and is the better-value stop. Sapa (5-6h by bus or
        overnight train) for rice terraces, best June-September when they are green.
        Cat Ba island rather than a Ha Long Bay cruise if you want the karst scenery
        without the tour-boat crowd. Southward the standard next leg is the overnight
        train or sleeper bus to Phong Nha for the caves.
        """,
    ),
    _route(
        "Hoi An", "Vietnam", ["Hue", "Da Nang", "Da Lat", "Nha Trang", "Phong Nha"],
        """
        Onward from Hoi An. North: Hue (3-4h) over the Hai Van Pass, which is worth
        riding by motorbike or taking the train for the coastal views rather than the
        tunnel bus. Continue north to Phong Nha for the caves. South: Da Lat (long
        overnight bus, 12h+) for cool mountain air, canyoning and the best coffee in
        Vietnam, or Nha Trang for diving if you want the beach. Hoi An is a 3-4 day
        stop: the tailors, the old town lanterns, An Bang beach by bicycle, and a
        cooking class. Avoid September to November when the old town floods.
        """,
    ),
    _route(
        "Ho Chi Minh City", "Vietnam", ["Mekong Delta", "Mui Ne", "Da Lat", "Phnom Penh"],
        """
        Onward from Ho Chi Minh City. West: the Mekong Delta, either a rushed day trip
        to My Tho or, much better, two nights in Can Tho for the Cai Rang floating
        market at dawn. East: Mui Ne (5h) for the sand dunes and kitesurfing, then up
        to Da Lat. Across the border: Phnom Penh is an easy 6-7h bus for USD 12-18
        through the Bavet/Moc Bai crossing, one of the smoothest land borders in the
        region, with the bus company handling the paperwork. Saigon itself is 2-3
        days: the War Remnants Museum, the Cu Chi tunnels as a half-day, and street
        food in District 4.
        """,
    ),
    _route(
        "Siem Reap", "Cambodia", ["Battambang", "Phnom Penh", "Bangkok", "Koh Rong"],
        """
        Onward from Siem Reap. Battambang (3-4h) is the underrated stop - the bamboo
        train, colonial shophouses, a genuine circus school, and a fraction of the
        tourism. Phnom Penh is 6h by bus. Back to Thailand is 8-9h to Bangkok through
        Poipet, where officials routinely ask for extra "processing fees". If you are
        heading for the islands, it is Phnom Penh then Sihanoukville then the boat to
        Koh Rong Sanloem. Siem Reap is a 3-4 day stop: buy the three-day Angkor pass
        at USD 62 and spread it across a week, sunrise at Angkor Wat then the outer
        temples in the afternoon when the buses have gone.
        """,
    ),
    _route(
        "Phnom Penh", "Cambodia", ["Kampot", "Kep", "Sihanoukville", "Siem Reap", "Ho Chi Minh City"],
        """
        Onward from Phnom Penh. South: Kampot (4h) is the stop travellers most often
        say they wish they had given more time - riverside bungalows, the Bokor
        mountain road, pepper farms, and a slow pace that suits long-stay budgets.
        Kep is an hour further for crab market and Rabbit Island. Sihanoukville has
        been transformed by casino construction and most backpackers now transit
        straight through to the boat for Koh Rong Sanloem, the quieter of the two
        islands. North: Siem Reap 6h. East: Ho Chi Minh City 6-7h.
        """,
    ),
    _route(
        "Ubud", "Indonesia", ["Canggu", "Nusa Penida", "Gili Islands", "Amed", "Yogyakarta"],
        """
        Onward from Ubud. Canggu (1.5h) for the surf and long-stay hostel scene.
        Nusa Penida (fast boat from Sanur, 45min) for Kelingking beach, best as an
        overnight rather than a day trip because the day tours are a scrum. The Gili
        Islands (2-3h boat) for cheap diving - Trawangan for the party, Air for the
        balance, Meno for quiet. Amed on the east coast for the USAT Liberty wreck
        dive, which is shore-accessible and one of the best cheap dives in Asia.
        Further: a flight to Yogyakarta on Java for Borobudur, Prambanan and the
        Bromo-Ijen volcano pairing.
        """,
    ),
    _route(
        "Kuala Lumpur", "Malaysia", ["Penang", "Cameron Highlands", "Taman Negara", "Melaka", "Singapore"],
        """
        Onward from Kuala Lumpur. Penang (4-5h bus or 1h flight) for George Town
        street art and the best-value hawker food in the region. Cameron Highlands
        (4h) for tea plantations and cool air, a useful break from the heat. Taman
        Negara (3-4h) for accessible rainforest and the canopy walkway. Melaka (2h)
        for a weekend of Peranakan architecture. South: Singapore is 5h by bus but
        expensive enough that most backpackers transit rather than linger.
        """,
    ),
    _route(
        "Penang", "Malaysia", ["Langkawi", "Kuala Lumpur", "Perhentian Islands", "Krabi"],
        """
        Onward from Penang. Langkawi (2.75h ferry) for duty-free and island hopping.
        The Perhentians are across on the east coast and only worth it March to
        October - November to February they effectively close. North into Thailand:
        minivans run to Hat Yai in 4-5h and on to Krabi, which is also why Penang is
        the classic visa-run destination for long Thailand stays. Penang itself is
        3 days: George Town on foot, the clan jetties, Kek Lok Si temple and Penang
        Hill.
        """,
    ),
    _route(
        "El Nido", "Philippines", ["Coron", "Port Barton", "Siargao", "Cebu"],
        """
        Onward from El Nido. Coron (3.5-4h fast ferry, around PHP 1,800) for wreck
        diving on the Japanese fleet, which is world class and cheap. Port Barton
        (2-3h van) is the quieter, cheaper version of El Nido that people wish they
        had gone to first. Further afield: fly via Manila or Cebu to Siargao for
        surfing and the cheapest long-stay scene in the country. Budget for flights
        rather than assuming overland - there is no cheap alternative between
        islands, and typhoon season from August to October cancels boats at short
        notice.
        """,
    ),
    _route(
        "Kathmandu", "Nepal", ["Pokhara", "Chitwan", "Annapurna Base Camp", "Everest Base Camp"],
        """
        Onward from Kathmandu. Pokhara (6-7h bus or 25min flight) is the trailhead
        town for the Annapurna treks and a pleasant lakeside stop in its own right.
        From Pokhara: Poon Hill (4-5 days, the accessible classic), Annapurna Base
        Camp (7-12 days), or the Annapurna Circuit. Everest Base Camp (12-14 days)
        starts with the Lukla flight, which is weather-dependent and regularly
        delayed - build buffer days or you will miss an onward international flight.
        Chitwan (5h) for rhinos and elephants if you want a break from altitude.
        Rent your down jacket and sleeping bag in Thamel for a couple of dollars a
        day rather than carrying your own across Asia.
        """,
        region="south asia",
    ),
    _route(
        "Ella", "Sri Lanka", ["Arugam Bay", "Mirissa", "Kandy", "Nuwara Eliya"],
        """
        Onward from Ella. East: Arugam Bay (4-5h) for surf, in season May to
        September only. South: Mirissa and the south coast beaches (4h), good
        December to March, with whale watching November to April. North: Kandy via
        the famous hill-country train, which is the single best cheap experience in
        the country - book a reserved second-class seat a few days ahead, or ride
        third class unreserved and stand in the doorway. Ella itself is 2-3 days:
        Little Adam's Peak, Ella Rock, the Nine Arches Bridge and a tea factory tour.
        """,
        region="south asia",
    ),
]

# origin city -> known onward hops, used by the discovery tool as a fallback when
# retrieval is unavailable, and by the city detector below.
ROUTE_GRAPH: dict[str, list[str]] = {
    doc["metadata"]["destination"]: doc["metadata"]["next_hops"] for doc in ROUTE_DOCS
}

CITY_TO_COUNTRY: dict[str, str] = {
    doc["metadata"]["destination"]: doc["metadata"]["country"] for doc in ROUTE_DOCS
}

# Cities that appear only as onward hops still need to be recognisable.
EXTRA_CITIES: dict[str, str] = {
    "chiang rai": "thailand", "mae hong son": "thailand", "ayutthaya": "thailand",
    "andaman coast": "thailand", "gulf islands": "thailand", "koh phi phi": "thailand",
    "kanchanaburi": "thailand", "koh tao": "thailand", "koh lanta": "thailand",
    "krabi": "thailand", "koh phangan": "thailand", "koh samui": "thailand",
    "phuket": "thailand", "hua hin": "thailand", "koh chang": "thailand",
    "vientiane": "laos", "nong khiaw": "laos", "huay xai": "laos",
    "muang ngoi": "laos", "4000 islands": "laos", "pakse": "laos",
    "sapa": "vietnam", "ha giang": "vietnam", "ninh binh": "vietnam",
    "cat ba": "vietnam", "phong nha": "vietnam", "hue": "vietnam",
    "da nang": "vietnam", "da lat": "vietnam", "nha trang": "vietnam",
    "mui ne": "vietnam", "mekong delta": "vietnam", "can tho": "vietnam",
    "angkor": "cambodia", "angkor wat": "cambodia",
    "battambang": "cambodia", "kampot": "cambodia", "kep": "cambodia",
    "sihanoukville": "cambodia", "koh rong": "cambodia", "koh rong sanloem": "cambodia",
    "bali": "indonesia", "java": "indonesia", "sumatra": "indonesia",
    "canggu": "indonesia", "nusa penida": "indonesia", "gili islands": "indonesia",
    "gili trawangan": "indonesia", "gili air": "indonesia", "amed": "indonesia",
    "yogyakarta": "indonesia", "lombok": "indonesia", "seminyak": "indonesia",
    "borneo": "malaysia", "george town": "malaysia",
    "cameron highlands": "malaysia", "taman negara": "malaysia", "melaka": "malaysia",
    "langkawi": "malaysia", "perhentian islands": "malaysia", "kota kinabalu": "malaysia",
    "coron": "philippines", "port barton": "philippines", "siargao": "philippines",
    "cebu": "philippines", "moalboal": "philippines", "manila": "philippines",
    "pokhara": "nepal", "chitwan": "nepal", "annapurna base camp": "nepal",
    "everest base camp": "nepal", "nagarkot": "nepal",
    "arugam bay": "sri lanka", "mirissa": "sri lanka", "kandy": "sri lanka",
    "nuwara eliya": "sri lanka", "sigiriya": "sri lanka", "unawatuna": "sri lanka",
    "galle": "sri lanka", "colombo": "sri lanka",
}

KNOWN_CITIES: dict[str, str] = {**CITY_TO_COUNTRY, **EXTRA_CITIES}

COUNTRIES: set[str] = set(KNOWN_CITIES.values())


def resolve_country(location: str | None) -> str | None:
    """Map any free-form place string to the country it belongs to.

    Handles country names, known towns, and compound strings like
    "Perhentian Islands, Malaysia" or "Bali, Indonesia".

    This exists because the climate table and the route table are keyed by
    COUNTRY, while candidates now arrive at town granularity. An exact lookup
    silently returned "unknown" for "Perhentian Islands, Malaysia", which threw
    away a correct monsoon warning for a country that is fully covered.
    """
    key = (location or "").strip().lower()
    if not key:
        return None
    if key in COUNTRIES:
        return key
    if key in KNOWN_CITIES:
        return KNOWN_CITIES[key]

    # Compound strings: try each comma- or slash-separated part.
    for part in (p.strip() for p in key.replace("/", ",").split(",")):
        if part in COUNTRIES:
            return part
        if part in KNOWN_CITIES:
            return KNOWN_CITIES[part]

    # Last resort: a country or town name embedded in a longer phrase.
    for country in COUNTRIES:
        if country in key:
            return country
    for city, country in KNOWN_CITIES.items():
        if city in key:
            return country
    return None

