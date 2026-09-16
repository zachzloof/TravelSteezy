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
        940-1,200 THB in second-class sleeper, which saves a night of accommodation.
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
        USD 250-350 all in with an "easy rider" driver if you cannot ride yourself (a
        Border Area Entry Permit, around USD 10, has been required since June 2026 -
        your driver or homestay arranges it). Ninh Binh (2h) is the inland version of
        Ha Long Bay by bicycle and rowboat, and is the better-value stop. Sapa (5-6h by
        bus or overnight train) for rice terraces, best June-August when green or
        September to mid-October for the golden harvest.
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
        to Da Lat. Across the border: Phnom Penh is an easy 6-7h bus for USD 20-27
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
        tourism. Phnom Penh is 6h by bus. Back to Thailand: the Poipet land border has
        been closed since mid-2025 due to an armed border conflict with no reopening date
        as of late 2026 - fly Siem Reap-Bangkok (around 1h) instead and check current
        border status before planning any overland route. If you are heading for the
        islands, it is Phnom Penh then Sihanoukville then the boat to
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
        Onward from El Nido. Coron (3.5-4h fast ferry, roughly PHP 2,750-3,250 depending
        on operator, more in peak season) for wreck
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
        Onward from Ella. East: Arugam Bay (4-5h) for surf, in season April to
        October, best waves June-August. South: Mirissa and the south coast beaches (4h), good
        December to March, with whale watching November to April. North: Kandy via
        the famous hill-country train, which is the single best cheap experience in
        the country - book a reserved second-class seat a few days ahead, or ride
        third class unreserved and stand in the doorway. Ella itself is 2-3 days:
        Little Adam's Peak, Ella Rock, the Nine Arches Bridge and a tea factory tour.
        """,
        region="south asia",
    ),
    _route(
        "Vientiane", "Laos", ["Vang Vieng", "Luang Prabang", "4000 Islands", "Bangkok"],
        """
        Onward from Vientiane. The high-speed rail makes Vang Vieng under 1h and Luang
        Prabang under 2h, a total inversion of the old 6-10h bus reality - book a few
        days ahead in peak season since tickets sell out. South: the slow, quiet 4000
        Islands (Si Phan Don) is 8-9h by bus, worth it only if you have the days to
        spare for hammock time on Don Det. West: the Friendship Bridge crossing to
        Nong Khai, Thailand puts you on an overnight train to Bangkok. Vientiane
        itself is a 1-2 day stop, not more: the COPE Visitor Centre (unexploded
        ordnance history, genuinely the most worthwhile thing in the capital), Patuxai
        arch, and the night market along the Mekong.
        """,
    ),
    _route(
        "Nong Khiaw", "Laos", ["Muang Ngoi", "Luang Prabang", "Vieng Xai"],
        """
        Onward from Nong Khiaw. Muang Ngoi is a 1h boat with no road access at all -
        genuinely one of the few places left on this circuit reachable only by river,
        worth 2-3 days of doing very little. Back to Luang Prabang is 3-4h by minibus.
        East, for the committed: Vieng Xai's cave complex (the hidden Pathet Lao
        wartime headquarters) is a full day further and rarely visited, which is
        exactly its appeal. Nong Khiaw itself is 2 days: the viewpoint hike above town
        for sunrise over the limestone karsts, and kayaking the Nam Ou river.
        """,
    ),
    _route(
        "Da Lat", "Vietnam", ["Nha Trang", "Mui Ne", "Ho Chi Minh City", "Hoi An"],
        """
        Onward from Da Lat. Nha Trang (4h) for diving and beach after the mountain air.
        Mui Ne (4h) for the sand dunes and kitesurfing. Ho Chi Minh City is a long
        7-8h bus, usually overnight. North back to Hoi An is a full day either way -
        most people fly this leg rather than bus it. Da Lat itself is 2-3 days:
        canyoning (abseiling down real waterfalls, one of the best budget adventure
        activities in Vietnam), the Crazy House, and the best coffee-growing region in
        the country - do a farm tour, not just a cafe.
        """,
    ),
    _route(
        "Hue", "Vietnam", ["Phong Nha", "Hoi An", "Hanoi"],
        """
        Onward from Hue. South over the Hai Van Pass to Hoi An (3-4h) - ride it by
        motorbike or take the train for the coastal views rather than the tunnel bus,
        which misses the entire point of the route. North to Phong Nha (4-5h) for the
        caves. Hanoi is a long haul (12h+ by train or bus, or a short cheap flight).
        Hue itself is 2 days: the Imperial Citadel, the royal tombs by bicycle or
        scooter along the Perfume River, and bun bo Hue, the city's own noodle soup,
        worth seeking out specifically rather than settling for pho everywhere.
        """,
    ),
    _route(
        "Sihanoukville", "Cambodia", ["Koh Rong", "Koh Rong Sanloem", "Kampot", "Phnom Penh"],
        """
        Onward from Sihanoukville - now mostly a transit point rather than a
        destination, following heavy casino-driven construction that changed the
        town's character. Most backpackers pass straight through to the pier for boats
        to Koh Rong (party hostels, beach bars) or the quieter Koh Rong Sanloem (Lazy
        Beach, Sunset Beach - the calmer choice). Kampot is 2-3h and the town most
        people wish they'd gone to instead. Phnom Penh is 4h. If sleeping in
        Sihanoukville itself is unavoidable between a bus and a boat, treat it as a
        one-night logistics stop, not a stay.
        """,
    ),
    _route(
        "Kampot", "Cambodia", ["Kep", "Sihanoukville", "Phnom Penh"],
        """
        Onward from Kampot. Kep is a quick 25-30min tuk-tuk for the crab market and
        Rabbit Island day trip. Sihanoukville (for the island boats) is 2-3h.
        Phnom Penh is 3h. Kampot itself rewards slow travel more than almost anywhere
        else on the Cambodia circuit: riverside bungalows, sunset boat cruises, the
        Bokor Mountain day trip (an eerie abandoned French hill-station casino), and
        pepper farm tours - Kampot pepper is genuinely internationally known and the
        farms welcome visitors. Budget travellers who plan 2 days here often stay a
        week.
        """,
    ),
    _route(
        "Sapa", "Vietnam", ["Ha Giang", "Hanoi"],
        """
        Onward from Sapa. Most people arrive already having done, or planning next, the
        Ha Giang loop (a separate 5-6h transfer, not a direct Sapa-Ha Giang road) - the
        two are often confused as one region but require their own separate trip
        planning. Back to Hanoi is 5-6h by bus or the overnight sleeper train from
        nearby Lao Cai, which is the more comfortable option and saves a night's
        accommodation. The Lao Cai border crossing into Yunnan, China exists but
        requires arranging a Chinese visa well in advance - not a spontaneous option.
        Sapa itself is 2-3 days: a homestay trek through the rice terraces (best
        June-August when green, or September to mid-October for the golden harvest)
        with a local guide from one of the H'mong or Dao villages.
        """,
    ),
    _route(
        "Coron", "Philippines", ["El Nido", "Manila", "Cebu"],
        """
        Onward from Coron. El Nido is a rough, memorable 3.5-4h fast ferry (rougher in
        the Aug-Oct typhoon-risk window - check forecasts, cancellations happen at
        short notice). Manila is a short flight; there is no practical overland or
        long-ferry option worth taking. Onward to the Visayas (Cebu, Bohol, Siargao)
        also means flying via Manila or Cebu, since there is no direct inter-island
        boat network covering this distance. Coron itself is 3-4 days: the wreck
        diving on the sunken WWII Japanese fleet (world class and comparatively cheap),
        Kayangan Lake, and Twin Lagoon.
        """,
    ),
    _route(
        "Siargao", "Philippines", ["Cebu", "Manila", "Bohol"],
        """
        Onward from Siargao. Cebu is the usual flight connection (around 1h) for
        onward domestic or international travel. Manila direct flights also run.
        Bohol (for the Chocolate Hills and tarsier sanctuary) is reachable via a
        Cebu connection, not directly. Siargao itself rewards a longer stay than most
        backpackers budget: Cloud 9 for the surf (best Aug-Nov swell season), island-
        hopping to Naked Island and Guyam, and a genuinely strong long-stay digital-
        nomad-adjacent hostel scene that has grown fast in recent years - book
        accommodation further ahead than elsewhere in the Philippines during peak
        surf season.
        """,
    ),
    _route(
        "Canggu", "Indonesia", ["Ubud", "Uluwatu", "Nusa Penida", "Yogyakarta"],
        """
        Onward from Canggu. Ubud is 45min-1h inland for the cultural/rice-terrace
        contrast to Canggu's surf-cafe scene. Uluwatu (45min) for the cliff-top surf
        breaks and sunset temple. Nusa Penida is a 45min fast boat from Sanur (30min
        further from Canggu) for Kelingking Beach - go early or stay overnight to beat
        the day-tour crowds. Further out, Yogyakarta on Java is a flight away for
        Borobudur and the Bromo-Ijen volcano circuit. Canggu itself is where long-stay
        backpackers and remote workers actually settle rather than pass through - the
        coworking-cafe scene here is the strongest on the whole SE Asia circuit.
        """,
    ),
    _route(
        "Gili Trawangan", "Indonesia", ["Gili Air", "Gili Meno", "Lombok", "Bali"],
        """
        Onward from Gili Trawangan. Gili Air and Gili Meno are both a short, cheap
        public boat away (15-20min) if the party atmosphere on "Gili T" isn't the
        goal - Air for a middle-ground social scene, Meno for genuine quiet. Lombok's
        mainland (for Mount Rinjani trekking, a serious multi-day volcano climb) is a
        short boat plus onward transfer. Back to Bali is a 1.5-2h fast boat to
        Padang Bai or Sanur. No cars or motorbikes are allowed on any of the three
        Gilis - getting around is on foot, bicycle, horse-cart (cidomo), or increasingly
        a rented electric bike/scooter (no license needed, around IDR 250,000-350,000/day),
        which is
        part of the appeal, not an inconvenience.
        """,
    ),
    _route(
        "Pokhara", "Nepal", ["Kathmandu", "Annapurna Base Camp", "Poon Hill", "Chitwan"],
        """
        Onward from Pokhara, the trailhead town for the Annapurna region. Poon Hill
        (4-5 days) is the accessible classic trek for a first-timer. Annapurna Base
        Camp (7-12 days) is the step up. The full Annapurna Circuit is 12-18 days for
        those with the time. Back to Kathmandu is 6-7h by bus or a 25min flight -
        worth the flight cost if a trek has already eaten most of the trip's days.
        South: Chitwan (4-5h) for rhinos and elephants, a good low-altitude break
        either before or after trekking. Pokhara itself, lakeside, is worth 2-3 days
        even without a trek attached - paragliding here is some of the cheapest and
        most scenic in the world.
        """,
    ),
    _route(
        "Kandy", "Sri Lanka", ["Ella", "Nuwara Eliya", "Sigiriya", "Colombo"],
        """
        Onward from Kandy. The hill-country train to Ella (via Nuwara Eliya) is the
        single best cheap experience in the country - book a reserved second-class
        seat days ahead, or ride third class unreserved and stand in the doorway for
        the views anyway. Sigiriya (2-3h) for the rock fortress, or the cheaper
        Pidurangala directly opposite for a better view of Sigiriya itself. Colombo
        is 3h for international flight connections. Kandy itself is 2 days: the
        Temple of the Tooth, the botanical gardens at Peradeniya, and a cultural dance
        show in the evening.
        """,
    ),
    _route(
        "Battambang", "Cambodia", ["Siem Reap", "Phnom Penh", "Poipet Thailand border"],
        """
        Onward from Battambang, the underrated stop most SE Asia itineraries skip.
        Siem Reap is 3-4h. Phnom Penh is 5-6h. The Poipet land border to Thailand has
        been closed since mid-2025 due to an armed border conflict with no reopening
        date as of late 2026 - fly out via Siem Reap or Phnom Penh instead and check
        current border status before planning any overland route west.
        Battambang itself is 2 days: the bamboo train (a genuinely fun, slightly
        absurd homemade rail-cart ride), well-preserved French colonial shophouses,
        and Phare Ponleu Selpak, a real circus school with evening performances - a
        fraction of the crowds Siem Reap gets for a comparable amount to see and do.
        """,
    ),
    _route(
        "Langkawi", "Malaysia", ["Penang", "Koh Lipe Thailand", "Kuala Lumpur"],
        """
        Onward from Langkawi. Penang is a 2.75h ferry. North across the maritime
        border, Koh Lipe (Thailand) is reachable by speedboat in the Nov-Apr dry
        season only - a genuine way to island-hop between the two countries without
        flying, but boats stop running outside that window. Kuala Lumpur is a short,
        cheap flight. Langkawi itself is duty-free (worth stocking up on alcohol and
        chocolate before leaving Malaysia), with the cable car up Mount Machincang and
        island-hopping to the mangroves and Pulau Dayang Bunting as the standard
        2-3 day itinerary.
        """,
    ),
    _route(
        "Delhi", "India", ["Agra", "Jaipur", "Rishikesh", "Varanasi", "Amritsar"],
        """
        Onward from Delhi, the usual arrival and hub city for a first India trip. Agra
        (3-4h by road, 2h by the Gatimaan Express train) for the Taj Mahal - go for
        sunrise, both for the light and to beat the heat and crowds. Jaipur (4-5h) to
        start the Rajasthan loop. Rishikesh (6-7h by road or an overnight train plus
        transfer) for yoga and the Ganges. Varanasi is best reached by overnight
        sleeper train (12h+) rather than the long day-bus. Amritsar (6h by train) for
        the Golden Temple. Delhi itself is worth 2-3 days despite the instinct to
        rush through it: Old Delhi's street food and Jama Masjid, Humayun's Tomb, and
        using the metro rather than taxis for anywhere it reaches.
        """,
        region="south asia",
    ),
    _route(
        "Rishikesh", "India", ["Delhi", "Dharamshala/McLeod Ganj", "Haridwar"],
        """
        Onward from Rishikesh. Delhi is 6-7h by road or bus-plus-train combination.
        North to Dharamshala/McLeod Ganj (the Dalai Lama's residence-in-exile, and the
        gateway to Himachal trekking around Kasol and Tosh) is 8-10h by bus - budget a
        full day. Haridwar, 45min away, is worth a half-day trip for the evening
        Ganga Aarti ceremony if Rishikesh's own version feels too touristic. Rishikesh
        itself is 3-5 days: yoga and meditation courses of every price point and
        seriousness level, the suspension bridges (Laxman Jhula, Ram Jhula), and
        white-water rafting on the Ganges (Sep-Jun, not during the monsoon).
        """,
        region="south asia",
    ),
    _route(
        "Varanasi", "India", ["Delhi", "Bodh Gaya", "Kolkata"],
        """
        Onward from Varanasi. Delhi is best reached by overnight sleeper train.
        Bodh Gaya (4-5h), the site of the Buddha's enlightenment, is a worthwhile
        detour for anyone with even a passing interest in Buddhism, and gets far
        fewer Western backpackers than the ghats. Kolkata is a further 10-12h by
        train. Varanasi itself is 2-3 days: sunrise boat rides on the Ganges past the
        ghats, the nightly Ganga Aarti fire ceremony at Dashashwamedh Ghat, and
        walking the old city's lanes - widely described by backpackers as the single
        most intense sensory experience on the India circuit, in both directions.
        """,
        region="south asia",
    ),
    _route(
        "Goa", "India", ["Hampi", "Mumbai", "Gokarna"],
        """
        Onward from Goa. Hampi is an overnight sleeper bus or train (8-10h) - the
        standard way backpackers link Goa's beaches to Karnataka's ruins. Mumbai is
        8-12h by train or a short cheap flight. South along the coast, Gokarna
        (4-5h) is the smaller, less-developed alternative to Goa's more commercial
        beaches, popular with backpackers wanting the same coastal vibe with fewer
        package tourists. Goa itself splits north (Anjuna, Arambol - backpacker
        hostels, flea markets, trance-party history) from south (Palolem, Agonda -
        quieter, more family and long-stay oriented); most beach shacks and much of
        the tourism infrastructure closes entirely June-September for the monsoon.
        """,
        region="south asia",
    ),
    _route(
        "Jaisalmer", "India", ["Jodhpur", "Udaipur", "Jaipur"],
        """
        Onward from Jaisalmer, the desert-edge fort town and usual end point of the
        Rajasthan loop. Jodhpur (5-6h) for the Blue City and Mehrangarh Fort. Udaipur
        (7-8h) for the lake palaces. Jaipur is a long day (10-12h) - most people break
        the journey at Jodhpur rather than doing it direct. Jaisalmer itself is the
        base for an overnight camel safari into the Thar Desert dunes, the main
        reason most backpackers come this far west - book through a guesthouse with
        recent reviews specifically for the safari, since quality varies enormously
        and this is one of the more commonly complained-about tourist experiences in
        Rajasthan when done cheaply and carelessly.
        """,
        region="south asia",
    ),
    _route(
        "Hampi", "India", ["Goa", "Mumbai", "Bengaluru"],
        """
        Onward from Hampi. Goa is an overnight sleeper bus or train (8-10h), the
        classic pairing of ruins and beach. Bengaluru (6-8h) for onward flights
        anywhere in India or internationally. Mumbai is a longer haul, usually an
        overnight train. Hampi itself is 2-3 days exploring the boulder-strewn ruins
        of the Vijayanagara Empire by rented bicycle or scooter, with sunset from
        Matanga Hill or Hemakuta Hill as the standard end to a day - alcohol is
        officially banned in the core heritage zone, unlike almost anywhere else on
        the backpacker circuit.
        """,
        region="south asia",
    ),
    _route(
        "Jaipur", "India", ["Delhi", "Pushkar", "Udaipur", "Jaisalmer"],
        """
        Onward from Jaipur, the Pink City and second stop on the Golden Triangle.
        Delhi is 4-5h back the way you came. Pushkar (3-4h) is a small, sacred lake
        town and easy detour, especially lively during its November camel fair.
        Udaipur (6-7h) and Jaisalmer (10-12h, break at Jodhpur) continue the
        Rajasthan loop west. Jaipur itself is 2-3 days: Amber Fort (arrive early to
        avoid both heat and crowds), the City Palace, Hawa Mahal from the street
        outside at sunrise, and the old city's bazaars for block-printed textiles and
        semi-precious stones - haggle hard, opening prices are routinely 3-4x fair
        value.
        """,
        region="south asia",
    ),
    _route(
        "Udaipur", "India", ["Jaipur", "Jaisalmer", "Mumbai"],
        """
        Onward from Udaipur, the "City of Lakes" and usual highlight of a Rajasthan
        loop. Jaipur is 6-7h back east. Jaisalmer continues the loop west (7-8h).
        Mumbai is 10-12h by train or a short flight if the trip is turning south
        toward Goa. Udaipur itself is 2-3 days: Lake Pichola by boat at sunset, the
        City Palace complex, and a rooftop restaurant looking over the lake - this is
        also where a genuine splurge (a single night at a heritage lake-facing
        guesthouse) is most often worth breaking a shoestring budget for, by
        widespread backpacker consensus.
        """,
        region="south asia",
    ),
    _route(
        "Amritsar", "India", ["Delhi", "Dharamshala/McLeod Ganj"],
        """
        Onward from Amritsar. Delhi is 6h by train. Dharamshala/McLeod Ganj is 8-9h
        by bus, the usual next stop for anyone heading into Himachal. The India-
        Pakistan Wagah Border ceremony (a genuinely theatrical, over-the-top nightly
        flag-lowering with crowds cheering both sides) is a worthwhile half-day trip
        from town and needs no special arrangement beyond turning up early for a seat.
        Amritsar itself is the Golden Temple: visit at dawn or late evening to avoid
        the worst crowds, cover your head, and eat at the free langar community
        kitchen, which feeds tens of thousands daily regardless of religion or means -
        one of the most striking things to witness on the entire subcontinent.
        """,
        region="south asia",
    ),
    _route(
        "Mumbai", "India", ["Goa", "Hampi", "Udaipur"],
        """
        Onward from Mumbai, usually the international arrival/departure gateway for
        the south and west of the country rather than a hub backpackers linger in
        long. Goa is an overnight train or a short cheap flight. Hampi is a longer
        overnight train. Udaipur is 10-12h north if starting the Rajasthan loop from
        here instead of Delhi. Mumbai itself is worth 2 days: the Gateway of India and
        a ferry to Elephanta Caves, Colaba's markets, and Marine Drive at sunset - most
        backpackers use it as a short bookend rather than a base, given the cost of
        accommodation is noticeably higher here than almost anywhere else in India.
        """,
        region="south asia",
    ),
    _route(
        "Yangon", "Myanmar", ["Bagan", "Mandalay", "Inle Lake"],
        """
        Onward from Yangon. Bagan is a 1h flight or a punishing 9-10h overnight bus -
        most backpackers fly this leg. Mandalay is similarly a short flight or a long
        bus. Inle Lake is reached via Heho airport (flight) or a long bus plus local
        transfer. Overland options and timings shift with the security situation (see
        the visa document's safety note) more than in any neighbouring country, so
        confirm current road status locally rather than assuming a route is open.
        Yangon itself is 2 days: Shwedagon Pagoda at sunset (the single most
        recommended thing to do in the country), the colonial downtown core, and
        Kyaiktiyo (Golden Rock) as a long but doable day trip.
        """,
    ),
    _route(
        "Bagan", "Myanmar", ["Mandalay", "Inle Lake", "Yangon"],
        """
        Onward from Bagan. Mandalay is a short flight or a 4-5h bus/boat. Inle Lake is
        a flight via Heho or a long bus. Yangon is a 1h flight or a long overnight
        bus. Bagan itself is 2-3 days: renting an e-bike to explore the thousands of
        temples scattered across the plain at your own pace, sunrise or sunset from
        one of the designated viewing mounds (climbing the temples themselves is now
        restricted at most sites to protect them), and a hot-air balloon flight at
        dawn - expensive by regional standards but consistently named a trip highlight
        by those who do it.
        """,
    ),
    _route(
        "Inle Lake", "Myanmar", ["Kalaw", "Mandalay", "Yangon"],
        """
        Onward from Inle Lake. Kalaw is best done in reverse as a 2-3 day trek INTO
        Inle rather than as an onward leg, but the same route runs both ways.
        Mandalay and Yangon are both a flight from Heho airport or a long bus. Inle
        Lake itself is 2-3 days: a full-day boat tour of the floating gardens and
        stilt villages, watching the lake's distinctive leg-rowing fishermen, and
        visiting the workshops (weaving, silversmithing, cigar-rolling) built directly
        over the water.
        """,
    ),
    _route(
        "Mandalay", "Myanmar", ["Bagan", "Inle Lake", "Hsipaw"],
        """
        Onward from Mandalay. Bagan is a short flight or a 4-5h bus/boat down the
        Irrawaddy. Inle Lake is a flight or long bus via Heho. Hsipaw, reached by a
        scenic train ride across the Gokteik Viaduct, is the trekking-and-hill-tribe
        alternative to Kalaw for those who've already done the Inle approach - but unlike
        the rest of this circuit, Hsipaw and Kyaukme sit in northern Shan State, which the
        UK FCDO currently advises against ALL travel to (the most severe tier, not the
        "all but essential" tier covering Mandalay/Bagan/Inle) due to active conflict; the
        train itself still runs, but check current advisories carefully before treating
        this as a normal add-on. Mandalay
        itself is 2 days: the U Bein teak bridge at sunset (the longest teak footbridge
        in the world), Mandalay Hill for a panorama, and day trips to the nearby former
        royal capitals of Amarapura, Sagaing and Inwa.
        """,
    ),
    _route(
        "Kalaw", "Myanmar", ["Inle Lake", "Mandalay"],
        """
        Onward from Kalaw. The main reason to be here at all is the 2-3 day trek to
        Inle Lake through hill-tribe villages and tea plantations, considered one of
        the best budget trekking experiences in the country - arrange a guide in town
        rather than pre-booking from Yangon, since local guides know current trail and
        security conditions best. Mandalay is a separate bus connection if skipping
        the trek. Kalaw itself, at a cooler hill-station altitude, is worth a day
        before setting off: colonial-era architecture and a genuinely different pace
        from the lowland heat.
        """,
    ),
    _route(
        "Ulaanbaatar", "Mongolia", ["Gobi Desert", "Terelj National Park", "Lake Khovsgol"],
        """
        Onward from Ulaanbaatar, the near-universal starting point since almost all
        international flights land here and there is no meaningful backpacker route
        that doesn't start with arranging a driver-guide from the capital. Terelj
        National Park (1.5-2h) is the easy, accessible taste of the steppe and
        ger-camp experience if time is short. The Gobi Desert (Khongoryn Els sand
        dunes, the Flaming Cliffs) is typically a 4-7 day round-trip jeep tour,
        booked as a shared group through a hostel to split the cost. Lake Khovsgol in
        the far north is a further, longer trip (7+ days round-trip) and the least
        accessible of the three without significant time to spare. Ulaanbaatar itself
        is 1-2 days: the Gandantegchinlen Monastery, the Chinggis Khaan statue complex
        outside town, and the Naran Tuul ("Black Market") for cashmere.
        """,
        region="east asia",
    ),
    _route(
        "Sydney", "Australia", ["Blue Mountains", "Byron Bay", "Melbourne", "Cairns"],
        """
        Onward from Sydney, the usual arrival point and start of the east coast run. The Blue
        Mountains (Katoomba) are an easy day trip - about 2h by train from Central Station - for
        the Three Sisters lookout at Echo Point, Scenic World's cable car and the world's steepest
        railway. North up the coast: Byron Bay is a long day's drive or bus (around 10-11h) or a
        short flight via Ballina/Gold Coast airports - most people break the trip at Port
        Macquarie or Coffs Harbour. South: Melbourne is 12h by overnight train or coach, or a
        cheap 1.5h flight, and is the other end of the classic Great Ocean Road detour. Sydney
        itself rewards 3-4 days: the Bondi-to-Coogee coastal walk (free), the Opera House and
        Harbour Bridge from Circular Quay, and the ferry to Manly, one of the best-value harbour
        views in the city for the price of a regular transit ticket.
        """,
        region="oceania",
    ),
    _route(
        "Cairns", "Australia", ["Whitsundays", "Byron Bay", "Sydney", "Great Barrier Reef"],
        """
        Onward from Cairns, the usual starting point for a north-to-south east coast run. South by
        bus or campervan to Airlie Beach and the Whitsundays (about 15-17h direct, most people
        break the trip at Townsville or Mission Beach) for a 2-3 day sailing trip through the
        islands. Continuing south it's a multi-day hop via Brisbane and the Gold Coast to Byron
        Bay and eventually Sydney - a full Cairns-Sydney run by bus/campervan realistically takes
        2-3 weeks done properly, or a Greyhound "Whimit" hop-on-hop-off pass covers the whole leg
        for around AUD 289 with no fixed schedule. Cairns itself is 3-4 days: a Great Barrier Reef
        day trip (AUD 220-350 for a full-day outer-reef boat) for snorkelling or diving, the
        Daintree Rainforest and Cape Tribulation as a long day trip, and the Kuranda Scenic
        Railway plus Skyrail cable car loop. Stick to patrolled, stinger-netted swimming spots
        November to May - this is genuine box jellyfish territory, not a generic warning.
        """,
        region="oceania",
    ),
    _route(
        "Melbourne", "Australia", ["Great Ocean Road", "Tasmania", "Sydney", "Adelaide"],
        """
        Onward from Melbourne. The Great Ocean Road (the Twelve Apostles, Loch Ard Gorge) is the
        essential detour - a rented car or a budget bus tour over 2-3 days does it properly, rather
        than the rushed one-day version some tours sell. South across Bass Strait, the Spirit of
        Tasmania overnight ferry (about 9-11h from Geelong) or a short flight gets you to Hobart
        and the Tasmanian wilderness - genuinely worth the detour for hikers, especially the
        Overland Track (bookable October to May). East: Sydney is 12h by train/coach or a short
        flight. West: Adelaide is 8-9h by road, the gateway toward the Nullarbor and Perth, a much
        longer and less-travelled leg most first-timers skip. Melbourne itself is 2-3 days: the
        laneway street art and coffee culture, free trams within the city grid, and a day trip to
        the Yarra Valley wine region or the Mornington Peninsula.
        """,
        region="oceania",
    ),
    _route(
        "Byron Bay", "Australia", ["Gold Coast", "Sydney", "Cairns", "Brisbane"],
        """
        Onward from Byron Bay. North: the Gold Coast and Brisbane are about 1.5-2h by bus, the
        jumping-off point for flights further up to Cairns and the tropical north. South: Sydney
        is a long 10-11h bus or a cheap short flight via Ballina airport just south of town. Byron
        itself is a 3-5 day stop, not a quick one - the lighthouse walk at Cape Byron (Australia's
        easternmost point) for sunrise, learning to surf at the beginner-friendly breaks around
        Wategos/Main Beach, and the hinterland villages of Nimbin and Bangalow as an easy day trip
        for a different, market-town side of the region. It has one of the strongest backpacker
        hostel and long-stay social scenes on the whole east coast, which is exactly why people
        plan two nights and stay two weeks.
        """,
        region="oceania",
    ),
    _route(
        "Auckland", "New Zealand", ["Bay of Islands", "Rotorua", "Wellington", "Waiheke Island"],
        """
        Onward from Auckland, the main international gateway. North: the Bay of Islands (Paihia)
        is about 3-3.5h by bus or car for sailing, dolphin-watching and the Waitangi Treaty
        Grounds. South: Rotorua is 4-4.5h direct by InterCity coach for geothermal geysers, mud
        pools and Maori cultural evenings; continuing on, Wellington is a further 8-9h south by bus
        (most people break the North Island leg at Rotorua and Taupo rather than doing it in one
        push). Waiheke Island is a 40min ferry from downtown for a cheap day of vineyards and
        beaches without leaving the city region. Auckland itself is 2 days: the Sky Tower, the free
        Auckland Domain and Museum, and a walk up One Tree Hill/Maungakiekie for a harbour panorama
        on both sides of the isthmus at once.
        """,
        region="oceania",
    ),
    _route(
        "Queenstown", "New Zealand", ["Milford Sound", "Wanaka", "Te Anau", "Dunedin"],
        """
        Onward from Queenstown, the adventure-sports hub and usual South Island base. Milford
        Sound is a full-day trip (10-12h return, around NZD 100-180 including the fjord cruise)
        through Fiordland - genuinely worth doing as an organised day trip rather than
        self-driving if short on time, since the road itself is long and weather can close it.
        Wanaka is a scenic 1h over the Crown Range, a quieter alternative base with its own lake
        and the "Wanaka Tree" photo spot. Te Anau, the gateway to the Kepler and Milford tracks, is
        about 2h. Dunedin is 3.5-4h southeast for Otago Peninsula wildlife (albatross and penguin
        colonies). Queenstown itself is where the Kawarau Bridge Bungy (the original commercial
        bungy site, around NZD 205-220) and most of the country's other big-ticket adventure
        activities - jet boating, skydiving, canyon swinging - are clustered, plus the Skyline
        Gondola for a cheaper, adrenaline-free view over the lake.
        """,
        region="oceania",
    ),
    _route(
        "Wellington", "New Zealand", ["Picton", "Abel Tasman", "Auckland", "Nelson"],
        """
        Onward from Wellington across to the South Island: the Interislander or Bluebridge ferry
        to Picton takes about 3-3.5h through the Marlborough Sounds, one of the scenic highlights
        of the whole trip and worth booking a daytime sailing for rather than the cheapest slot.
        From Picton, Nelson (2h) is the base for Abel Tasman National Park - book the water taxi
        plus a day or multi-day Coastal Track walk well ahead in summer, since it's one of the most
        popular Great Walks. North back up the North Island, Auckland is a long 8-9h bus, usually
        broken at Taupo. Wellington itself is 2-3 days: the Museum of New Zealand Te Papa
        Tongarewa (free entry, genuinely excellent), the Cable Car up to the Botanic Garden, and
        the waterfront - also worth timing around Wellington's notoriously strong, sudden winds,
        which can shut the ferry crossing at short notice.
        """,
        region="oceania",
    ),
    _route(
        "Rotorua", "New Zealand", ["Auckland", "Taupo", "Wellington"],
        """
        Onward from Rotorua. Auckland is back the way you came, 4-4.5h by InterCity coach. South,
        Taupo is a quick 1h for bungy jumping over the Waikato River and Huka Falls, and is the
        jumping-off point for the Tongariro Alpine Crossing, New Zealand's best one-day hike
        (7-8h, a serious full-day tramp not a casual walk - check conditions, since it crosses
        genuinely alpine terrain that gets snow outside summer). Continuing south, Wellington is a
        further 4.5-5h from Taupo. Rotorua itself is 2 days: the geothermal fields at Te Puia or
        Wai-O-Tapu (mud pools, geysers, the Champagne Pool), a Maori cultural evening (hangi feast
        plus performance), and the smell of sulphur across the whole town, which every visitor
        comments on within an hour of arriving.
        """,
        region="oceania",
    ),
    _route(
        "Seoul", "South Korea", ["Busan", "Gyeongju", "Jeju", "DMZ", "Incheon"],
        """
        Onward from Seoul. South: the KTX to Busan is 2h15 direct, around USD 43-50, with
        trains every 20-30 minutes from Seoul Station - the backbone move of a Korea trip. A
        DMZ/JSA day tour (half-day DMZ only from around USD 40, full JSA access from around
        USD 120, book 1-2 weeks ahead for JSA security clearance, no tours run Sunday or
        Monday) is the other essential Seoul-based day trip. Jeju Island is a roughly 1-hour
        domestic flight, often under USD 30 one-way on Jeju Air, Jin Air or T'way. Seoul
        itself rewards 3-4 days: Gyeongbokgung Palace with its changing-of-the-guard
        ceremony, Bukchon Hanok Village, the Hongdae and Myeongdong nightlife/shopping
        districts, and Namsan Tower at sunset. Incheon airport, an hour from the city by
        train, has its own transit-day attractions (a free city tour for long layovers) if
        passing through rather than stopping.
        """,
        region="east asia",
    ),
    _route(
        "Busan", "South Korea", ["Gyeongju", "Seoul", "Jeju", "Fukuoka Japan"],
        """
        Onward from Busan. Gyeongju, the old Silla capital, is about an hour away by bus or
        train and is the standard day trip: Bulguksa Temple and Seokguram Grotto (both
        UNESCO), and the Daereungwon royal tomb complex in the city centre. Back to Seoul,
        the KTX is 2h15 (USD 43-50). Onward to Japan: the Camellia Line ferry to Fukuoka
        (Hakata) runs 6-11.5 hours depending on the sailing, roughly USD 80-150 - the old
        high-speed JR Beetle hydrofoil (3h40) was discontinued in December 2024 and hasn't
        been replaced, so budget more time than older guides suggest. Jeju is a roughly
        1-hour flight, frequently under USD 30 one-way. Busan itself is 2-3 days: Haeundae
        Beach (with nightlife along the front), Gamcheon Culture Village's colourful hillside
        houses ("Korea's Santorini"), and the Jagalchi fish market. Busan runs 15-20% cheaper
        than Seoul for food and dorms, and is the more relaxed of the two if you want extra
        nights without the capital's pace or prices.
        """,
        region="east asia",
    ),
    _route(
        "Jeju", "South Korea", ["Seoul", "Busan"],
        """
        Onward from Jeju. There's no cheap way off the island except flying: Seoul and Busan
        are both roughly 1-hour flights, frequently under USD 30 one-way on Jeju Air, Jin Air
        or T'way. The old direct Busan-Jeju ferry has been discontinued; sea options now run
        instead from Mokpo, Wando or Nokdong on the mainland (Mokpo-Jeju is about 4.5 hours).
        Jeju itself is worth 3-4 days and rewards renting a car or scooter, since public
        transport is thin outside Jeju City: Hallasan (South Korea's highest peak, a serious
        but doable day hike), the volcanic tuff cone at Seongsan Ilchulbong for sunrise, the
        Manjanggul lava tube, and black-sand/turquoise-water beaches on the east and west
        coasts. It has its own distinct, milder microclimate - noticeably warmer and rainier
        than the mainland - and its own local specialty worth trying: fresh hoe (raw fish)
        and tangerines.
        """,
        region="east asia",
    ),
    _route(
        "Tokyo", "Japan", ["Kyoto", "Hakone", "Nikko", "Kamakura", "Osaka"],
        """
        Onward from Tokyo. Kyoto is the standard next move: 2h15 by Shinkansen, around
        USD 95-100 one-way (JPY 13,320-14,570) - the backbone leg of a first Japan trip.
        Hakone (1.5-2h by train/bus, or a Hakone Free Pass covering the cable car, ropeway
        and pirate-ship lake cruise) is the classic Mt Fuji-view day or overnight trip, best
        on a clear morning. Nikko (2h) for the ornate Toshogu shrine complex and forest
        waterfalls, an easier alternative to Hakone if Fuji is clouded over. Kamakura (1h)
        for the Great Buddha and a laid-back beach-town day trip, crowded on weekends. Tokyo
        itself easily fills 4-5 days: Shibuya and Shinjuku for the neon-city experience,
        Senso-ji temple in Asakusa, the Tsukiji outer market for breakfast sushi, and
        teamLab's digital art museums as a genuine splurge. Get a Suica or Pasmo IC card on
        day one - it works on virtually every train, bus and convenience-store register in
        the country from here on.
        """,
        region="east asia",
    ),
    _route(
        "Kyoto", "Japan", ["Osaka", "Nara", "Hiroshima", "Tokyo"],
        """
        Onward from Kyoto. Osaka is a short, cheap 15-30 minute local-train hop (not worth a
        Shinkansen ticket), and most people base in one city and day-trip the other. Nara
        (35min by local train) is the essential half-day trip: over 1,200 free-roaming sika
        deer in Nara Park that bow for crackers, and Todai-ji temple housing Japan's largest
        bronze Buddha in the world's largest wooden building. West: Hiroshima is 1h40 by
        Shinkansen, around USD 65 (JPY 10,570). Kyoto itself rewards a full 3-4 days, more
        than almost anywhere else in Japan: Fushimi Inari's thousands of vermilion torii
        gates (free, open 24h, best at dawn to beat the tour groups), the Arashiyama bamboo
        grove, Kinkaku-ji (the Golden Pavilion), and Gion in the early evening for a chance
        of spotting a working geiko or maiko. Kyoto's dorm beds (around USD 8-24) are
        noticeably cheaper than Tokyo's, making it a good place to slow down.
        """,
        region="east asia",
    ),
    _route(
        "Osaka", "Japan", ["Kyoto", "Nara", "Hiroshima", "Kobe"],
        """
        Onward from Osaka. Kyoto and Nara are both easy local-train day trips (15-30min and
        about 45min respectively) - Osaka is a genuinely convenient base for both if its
        hostel prices or nightlife suit you better than Kyoto's. West: Hiroshima is 1h26 by
        Shinkansen, around USD 60 (JPY 9,710), continuing to Miyajima's floating torii gate
        by a short onward ferry. Kobe (20-30min) is an easy detour for its beef and the
        Nunobiki Herb Garden ropeway. Osaka itself is 2-3 days built almost entirely around
        food: Dotonbori's canal-side street food (takoyaki, okonomiyaki) is the reason most
        backpackers rate Osaka's eating scene above Tokyo's or Kyoto's, plus Osaka Castle and
        Shinsekai's retro downtown atmosphere. Kansai International Airport is a common
        international entry/exit point if doing a one-way Tokyo-to-Osaka run rather than
        backtracking.
        """,
        region="east asia",
    ),
    _route(
        "Hiroshima", "Japan", ["Miyajima", "Kyoto", "Osaka", "Fukuoka"],
        """
        Onward from Hiroshima. Miyajima island is a short 10-minute ferry (plus a 30min
        tram/train from central Hiroshima) for the iconic "floating" torii gate of
        Itsukushima Shrine and free-roaming deer - doable as a half-day but an overnight lets
        you see the gate lit up after the day-trippers leave. Back east: Kyoto is 1h40 by
        Shinkansen (around USD 65), Osaka 1h26 (around USD 60). West: Fukuoka/Hakata is a
        further 1h by Shinkansen and is the jumping-off point for the Camellia Line ferry to
        Busan, South Korea (6-11.5h, roughly USD 80-150) if continuing overland into Korea
        rather than flying. Hiroshima itself is a sobering, essential 1-2 days: the Peace
        Memorial Park and Museum, and the Atomic Bomb Dome, left deliberately as it was in
        1945. Most backpackers combine the museum with Miyajima on the same trip to end the
        day on a lighter note.
        """,
        region="east asia",
    ),
    _route(
        "Beijing", "China", ["Xian", "Datong", "Chengdu", "Shanghai", "Ulaanbaatar"],
        """
        Onward from Beijing. Xian (the Terracotta Army) is a straightforward 4.5-6h
        high-speed train, USD 60-90 second class, and the natural first move for most
        itineraries. Datong, 2h by high-speed rail, is an easy and underrated day-or-two
        detour few first-timers take, for the Hanging Monastery and the Yungang Grottoes.
        Chengdu (pandas, Sichuan food) is a longer 7-8h high-speed run or a 3h flight. For
        the Trans-Mongolian route, the twice-weekly K23/K3 train to Ulaanbaatar takes about
        27-30h - book well ahead, seats sell out fast in Mongolia's short summer season.
        Shanghai is 4.5-5h by high-speed rail, the standard way to close a loop through the
        east. Beijing itself is worth 4-5 days minimum: the Great Wall (Mutianyu is less
        crowded and better maintained than Badaling), the Forbidden City, and the hutong
        alleys around Houhai.
        """,
        region="east asia",
    ),
    _route(
        "Xian", "China", ["Beijing", "Chengdu", "Guilin"],
        """
        Onward from Xian. Chengdu is 3.5-4h by high-speed rail, USD 45-65, the natural next
        stop for pandas and Sichuan food. Beijing is 4.5-6h back the way you came. Guilin,
        further south for the karst scenery, is a longer haul at around 10-11h by
        high-speed rail - most people fly this leg instead (about 2h, often cheaper than
        the train). Xian itself is a 2-3 day stop: the Terracotta Army (book the earliest
        entry slot to beat the tour groups), the intact Ming-dynasty city wall (rentable
        bikes to ride the full loop), and the Muslim Quarter's night food street.
        """,
        region="east asia",
    ),
    _route(
        "Chengdu", "China", ["Xian", "Beijing", "Lhasa", "Kunming"],
        """
        Onward from Chengdu. Kunming, the gateway to Yunnan and the overland route toward
        Laos/Vietnam/Myanmar, is 6-7h by high-speed rail or a 1.5h flight. Xian is 3.5-4h
        back north by high-speed rail. Lhasa is reachable by a spectacular but long 36-40h
        train over the Tibetan Plateau, or a 2.5h flight - either way, remember the Tibet
        Travel Permit is mandatory and can only be arranged through a licensed agency well
        in advance, so this is not a spontaneous add-on. Chengdu itself is worth 2-3 days
        for the giant panda bases (go at opening time, when the pandas are most active) and
        the Sichuan hotpot scene.
        """,
        region="east asia",
    ),
    _route(
        "Guilin", "China", ["Yangshuo", "Kunming", "Beijing"],
        """
        Onward from Guilin. Nearly everyone's real destination is Yangshuo, 1h by shuttle
        bus - the rice-terrace roads, a Yulong River bamboo raft trip (cheaper and quieter
        than the main Li River cruise that starts in Guilin), and a genuine rock-climbing
        scene make it worth 3-4 days on its own, more than Guilin city itself. From
        Guilin/Yangshuo onward: Kunming, for the Yunnan extension toward Laos, Vietnam and
        Myanmar, is a long 10-11h high-speed rail run or a 1.5-2h flight. Guilin city
        itself is worth one day for the Li River cruise if short on time, or skip straight
        to Yangshuo.
        """,
        region="east asia",
    ),
    _route(
        "Kunming", "China", ["Dali", "Lijiang", "Shangri-La", "Chengdu"],
        """
        Onward from Kunming, the "Spring City" and gateway to Yunnan. Dali (the old
        Bai-minority town on Erhai Lake) is 4-5h by bus or a quicker 2h on the
        high-speed rail link. Lijiang, a further 2-3h from Dali by bus or train, is
        the jump-off point for the 2-4 day Tiger Leaping Gorge trek, one of the
        best budget treks in China. Shangri-La, another 3-4h beyond Lijiang, sits
        above 3,200m - genuine altitude sickness risk, acclimatise a day before any
        hiking, and its Tibetan-influenced culture and monasteries are a preview of
        the Tibetan Plateau without the permit Tibet itself requires. Back toward
        the standard corridor, Chengdu is 6-7h by high-speed rail or a 1.5h flight.
        For continuing overland out of China: the China-Laos high-speed railway to
        Vientiane (roughly 10-13h) starts here, and the Hekou-Lao Cai border
        crossing into Vietnam is a further, less-travelled option. Kunming itself
        is worth a day: the Stone Forest karst formations (1.5h out of town) and
        Yunnan's distinctive "crossing-the-bridge" rice noodles, found almost
        nowhere else in the country.
        """,
        region="east asia",
    ),
    _route(
        "Shanghai", "China", ["Suzhou", "Hangzhou", "Beijing", "Guilin"],
        """
        Onward from Shanghai. Suzhou, famous for its classical Ming-era gardens, is
        a cheap 25-minute high-speed rail hop - genuinely doable as a day trip.
        Hangzhou, for West Lake and its surrounding tea hills, is 45min-1h and
        rewards an overnight more than Suzhou does. Beijing is 4.5-5h by high-speed
        rail, the standard way to close a Beijing-Xian-Guilin-Shanghai loop; Guilin
        is a similar distance southwest. For onward international travel without
        flying, a twice-weekly ferry to Osaka, Japan runs about 45 hours from
        around USD 150-200 for the cheapest berth - a slow, genuinely cheap
        alternative for anyone not in a hurry. Shanghai itself rewards 3-4 days:
        the Bund's riverside skyline view of Pudong, Yu Garden and the old town,
        the French Concession's tree-lined streets and cafe scene, and Zhujiajiao
        water town as an easy half-day trip. The Maglev train to Pudong airport
        (a top speed of 430km/h over its 8-minute run) is worth riding once just
        for what it is, even if the metro is cheaper for the same trip.
        """,
        region="east asia",
    ),
    _route(
        "Harbin", "China", ["Beijing"],
        """
        Onward from Harbin - worth naming honestly as a narrow-appeal detour, not
        a standard stop on the Beijing-Xian-Guilin-Shanghai corridor. Almost
        everyone who comes this far north does so for one specific event: the
        Harbin International Ice and Snow Festival, roughly early January to late
        February, when city-block-sized illuminated ice sculptures and buildings
        make it one of the most striking winter spectacles anywhere - and one of
        the coldest, routinely -20C or lower, genuine expedition-grade layers
        required, not a normal winter coat. Outside that window there is
        meaningfully less reason to come. Harbin's Russian-colonial history as a
        Trans-Siberian Railway town is visible year-round in Central Street's
        architecture and Saint Sophia Cathedral, and the Siberian Tiger Park
        outside town is open regardless of season. Onward, Beijing is a long haul:
        about 8h by high-speed rail or a 2-2.5h flight, the practical way most
        people actually make the connection back to the main corridor.
        """,
        region="east asia",
    ),
    _route(
        "Lima", "Peru", ["Huacachina", "Arequipa", "Cusco"],
        """
        Onward from Lima, the usual international arrival point and not a place to
        linger more than 2-3 days. South along the Panamericana: an overnight or
        day bus to Huacachina (5-6h) for the desert oasis, sandboarding and pisco
        tastings, then on to Nazca (2h further) for the Lines. Southeast to
        Arequipa is a long direct bus (14-16h) that most people break up via the
        coastal stops rather than doing in one push. Lima itself: Miraflores'
        clifftop Malecon, Barranco's street art and nightlife, and a ceviche lunch
        at a proper cevicheria rather than a hotel restaurant - lunch, not dinner,
        is when it is freshest and cheapest.
        """,
        region="south america",
    ),
    _route(
        "Cusco", "Peru", ["Machu Picchu", "Puno", "Arequipa", "La Paz"],
        """
        Onward from Cusco, the hub for the whole southern Peru circuit. Machu
        Picchu is reached either by the 4-day Inca Trail (permits book out months
        ahead for the May-September season) or by train from Ollantaytambo to
        Aguas Calientes (around 1.5-2h, from roughly USD 70 one-way) for a
        same-day or overnight visit. Southeast to Puno (6-7h bus) for Lake
        Titicaca's floating Uros islands, then on to La Paz, Bolivia via the
        Desaguadero or Copacabana border crossing (around 7-10h total including
        formalities). Southwest to Arequipa is a 10-11h bus. Cusco itself rewards
        2-3 days of altitude acclimatisation before any trek: the San Pedro
        market, Sacsayhuaman ruins above town, and the Sacred Valley (Pisac,
        Ollantaytambo) as an easy day trip.
        """,
        region="south america",
    ),
    _route(
        "Arequipa", "Peru", ["Colca Canyon", "Cusco", "Lima"],
        """
        Onward from Arequipa, Peru's underrated "White City" built from white
        volcanic sillar stone. Colca Canyon, one of the world's deepest canyons and
        the best place in Peru to see condors soaring on the morning thermals, is a
        3-4h bus to Chivay followed by an early village-to-village trek or a
        single punishing day tour - departures are typically 3-4am, so budget a
        night in Arequipa beforehand rather than arriving and leaving same-day.
        Onward to Cusco is a 10-11h night bus; back to Lima is 14-16h or a short
        flight. Arequipa itself is worth 2-3 days: the Santa Catalina Monastery (a
        walled colonial city within the city), and it is the standard place to
        acclimatise for a day or two before heading up to Cusco's higher altitude.
        """,
        region="south america",
    ),
    _route(
        "Bogota", "Colombia", ["Medellin", "Salento", "San Gil", "Cartagena"],
        """
        Onward from Bogota, the high-altitude (2,640m) capital and usual arrival
        point. Medellin is 8-10h by bus or a cheap, fast 1h flight - most
        backpackers fly given the distance and mediocre road. Salento and the
        coffee region are 7-8h by bus. San Gil, the adventure-sports hub
        (rafting, paragliding, caving), is 7h. Bogota itself is 2-3 days: the
        gold museum, the street art and cafes of La Candelaria's colonial core,
        and Monserrate hill by cable car or funicular for a city panorama - go
        early to avoid both crowds and Bogota's frequent afternoon rain.
        """,
        region="south america",
    ),
    _route(
        "Medellin", "Colombia", ["Guatape", "Salento", "Cartagena", "Bogota"],
        """
        Onward from Medellin, most travellers' favourite Colombian base for a
        long-stay stop. Guatape (2h) is the classic day trip: the striped rock
        of El Penon (740 steps to the top) and a lakeside town of brightly
        painted zocalos. Salento and the coffee region are 5-6h. Cartagena is a
        long overnight bus (13-15h) or a much faster 1h flight - fly this one
        unless you specifically want the overland experience. Medellin itself
        rewards several days: the Comuna 13 graffiti tour with a local operator,
        the Metrocable up into the hillside barrios for the view alone, and
        Parque Lleras/El Poblado as the backpacker social base.
        """,
        region="south america",
    ),
    _route(
        "Cartagena", "Colombia", ["Santa Marta", "Tayrona", "Medellin", "Bogota"],
        """
        Onward from Cartagena. Santa Marta is 4-5h by bus and is itself the
        gateway to Tayrona National Park (a further 1h) for jungle-backed
        beaches, and to the multi-day Lost City (Ciudad Perdida) trek, a
        4-5 day jungle hike to Kogi-territory ruins that rivals Peru's Inca Trail
        for many backpackers without the permit bottleneck. Back inland, Medellin
        and Bogota are both best reached by air (1-1.5h) rather than the long
        overland bus. Cartagena itself is 2-3 days: the Walled City's colonial
        core, and Getsemani next door for the street art, cheaper hostels and a
        livelier backpacker nightlife scene - Getsemani has gentrified fast and
        is safe in its main streets, though some side streets still warrant care
        after dark.
        """,
        region="south america",
    ),
    _route(
        "Quito", "Ecuador", ["Banos", "Otavalo", "Mindo", "Cuenca"],
        """
        Onward from Quito, the high-altitude (2,850m) capital and usual arrival
        point. Banos is 4h/USD 5 direct from Quitumbe terminal in the south of
        the city. Otavalo (2h), for South America's largest indigenous
        handicrafts market (best on Saturday mornings), is an easy day trip or
        overnight. Mindo (2-2.5h) is the cloud-forest stop for birdwatching,
        tubing and zip-lining, a good low-key add-on before heading further
        south. Cuenca is a longer 8-10h direct bus or better broken up via
        Banos. Quito itself is worth 2-3 days: the well-preserved colonial Old
        Town (a UNESCO site), the TelefeQuito cable car up Pichincha volcano for
        a city panorama, and standing on the actual equator line at the Museo
        Intinan (not the touristy "Mitad del Mundo" monument next door, which
        is slightly mislocated).
        """,
        region="south america",
    ),
    _route(
        "Banos", "Ecuador", ["Quito", "Cuenca", "Coca"],
        """
        Onward from Banos. Back to Quito is 4h. South to Cuenca is a slow,
        winding 8-10h with no fast alternative - most people treat it as the
        day's plan rather than a quick hop. East into the Amazon, Coca (Puerto
        Francisco de Orellana) is the jumping-off point for jungle lodges further
        downriver, roughly 5-6h by bus or a short flight. Banos itself is 2-4
        days: the Waterfall Route (Ruta de las Cascadas) by rented bike or
        dune buggy (USD 5-10/day) past a string of cascades including Pailon
        del Diablo, the hot springs the town is named for, and the swing at
        Casa del Arbol with Tungurahua volcano as a backdrop when it isn't
        clouded over.
        """,
        region="south america",
    ),
    _route(
        "Cuenca", "Ecuador", ["Banos", "Guayaquil", "Quito"],
        """
        Onward from Cuenca. Banos is the same slow 8-10h back north. Guayaquil
        (4-4.5h) is mainly useful as the departure point for flights to the
        Galapagos, which are noticeably cheaper from Guayaquil than from Quito.
        Quito direct is 8-9h, usually broken up via Banos rather than done in one
        go. Cuenca itself is 2-3 days: the UNESCO-listed colonial centre with its
        blue-domed cathedral, Panama hats (genuinely made here despite the name,
        not in Panama), and El Cajas National Park an hour away for high-altitude
        paramo hiking among hundreds of glacial lakes.
        """,
        region="south america",
    ),
    _route(
        "La Paz", "Bolivia", ["Uyuni", "Death Road", "Sucre", "Copacabana"],
        """
        Onward from La Paz, the world's highest administrative capital
        (3,650m) and the near-universal hub for Bolivia. Uyuni is reached by
        overnight bus (9-10h) or a short flight - most backpackers bus it to
        save the flight cost and use the overnight hours for sleep. The Death
        Road mountain-bike descent (Yungas Road) is a full-day trip direct from
        La Paz, no overnight needed. Copacabana, on Lake Titicaca and the
        onward route to Puno, Peru, is 3-4h. Sucre is a longer 12-14h overnight
        bus or a short flight. La Paz itself is 2-3 days: the cable-car network
        (Mi Teleferico) is the cheapest sightseeing in South America and doubles
        as functional public transport up into El Alto, the Witches' Market for
        the (occasionally unsettling) llama-fetus stalls, and San Pedro Prison's
        surrounding streets by day only - it is not the informal tourist
        attraction it once had a reputation for being.
        """,
        region="south america",
    ),
    _route(
        "Uyuni", "Bolivia", ["San Pedro de Atacama Chile", "La Paz", "Sucre", "Villazon"],
        """
        Onward from Uyuni, essentially a one-purpose town built around the salt
        flat tours. The standard exit for anyone continuing the circuit south is
        the 3-day 4x4 salt-flat tour ending at the Chilean border, dropping you
        directly in San Pedro de Atacama rather than backtracking to Uyuni town -
        the efficient way to link Bolivia and Chile without doubling back. Back
        to La Paz is a 9-10h overnight bus. Sucre is 6-7h. South to the
        Argentine border at Villazon (for Salta) is a longer haul via Tupiza,
        itself worth a stop for cheaper, less crowded horseback and 4x4 desert
        tours than Uyuni's. Uyuni town itself has little beyond the tour
        agencies and the train cemetery on its outskirts, worth an hour before
        or after a tour rather than a dedicated stop.
        """,
        region="south america",
    ),
    _route(
        "Sucre", "Bolivia", ["La Paz", "Uyuni", "Potosi"],
        """
        Onward from Sucre, Bolivia's whitewashed constitutional capital and the
        country's most popular place to study Spanish cheaply. Potosi, the
        former world's-richest silver-mining city and now a sobering, still-active
        mine tour (genuinely dangerous conditions, book a reputable operator),
        is 2.5-3h. La Paz is a long overnight bus (12-14h) or a short flight.
        Uyuni is 6-7h, the usual link onward to the salt flats. Sucre itself
        rewards a longer stay than most itineraries budget: the white colonial
        centre, the dinosaur footprints at Cal Orck'o on the edge of town, and
        consistently the cheapest, most laid-back Spanish-immersion scene on the
        continent.
        """,
        region="south america",
    ),
    _route(
        "Santiago", "Chile", ["Valparaiso", "San Pedro de Atacama", "Puerto Natales"],
        """
        Onward from Santiago, the central hub most trips start and end at.
        Valparaiso is an easy 1h40 bus for the graffiti-covered hillside
        funiculars and port-city atmosphere - a worthwhile 1-2 night stop or day
        trip. North to San Pedro de Atacama is a long 20-23h bus (better broken
        with an overnight, "salon-cama" seats recommended) or a 2h flight to
        Calama plus a short transfer. South to Puerto Natales, the Patagonia
        gateway, is far enough that almost everyone flies (around 3.5h) rather
        than facing a multi-day bus. Santiago itself is 2 days: the Bellavista
        and Lastarria neighbourhoods for food and nightlife, and the Cerro San
        Cristobal funicular for a smog-permitting city panorama with the Andes
        behind it.
        """,
        region="south america",
    ),
    _route(
        "San Pedro de Atacama", "Chile", ["Uyuni Bolivia", "Santiago", "Calama"],
        """
        Onward from San Pedro de Atacama, a small desert town that is the base
        for the whole Atacama circuit rather than a destination in itself.
        Crossing into Bolivia to Uyuni is the classic onward move: a 3-day 4x4
        salt-flat tour run in reverse from the Bolivian side, ending in Uyuni
        town rather than a simple bus transfer. Calama, 1h10 away, is the
        airport town for flights back to Santiago (around 2h) when the long bus
        is not appealing. San Pedro itself is 3-4 days of day-tour base: Valle
        de la Luna at sunset, the El Tatio geysers (a brutal 4am pickup to catch
        them steaming at dawn), and the high-altitude Altiplanic lagoons -
        almost everything here is done via organised half or full-day tours
        from town rather than independently, given the distances and lack of
        public transport between sites.
        """,
        region="south america",
    ),
    _route(
        "Puerto Natales", "Chile", ["Torres del Paine", "El Calafate Argentina", "Punta Arenas"],
        """
        Onward from Puerto Natales, the compact gateway town for Torres del
        Paine National Park. The park entrance is roughly 1.5-2h by bus or
        organised transfer, with the W Trek (4-5 days) or the longer O Circuit
        (7-10 days) as the main draws - book refugio/campsite accommodation
        months ahead for December-February. Crossing into Argentina, El Calafate
        (for the Perito Moreno Glacier) is a straightforward 5-6h bus across the
        border. Punta Arenas, for onward flights or Antarctic-adjacent
        cruises, is 3h south. Puerto Natales itself is a 1-2 day logistics stop
        for gear rental and grocery shopping before the trek - it has limited
        sights of its own beyond the waterfront and is treated by most
        backpackers as pure staging ground.
        """,
        region="south america",
    ),
    _route(
        "Buenos Aires", "Argentina", ["Mendoza", "Iguazu Falls", "Bariloche", "El Calafate"],
        """
        Onward from Buenos Aires, the near-universal arrival hub. Mendoza is a
        2h flight or a long 13-14h overnight bus for wine country. Iguazu Falls
        (Puerto Iguazu) is 1h45 by air or a very long 18-19h bus - fly this one
        unless time is no object. Bariloche is 2h15 by air or a full 22-24h bus.
        El Calafate, for Patagonia's south, is 3h by air. Buenos Aires itself
        rewards 3-4 days: San Telmo's Sunday antiques market, a tango show
        (skip the touristy dinner-show package, seek out a milonga instead for
        the real thing), the pastel houses of La Boca's Caminito, and Recoleta
        Cemetery, where Evita is buried among elaborate above-ground mausoleums.
        """,
        region="south america",
    ),
    _route(
        "Mendoza", "Argentina", ["Buenos Aires", "Santiago Chile", "Bariloche"],
        """
        Onward from Mendoza. Back to Buenos Aires is a 2h flight or a long
        13-14h overnight bus. West over the Andes to Santiago, Chile is a
        spectacular 6-7h bus through the high mountain pass (weather-dependent
        in winter, sometimes closed by snow). South to Bariloche is a long
        18-19h bus or a shorter flight via Buenos Aires. Mendoza itself is 2-3
        days: bike-and-wine tours through Lujan de Cuyo and the Uco Valley
        wineries (rent a bike and a map from a hostel rather than booking a
        guided van tour, cheaper and more fun), and Aconcagua, the highest peak
        outside Asia, visible and climbable (with permits, for serious
        mountaineers only) from the province.
        """,
        region="south america",
    ),
    _route(
        "Bariloche", "Argentina", ["El Calafate", "Buenos Aires", "Puerto Varas Chile"],
        """
        Onward from Bariloche, the northern gateway to Argentine Patagonia. El
        Calafate is 1.5h by air (the bus is a very long 24h+ and rarely worth
        it). Buenos Aires is 2h15 by air. West into Chile, Puerto Varas is
        reachable via the multi-day Cruce Andino lake-and-bus crossing through
        Andean scenery, a genuinely scenic alternative to flying. Bariloche
        itself is 3-4 days: the Circuito Chico lake-and-mountain drive (rentable
        by bike or car), Cerro Catedral for hiking in summer or skiing in the
        July-August winter season, and the town's famous chocolate shops, a
        legacy of its Swiss-German immigrant history.
        """,
        region="south america",
    ),
    _route(
        "El Calafate", "Argentina", ["Puerto Natales Chile", "Ushuaia", "Bariloche", "Buenos Aires"],
        """
        Onward from El Calafate, the base for Argentina's Perito Moreno Glacier.
        Crossing into Chile, Puerto Natales (for Torres del Paine) is a
        straightforward 5-6h bus over the border. South to Ushuaia, the world's
        southernmost city and jumping-off point for Antarctica cruises, is a
        long 18-19h bus around the Chilean side of the border or a short flight.
        Buenos Aires is a 3h flight. El Calafate itself is 2-3 days: the Perito
        Moreno Glacier's walkways (a straightforward day trip, watch and listen
        for the ice calving off the face) and, for the more committed, ice-trekking
        directly on the glacier itself with crampons, bookable in town.
        """,
        region="south america",
    ),
    _route(
        "Rio de Janeiro", "Brazil", ["Paraty", "Ilha Grande", "Salvador", "Florianopolis"],
        """
        Onward from Rio, the usual arrival point and worth 4-5 days on its own.
        Paraty, a well-preserved colonial coastal town, is 4-5h by bus
        (around R$70). Ilha Grande, a car-free island with some of Brazil's best
        beaches, is reached via a bus-plus-boat combo from either Rio or the
        Angra dos Reis mainland. North to Salvador is a long 24h+ bus or a
        cheap 2h flight - fly this one. South to Florianopolis is similarly
        long overland or a 1.5h flight. Rio itself: Christ the Redeemer and
        Sugarloaf by cable car for the views, Santa Teresa's tram and bohemian
        streets, and a Copacabana or Ipanema beach day - keep valuables to a
        bare minimum on the sand, phone and bag snatching is a real and common
        risk there.
        """,
        region="south america",
    ),
    _route(
        "Salvador", "Brazil", ["Rio de Janeiro", "Foz do Iguacu", "Morro de Sao Paulo"],
        """
        Onward from Salvador, the historic heart of Afro-Brazilian culture.
        Rio is a 2h flight or a long 24h+ bus. Morro de Sao Paulo, a
        car-free island beach town, is a combined bus-and-boat trip of around
        3-4h and a popular quieter add-on. Foz do Iguacu, for the Brazilian side
        of Iguazu Falls, is a longer domestic flight connection (there is no
        practical direct overland option). Salvador itself is 2-3 days: the
        Pelourinho historic centre's colourful colonial architecture and live
        capoeira and percussion in the street, Afro-Brazilian Candomble
        culture and cuisine (acaraje street food is the classic bite), and
        beaches within the city itself before heading further up the coast for
        quieter sand.
        """,
        region="south america",
    ),
    _route(
        "Florianopolis", "Brazil", ["Rio de Janeiro", "Paraty", "Foz do Iguacu"],
        """
        Onward from Florianopolis ("Floripa"), an island city with over 40
        beaches ranging from surf breaks to families-only calm water. Rio is a
        1.5h flight or a long overland haul. Paraty, breaking the journey north,
        is a similarly long bus best flown past rather than endured in one go.
        Foz do Iguacu is a domestic flight connection, no practical direct bus.
        Floripa itself rewards renting a scooter or car for a few days to work
        the island's beaches by surf conditions and crowd level - Joaquina and
        Mole for surfing and nightlife, Lagoinha do Leste for a quieter
        hike-in beach, and the historic centre (Santo Antonio de Lisboa) for a
        slower colonial-fishing-village afternoon.
        """,
        region="south america",
    ),
    _route(
        "Sao Paulo", "Brazil", ["Rio de Janeiro", "Ilhabela", "Paraty", "Ouro Preto"],
        """
        Onward from Sao Paulo. Most backpackers pass through fast rather than
        linger - Rio is the city Brazil trips are actually built around - but
        Sao Paulo has South America's best food and nightlife scene by a wide
        margin (Vila Madalena and Augusta for bars, some of the continent's
        best pizza and Japanese food, a legacy of the world's largest Japanese
        diaspora community) if a night or two fits the route. Rio is 5-6h by
        bus or a cheap 1h flight - fly it if time is short. Ilhabela, a car-
        free island known for sailing and surf, is 4-5h by bus and boat.
        Paraty, the colonial coastal town also reachable from Rio, is about
        4h. Ouro Preto, a UNESCO colonial mining town in Minas Gerais with
        some of Brazil's finest Baroque churches, is 5-6h and a genuinely
        underrated add-on most first-time itineraries skip entirely. In the
        city itself: the MASP art museum on Avenida Paulista, the Beco do
        Batman street-art alley in Vila Madalena, and Ibirapuera Park for a
        break from the traffic. The same beach-day caution as Rio applies to
        valuables in crowded public spaces here.
        """,
        region="south america",
    ),
    _route(
        "Manaus", "Brazil", ["Amazon Jungle Lodges", "Anavilhanas Archipelago", "Belem"],
        """
        Onward from Manaus, the only realistic gateway to the Brazilian
        Amazon - no road connects it to the rest of the country, so every
        route in or out is by river or by air. Jungle lodge stays (2-4 nights
        is standard, booked through a Manaus-based operator rather than
        independently) range from budget riverside lodges to higher-end
        options, and dry season (roughly May-October) suits trail-based
        wildlife walks while wet season (especially around February) favours
        canoe trips through flooded forest (igapo) instead - see the Brazil
        seasonal document. The Meeting of the Waters (Encontro das Aguas), a
        half-day boat trip from the city, is the single most popular outing:
        the black Rio Negro and the pale, sediment-heavy Rio Solimoes run
        side by side for kilometres without mixing. The Anavilhanas
        Archipelago, the world's second-largest river-island archipelago, is
        a further half-to-full day upriver. For the genuinely committed,
        multi-day hammock-class riverboats run down the Amazon to Belem near
        the river's mouth - slow, cheap, and one of the classic South America
        bucket-list journeys rather than a normal transport leg. Manaus
        itself is worth a day for the ornate Teatro Amazonas opera house, a
        rubber-boom-era relic that looks completely out of place in the
        middle of the rainforest.
        """,
        region="south america",
    ),
    _route(
        "Jericoacoara", "Brazil", ["Fortaleza", "Lencois Maranhenses", "Natal"],
        """
        Onward from Jericoacoara ("Jeri"), a car-free village of sand streets
        that is Brazil's kitesurfing and windsurfing capital - the steady
        trade winds peak roughly July/August through December. There is no
        paved road in: the standard approach from Fortaleza is a 5-6h
        bus-and-4x4-dune-buggy combination, part of the town's appeal rather
        than a flaw. Continuing along the coast toward Sao Luis, the Lencois
        Maranhenses National Park - white sand dunes pooling with rainwater
        lagoons, at their fullest and bluest roughly June-September after the
        rains - is a further, genuinely rugged multi-day journey and one of
        Brazil's most photographed but least-visited landscapes precisely
        because it is so inconvenient to reach. Natal is the other direction
        along the coast, a longer haul with its own dune and beach scene.
        Jeri itself rewards 3-5 days: sunset from the Duna do Por do Sol
        (Sunset Dune) right in town, the Pedra Furada rock arch a beach walk
        away, and dune-buggy tours to freshwater lagoons (Lagoa do Paraiso,
        Lagoa Azul) further out. This is the Northeast beach scene beyond the
        Salvador circuit most first-time Brazil itineraries never reach.
        """,
        region="south america",
    ),
    _route(
        "Cape Town", "South Africa", ["Stellenbosch", "Hermanus", "Knysna", "Johannesburg"],
        """
        Onward from Cape Town, usually the first stop and worth 4-5 days on its
        own. Stellenbosch and Franschhoek, the Winelands, are an easy 45min-1h
        drive or a wine-tram/tour day trip. Hermanus, for shore-based whale
        watching (Southern Rights, roughly June-November, peak August-
        November), is 1.5-2h. West of the city, Cape Point and Boulders
        Beach's African penguin colony make a full, worthwhile day trip.
        Gansbaai, the shark-cage-diving hub, is a further hour past Hermanus.
        Heading east, Knysna and the rest of the Garden Route are the start of
        a multi-day self-drive or Baz Bus hop-on-hop-off run along the N2 (see
        the tips document for what Baz Bus does and doesn't cover in 2026).
        For Kruger and the interior, Johannesburg is a 2h flight - there is no
        practical overland option most backpackers actually use. Cape Town
        itself: Table Mountain by cableway (weather-dependent, closes in high
        wind) or the free Platteklip Gorge hike, Robben Island's ferry tour,
        Bo-Kaap's colourful streets, and the District Six Museum. Long Street's
        nightlife is popular and fine in a group; keep valuables minimal
        walking back late and stick to well-lit routes, the same rule as any
        big-city nightlife strip in this corpus.
        """,
        region="africa",
    ),
    _route(
        "Johannesburg", "South Africa", ["Hazyview", "Pretoria", "Durban", "Cape Town"],
        """
        Onward from Johannesburg, the main international gateway and usually a
        short stop rather than a destination. Hazyview and the rest of the
        Kruger/Panorama Route area is 5-6h by self-drive or shuttle along the
        N4, or a 1h flight to Kruger Mpumalanga International or Skukuza
        airport if time is short. Pretoria is a quick 45min-1h for the Union
        Buildings and jacaranda-lined streets (spectacular late
        September-October when they bloom). Durban is a long 6-7h drive or a
        cheap 1.5h flight. Cape Town is a 2h flight, the standard way to link
        the two ends of a South Africa trip. Johannesburg itself is worth 1-2
        days rather than a quick transit: the Apartheid Museum, a half-day
        Soweto tour with an established community-based operator (Vilakazi
        Street, the Hector Pieterson Memorial), and Constitution Hill. Most
        backpackers base themselves in Sandton, Rosebank or Melville rather
        than the CBD and rely on Uber/Bolt rather than walking between areas
        after dark - see the tips document for the specifics behind that
        advice.
        """,
        region="africa",
    ),
    _route(
        "Hazyview", "South Africa", ["Kruger National Park", "Blyde River Canyon", "Eswatini", "Johannesburg"],
        """
        Onward from Hazyview, the standard backpacker base for a self-drive
        Kruger safari. Kruger's Numbi or Phabeni gates are 20-30min away;
        self-drive day passes (a conservation fee per person per day) make
        independent Big Five game viewing genuinely accessible on a budget,
        no guided tour required, though gate times are strict (roughly
        sunrise to sunset, checked on exit) and dry-season months
        (May-September, see the seasonal document) give noticeably better
        sightings. The Panorama Route - God's Window, Bourke's Luck Potholes,
        and the Blyde River Canyon, one of the largest "green" (vegetated)
        canyons on Earth - is an easy half-day loop by car. Continuing east,
        the Eswatini (formerly Swaziland) border is 2-3h, a common add-on for
        travellers with time and the right onward visa arrangements; Maputo,
        Mozambique is a longer haul from here but a classic combination from
        Kruger for beach time afterward. Back to Johannesburg is 5-6h by road.
        Malaria prophylaxis is a real consideration for this whole area - see
        the tips document - unlike Cape Town or Johannesburg itself.
        """,
        region="africa",
    ),
    _route(
        "Durban", "South Africa", ["Drakensberg", "Wild Coast", "St Lucia", "Johannesburg"],
        """
        Onward from Durban, the KwaZulu-Natal gateway and, unlike Cape Town's
        cold Atlantic water, a warm Indian Ocean beach city year-round. The
        Drakensberg (uKhahlamba), for hiking beneath South Africa's highest
        peaks and the Amphitheatre, is about 3h inland. South down the Wild
        Coast toward Coffee Bay is a genuinely slow, bumpy 4-5h - part of its
        appeal as one of the least-developed, most backpacker-loved stretches
        of coastline in the country, strong on Xhosa culture and cliff
        scenery, light on infrastructure. North, St Lucia and the
        iSimangaliso Wetland Park (hippos and crocodiles visible on an
        estuary boat trip, plus turtle-nesting season roughly
        November-February) is about 3h, often combined with the Hluhluwe-
        iMfolozi game reserve nearby - the reserve where the modern rhino-
        conservation movement began. Johannesburg is a 6-7h drive or a cheap
        1.5h flight. Durban itself: the Golden Mile beachfront, South
        Africa's strongest surf culture, and bunny chow (a curry served in a
        hollowed-out bread loaf), a legacy of the city's large Indian
        community and one of the country's genuinely distinctive local
        dishes.
        """,
        region="africa",
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
    "huay xai": "laos", "4000 islands": "laos", "pakse": "laos",
    "vieng xai": "laos",
    "ha giang": "vietnam", "ninh binh": "vietnam",
    "cat ba": "vietnam", "phong nha": "vietnam",
    "da nang": "vietnam", "nha trang": "vietnam",
    "mui ne": "vietnam", "mekong delta": "vietnam", "can tho": "vietnam",
    "lao cai": "vietnam",
    "angkor": "cambodia", "angkor wat": "cambodia",
    "kep": "cambodia", "koh rong": "cambodia", "koh rong sanloem": "cambodia",
    "poipet": "cambodia",
    "bali": "indonesia", "java": "indonesia", "sumatra": "indonesia",
    "nusa penida": "indonesia", "gili islands": "indonesia",
    "gili air": "indonesia", "amed": "indonesia",
    "yogyakarta": "indonesia", "lombok": "indonesia", "seminyak": "indonesia",
    "uluwatu": "indonesia",
    "borneo": "malaysia", "george town": "malaysia",
    "cameron highlands": "malaysia", "taman negara": "malaysia", "melaka": "malaysia",
    "perhentian islands": "malaysia", "kota kinabalu": "malaysia",
    "koh lipe": "thailand",
    "port barton": "philippines",
    "cebu": "philippines", "moalboal": "philippines", "manila": "philippines",
    "bohol": "philippines",
    "chitwan": "nepal", "annapurna base camp": "nepal",
    "everest base camp": "nepal", "nagarkot": "nepal", "poon hill": "nepal",
    "arugam bay": "sri lanka", "mirissa": "sri lanka",
    "nuwara eliya": "sri lanka", "sigiriya": "sri lanka", "unawatuna": "sri lanka",
    "galle": "sri lanka", "colombo": "sri lanka",
    # India (route docs cover delhi/rishikesh/varanasi/goa/jaisalmer/hampi/
    # jaipur/udaipur/amritsar/mumbai as origins; these are hop-only towns).
    "pushkar": "india", "jodhpur": "india", "mcleod ganj": "india",
    "dharamshala": "india", "haridwar": "india", "bodh gaya": "india",
    "kolkata": "india", "gokarna": "india", "bengaluru": "india",
    "agra": "india", "kasol": "india", "manali": "india", "leh": "india",
    "kerala": "india", "munnar": "india", "kochi": "india",
    # Myanmar (route docs cover yangon/bagan/inle lake/mandalay/kalaw).
    "hsipaw": "myanmar", "kyaiktiyo": "myanmar", "naypyidaw": "myanmar",
    # Mongolia (route doc covers ulaanbaatar).
    "gobi desert": "mongolia", "terelj national park": "mongolia",
    "lake khovsgol": "mongolia",
    # China (route docs cover beijing/xian/chengdu/guilin/kunming/shanghai/harbin as
    # origins). Hong Kong and Macau are deliberately NOT mapped here - they run
    # separate immigration, visa and currency regimes from mainland China, so
    # resolving them to "china" would silently apply the wrong visa rules and
    # coverage data.
    "datong": "china", "lhasa": "china", "yangshuo": "china",
    "dali": "china", "lijiang": "china", "shangri-la": "china",
    "suzhou": "china", "hangzhou": "china",
    # Bhutan (no route doc - see tips-bhutan-overview, no independent circuit).
    "thimphu": "bhutan", "paro": "bhutan", "punakha": "bhutan",
    # Australia (route docs cover sydney/cairns/melbourne/byron bay as origins).
    "whitsundays": "australia", "airlie beach": "australia", "great ocean road": "australia",
    "uluru": "australia", "tasmania": "australia", "hobart": "australia",
    "gold coast": "australia", "port douglas": "australia", "daintree": "australia",
    "blue mountains": "australia", "katoomba": "australia", "perth": "australia",
    "adelaide": "australia", "darwin": "australia", "townsville": "australia",
    "mission beach": "australia",
    # New Zealand (route docs cover auckland/queenstown/wellington/rotorua as origins).
    "bay of islands": "new zealand", "waiheke island": "new zealand",
    "milford sound": "new zealand", "wanaka": "new zealand", "te anau": "new zealand",
    "dunedin": "new zealand", "nelson": "new zealand", "abel tasman": "new zealand",
    "taupo": "new zealand", "picton": "new zealand", "franz josef": "new zealand",
    "fiordland": "new zealand",
    # South Korea (route docs cover seoul/busan/jeju as origins).
    "gyeongju": "south korea", "incheon": "south korea", "dmz": "south korea",
    # Japan (route docs cover tokyo/kyoto/osaka/hiroshima as origins).
    "nara": "japan", "hakone": "japan", "nikko": "japan", "kamakura": "japan",
    "okinawa": "japan", "naha": "japan", "miyajima": "japan", "kobe": "japan",
    "fukuoka": "japan",
    # Peru (route docs cover lima/cusco/arequipa as origins).
    "huacachina": "peru", "nazca": "peru", "puno": "peru", "machu picchu": "peru",
    "colca canyon": "peru", "ica": "peru", "paracas": "peru", "ollantaytambo": "peru",
    "aguas calientes": "peru", "rainbow mountain": "peru",
    # Colombia (route docs cover bogota/medellin/cartagena as origins).
    "santa marta": "colombia", "tayrona": "colombia", "guatape": "colombia",
    "salento": "colombia", "san gil": "colombia", "getsemani": "colombia",
    "palomino": "colombia", "cocora valley": "colombia",
    # Ecuador (route docs cover quito/banos/cuenca as origins).
    "galapagos islands": "ecuador", "guayaquil": "ecuador", "mindo": "ecuador",
    "montanita": "ecuador", "otavalo": "ecuador", "quilotoa": "ecuador",
    "coca": "ecuador", "santa cruz island": "ecuador", "isabela island": "ecuador",
    # Bolivia (route docs cover la paz/uyuni/sucre as origins).
    "potosi": "bolivia", "copacabana bolivia": "bolivia", "rurrenabaque": "bolivia",
    "tupiza": "bolivia", "villazon": "bolivia",
    # Chile (route docs cover santiago/san pedro de atacama/puerto natales as origins).
    "valparaiso": "chile", "torres del paine": "chile", "pucon": "chile",
    "punta arenas": "chile", "calama": "chile",
    # Argentina (route docs cover buenos aires/mendoza/bariloche/el calafate as origins).
    "ushuaia": "argentina", "salta": "argentina", "puerto iguazu": "argentina",
    "iguazu falls": "argentina", "cordoba argentina": "argentina", "cafayate": "argentina",
    "perito moreno glacier": "argentina",
    # Brazil (route docs cover rio de janeiro/salvador/florianopolis/sao paulo/
    # manaus/jericoacoara as origins).
    "foz do iguacu": "brazil", "ilha grande": "brazil", "paraty": "brazil",
    "ouro preto": "brazil", "morro de sao paulo": "brazil", "ilhabela": "brazil",
    "anavilhanas archipelago": "brazil", "belem": "brazil",
    "lencois maranhenses": "brazil", "fortaleza": "brazil", "natal": "brazil",
    # South Africa (route docs cover cape town/johannesburg/hazyview/durban as
    # origins).
    "stellenbosch": "south africa", "franschhoek": "south africa",
    "hermanus": "south africa", "gansbaai": "south africa",
    "knysna": "south africa", "wilderness": "south africa",
    "plettenberg bay": "south africa", "garden route": "south africa",
    "soweto": "south africa", "pretoria": "south africa",
    "kruger national park": "south africa", "blyde river canyon": "south africa",
    "panorama route": "south africa", "drakensberg": "south africa",
    "wild coast": "south africa", "coffee bay": "south africa",
    "st lucia": "south africa", "isimangaliso wetland park": "south africa",
    "hluhluwe": "south africa", "robben island": "south africa",
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

