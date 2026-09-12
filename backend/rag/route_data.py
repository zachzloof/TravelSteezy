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
        June-September when green, September-October when golden) with a local guide
        from one of the H'mong or Dao villages.
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
        Gilis - getting around is on foot, bicycle, or horse-cart (cidomo), which is
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
        Siem Reap is 3-4h. Phnom Penh is 5-6h. West to Poipet (2-3h) puts you at the
        land border for an 8-9h onward bus to Bangkok - officials here routinely ask
        for extra "processing fees", same as at the Siem Reap side of this border.
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
        alternative to Kalaw for those who've already done the Inle approach. Mandalay
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
    # Bhutan (no route doc - see tips-bhutan-overview, no independent circuit).
    "thimphu": "bhutan", "paro": "bhutan", "punakha": "bhutan",
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

