"""Curated seed corpus for the RAG store.

Scope: the Southeast Asia backpacker circuit plus two common add-ons (Nepal,
Sri Lanka). Deliberately backpacker-angled - hostels, night buses, slow boats,
free/cheap things to do, scam and safety notes - rather than package-tourist
content, because one of the eval failure modes is "gave generic tourist advice".

Every document carries:
  content_type : visa | seasonal | tips
  destination  : country name (lowercase)
  region       : broad region, for coarse filtering
  nationalities: for visa docs, which passports the text covers

Accuracy note: visa rules and prices change. These are indicative figures
compiled as course seed data, and the agents are instructed to tell the user to
confirm with the official embassy source before travelling.
"""
from __future__ import annotations

from typing import Any

WESTERN_PASSPORTS = ["united kingdom", "usa", "australia", "canada", "ireland", "new zealand"]


def _doc(
    doc_id: str,
    text: str,
    content_type: str,
    destination: str,
    region: str = "southeast asia",
    **extra: Any,
) -> dict[str, Any]:
    return {
        "id": doc_id,
        "text": text.strip(),
        "metadata": {
            "content_type": content_type,
            "destination": destination.lower(),
            "region": region.lower(),
            **extra,
        },
    }


# --------------------------------------------------------------------------- #
# VISA
# --------------------------------------------------------------------------- #
VISA_DOCS = [
    _doc(
        "visa-thailand-western",
        """
        Thailand visa exemption: holders of UK, US, Australian, Canadian, Irish and New
        Zealand passports enter visa-free for 60 days on arrival by air or land, extendable
        once at an immigration office inside Thailand for a further 30 days (fee around
        1,900 THB). Land border crossings used to be limited to shorter stays, so confirm
        the current land-entry allowance before doing a border run. Proof of onward travel
        within the permitted window is occasionally requested at check-in by budget airlines
        even when immigration does not ask. Overstaying carries a 500 THB per day fine,
        payable at the airport, and overstays beyond 90 days trigger re-entry bans.
        Backpacker note: the standard "visa run" to Vientiane, Penang or Phnom Penh is a
        routine part of long stays, but consecutive back-to-back land entries attract
        scrutiny from immigration officers.
        """,
        "visa",
        "thailand",
        nationalities=WESTERN_PASSPORTS,
    ),
    _doc(
        "visa-vietnam-western",
        """
        Vietnam e-visa: UK, US, Australian, Canadian, Irish and New Zealand passport holders
        must arrange an e-visa in advance through the official government portal
        (evisa.gov.vn). It grants up to 90 days, single or multiple entry, and costs roughly
        USD 25 single entry / USD 50 multiple entry. Processing typically takes 3-5 working
        days, so this is the destination most likely to be ruled out by a short-notice plan.
        UK, French, German, Italian, Spanish and Nordic citizens have separately enjoyed
        short visa-free stays (up to 45 days) under a unilateral exemption scheme that has
        been renewed periodically - check whether it is currently in force, because it
        changes. Beware unofficial visa websites charging large markups; only evisa.gov.vn
        is the government site. Your passport must have 6 months validity remaining.
        """,
        "visa",
        "vietnam",
        nationalities=WESTERN_PASSPORTS,
        lead_time_days=5,
    ),
    _doc(
        "visa-cambodia-western",
        """
        Cambodia e-visa and visa on arrival: all Western passports (UK, US, Australia,
        Canada, Ireland, New Zealand) get a 30-day tourist visa (type T) on arrival at
        Phnom Penh and Siem Reap airports and at major land borders, costing USD 30 plus a
        passport photo. An e-visa is available online for about USD 36 and speeds up
        airport arrival. Extendable once for 30 days inside the country. Land borders,
        especially Poipet from Thailand, are notorious for officials requesting extra
        "processing fees" of a few dollars, often demanded in Thai baht - paying in exact
        USD and politely declining the extra usually works. Carry USD cash: land borders
        frequently have no working card facilities.
        """,
        "visa",
        "cambodia",
        nationalities=WESTERN_PASSPORTS,
    ),
    _doc(
        "visa-laos-western",
        """
        Laos visa on arrival: available to UK, US, Australian, Canadian, Irish and New
        Zealand passport holders at international airports and main land borders for
        USD 30-42 depending on nationality, valid 30 days, extendable twice by 30 days each
        at the immigration office in Vientiane. An e-visa exists but the visa on arrival is
        usually simpler for overland arrivals. Bring a passport photo and USD cash; paying
        in kip or baht attracts a poor rate. The Huay Xai land border is the entry point for
        the two-day Mekong slow boat to Luang Prabang.
        """,
        "visa",
        "laos",
        nationalities=WESTERN_PASSPORTS,
    ),
    _doc(
        "visa-indonesia-western",
        """
        Indonesia visa on arrival (B1): UK, US, Australian, Canadian, Irish and New Zealand
        passport holders buy a 30-day visa on arrival for IDR 500,000 (about USD 35),
        extendable once for another 30 days either online through the e-VOA portal or in
        person at an immigration office - the in-person extension takes three visits over
        about a week, which matters if you are on a tight schedule. An e-VOA bought before
        flying speeds up arrival at Bali's Ngurah Rai airport, where the on-arrival queue
        can run over an hour at peak times. Passport needs 6 months validity and proof of
        onward travel is checked reasonably often at Bali immigration.
        """,
        "visa",
        "indonesia",
        nationalities=WESTERN_PASSPORTS,
    ),
    _doc(
        "visa-malaysia-western",
        """
        Malaysia: visa-free entry for 90 days for UK, US, Australian, Canadian, Irish and
        New Zealand passport holders - the most generous allowance on the SE Asia circuit,
        which makes Malaysia a useful place to sit out a rainy month elsewhere or to reset
        a regional itinerary. All arrivals must complete the Malaysia Digital Arrival Card
        (MDAC) online within three days before arrival; it is free and takes five minutes,
        but travellers are regularly caught out by not having done it. Penang is a classic
        visa-run destination for people on long Thailand stays.
        """,
        "visa",
        "malaysia",
        nationalities=WESTERN_PASSPORTS,
    ),
    _doc(
        "visa-philippines-western",
        """
        Philippines: 30 days visa-free on arrival for UK, US, Australian, Canadian, Irish
        and New Zealand passport holders, extendable in-country at a Bureau of Immigration
        office up to a total of 36 months, though each extension costs roughly PHP 3,000
        and involves queueing. Onward or return ticket within the permitted stay is
        genuinely enforced at check-in by airlines, more strictly than almost anywhere else
        in the region - budget travellers routinely buy a cheap throwaway onward flight.
        An eTravel registration must be completed online within 72 hours before arrival.
        """,
        "visa",
        "philippines",
        nationalities=WESTERN_PASSPORTS,
    ),
    _doc(
        "visa-nepal-western",
        """
        Nepal visa on arrival at Kathmandu Tribhuvan airport and land borders for all
        Western passports: USD 30 for 15 days, USD 50 for 30 days, USD 125 for 90 days,
        payable in cash (USD preferred, most major currencies accepted). Fill the online
        pre-arrival form to skip a queue. Separately, trekking requires permits: a TIMS card
        plus a conservation area permit (ACAP for Annapurna, Sagarmatha permit for Everest
        region), bought in Kathmandu or Pokhara - budget roughly USD 50-70 in permits for a
        standard Annapurna trek, and note that solo trekking rules in some regions now
        require a licensed guide.
        """,
        "visa",
        "nepal",
        region="south asia",
        nationalities=WESTERN_PASSPORTS,
    ),
    _doc(
        "visa-srilanka-western",
        """
        Sri Lanka ETA (Electronic Travel Authorisation): required in advance for UK, US,
        Australian, Canadian, Irish and New Zealand passport holders, applied for online,
        typically around USD 50 for a 30-day double-entry tourist ETA, approved within a day
        or two. Extendable to 90 days at the immigration department in Colombo. Apply only
        through the official eta.gov.lk site - the search results are full of agent sites
        charging double. Passport must have 6 months validity.
        """,
        "visa",
        "sri lanka",
        region="south asia",
        nationalities=WESTERN_PASSPORTS,
        lead_time_days=2,
    ),
]

# --------------------------------------------------------------------------- #
# SEASONAL / SAFETY
# --------------------------------------------------------------------------- #
SEASONAL_DOCS = [
    _doc(
        "seasonal-thailand",
        """
        Thailand has two different weather systems and people constantly get caught out by
        it. The Andaman coast (Phuket, Krabi, Koh Lanta, Koh Phi Phi) has its southwest
        monsoon roughly May to October, with the worst rain and rough seas in September and
        October; ferries are cancelled and some islands largely shut. The Gulf coast (Koh
        Samui, Koh Phangan, Koh Tao) runs on a different cycle and is wettest November to
        December, so November is a bad month for the Gulf islands but a fine one for the
        Andaman side. The north (Chiang Mai, Pai) is pleasant November to February, hot in
        March and April, and suffers a serious burning season in March and April when air
        quality in Chiang Mai regularly becomes among the worst in the world - genuinely
        worth avoiding if you have any respiratory sensitivity. Songkran, the water festival
        in mid-April, is the busiest and most expensive week of the year.
        """,
        "seasonal",
        "thailand",
        monsoon_months=[5, 6, 7, 8, 9, 10],
    ),
    _doc(
        "seasonal-vietnam",
        """
        Vietnam is long enough that there is no single season for the whole country. The
        north (Hanoi, Sapa, Ha Giang) is cold and misty December to February - Sapa can drop
        near freezing and the rice terraces are bare; the terraces are green in June to
        September and golden in late September. Central Vietnam (Hue, Hoi An, Da Nang) has a
        distinct typhoon and flood season from September to November, and Hoi An's old town
        genuinely floods most years. The south (Ho Chi Minh City, Mekong Delta) has a wet
        season May to November, usually short heavy afternoon downpours rather than all-day
        rain, so it remains very travellable. The overall sweet spot for doing the whole
        country in one run is February to April.
        """,
        "seasonal",
        "vietnam",
        monsoon_months=[9, 10, 11],
    ),
    _doc(
        "seasonal-cambodia",
        """
        Cambodia's wet season runs May to October, peaking in September and October when
        rural roads around Ratanakiri and Mondulkiri turn to mud and some are impassable.
        The upside is that Angkor's moats and the Tonle Sap are full, the temples are green
        and far less crowded, and guesthouse prices drop noticeably. November to February is
        dry and comfortable and is peak season with peak prices. March to May is brutally
        hot - Angkor in April at 38-40C is genuinely punishing if you are cycling between
        temples, which is what most backpackers do.
        """,
        "seasonal",
        "cambodia",
        monsoon_months=[5, 6, 7, 8, 9, 10],
    ),
    _doc(
        "seasonal-laos",
        """
        Laos is wet from May to October and dry from November to April. The Mekong slow boat
        from Huay Xai to Luang Prabang runs year round but is most pleasant November to
        February. Like northern Thailand, Laos has a burning season in March and April when
        hill-country haze around Luang Prabang and Vang Vieng can obscure the views people
        come for and air quality deteriorates badly. December and January nights in the
        northern hills are genuinely cold and most budget guesthouses have no heating -
        bring a warm layer, which surprises people arriving from the tropics.
        """,
        "seasonal",
        "laos",
        monsoon_months=[5, 6, 7, 8, 9, 10],
    ),
    _doc(
        "seasonal-indonesia",
        """
        Bali and most of Indonesia have a wet season November to March, peaking January and
        February with heavy afternoon rain and some road flooding; it rarely rains all day,
        so travel is still workable but surf and diving conditions suffer and the Gili
        crossing gets rough. Dry season April to October is peak, with July and August the
        busiest and priciest weeks of the year across Canggu, Ubud and the Gilis. Komodo
        diving is best April to November. Note the wet-season swell direction flips which
        side of Bali has good surf: dry season favours the west coast (Uluwatu, Canggu),
        wet season favours the east (Nusa Dua, Sanur, Keramas).
        """,
        "seasonal",
        "indonesia",
        monsoon_months=[11, 12, 1, 2, 3],
    ),
    _doc(
        "seasonal-malaysia",
        """
        Malaysia splits by coast. The east coast and islands (Perhentians, Redang, Tioman)
        have a northeast monsoon from roughly November to February during which the
        Perhentians essentially close - boats stop, most guesthouses shut, and turning up is
        pointless. The west coast (Penang, Langkawi) and Borneo are travellable year round
        with heavier rain September to November. Kuala Lumpur and the Cameron Highlands are
        fine any time. Because Malaysia's bad months are the opposite of the Andaman coast's
        bad months, it pairs naturally with Thailand for anyone stuck waiting out weather.
        """,
        "seasonal",
        "malaysia",
        monsoon_months=[11, 12, 1, 2],
    ),
    _doc(
        "seasonal-philippines",
        """
        The Philippines has a typhoon season from roughly June to November, peaking August
        to October, and this is the single most disruptive weather risk in Southeast Asia -
        typhoons cancel inter-island ferries and domestic flights at short notice, which can
        strand you for days with a non-refundable onward ticket. Ferry cancellations are the
        real planning problem, more than the rain itself. The dry season, December to May,
        is the reliable window; El Nido and Coron are at their best March to May. Note that
        Palawan sits slightly outside the main typhoon track and is often fine when Luzon
        and the Visayas are not.
        """,
        "seasonal",
        "philippines",
        monsoon_months=[6, 7, 8, 9, 10, 11],
        hazard="typhoon",
    ),
    _doc(
        "seasonal-nepal",
        """
        Nepal's trekking seasons are narrow and matter enormously. October and November are
        the prime window: stable weather, clear mountain views, busy trails. March to May is
        the second window, warmer with rhododendron blooms but hazier views. The monsoon,
        June to September, makes trekking genuinely miserable and dangerous in places -
        leeches, landslides, cloud-obscured views, and flight cancellations to Lukla. Winter,
        December to February, is clear but bitterly cold at altitude and high passes such as
        Thorong La can be snowed shut. Recommending Nepal trekking in July or August is a
        clear seasonal mistake.
        """,
        "seasonal",
        "nepal",
        region="south asia",
        monsoon_months=[6, 7, 8, 9],
    ),
    _doc(
        "seasonal-srilanka",
        """
        Sri Lanka has two monsoons hitting opposite coasts, so there is almost always
        somewhere good to be. The southwest monsoon (May to September) soaks the west and
        south coasts and the hill country, while the east coast (Arugam Bay, Trincomalee) is
        at its best then - Arugam Bay's surf season is precisely May to September. The
        northeast monsoon (October to January) reverses it: the south and west coasts
        (Mirissa, Unawatuna, Galle) are good December to March while the east shuts down.
        The mistake to avoid is planning a single loop of the whole island in one trip and
        hitting the wrong coast at the wrong time.
        """,
        "seasonal",
        "sri lanka",
        region="south asia",
        monsoon_months=[5, 6, 7, 8, 9],
    ),
]

# --------------------------------------------------------------------------- #
# BACKPACKER TIPS / ROUTES / BUDGET
# --------------------------------------------------------------------------- #
TIPS_DOCS = [
    _doc(
        "tips-thailand",
        """
        Thailand backpacker notes. Daily budget: shoestring 700-1,000 THB (dorm, street
        food, local transport), mid 1,500-2,500 THB. Dorms run 200-400 THB in Chiang Mai and
        400-700 THB on the islands. Free and cheap: Chiang Mai's temples and the Sunday
        Walking Street, monk chats at Wat Suan Dok, Doi Suthep by songthaew, Bangkok's Wat
        Pho area on foot, Lumphini Park, and the free ferry crossings on the Chao Phraya.
        Skip the tiger and elephant-riding attractions; the ethical alternative most
        backpackers use is an observation-only elephant sanctuary, which costs more but is
        the standard advice in every hostel. Overnight trains Bangkok-Chiang Mai in second
        class sleeper cost around 800-1,000 THB and save a night's accommodation. Standard
        circuit: Bangkok - Chiang Mai - Pai, then fly or bus south to the islands. Scam
        watch: the "Grand Palace is closed today" tuk-tuk gem scam is still running.
        """,
        "tips",
        "thailand",
        budget_shoestring_usd=22,
    ),
    _doc(
        "tips-vietnam",
        """
        Vietnam backpacker notes. Daily budget: shoestring USD 20-25, mid USD 35-50. Dorms
        USD 5-9. The classic route is a north-to-south (or reverse) run: Hanoi - Ha Giang
        loop - Ninh Binh - Phong Nha - Hue - Hoi An - Da Lat - Ho Chi Minh City - Mekong.
        The Ha Giang loop, three or four days by motorbike with an easy-rider driver if you
        cannot ride, is the thing most backpackers name as the highlight of the country, and
        it costs around USD 100-150 all in. Sleeper buses are cheap and ubiquitous but
        genuinely uncomfortable if you are over about 180cm; the reunification train is
        slower and much more pleasant. Phong Nha's caves are world class and still cheap to
        visit at the Paradise Cave and Dark Cave level. Bank on losing a day to the Hanoi
        traffic before you find your feet. Avoid booking bus tickets through hostels at a
        markup when the Futa/Phuong Trang app is cheaper.
        """,
        "tips",
        "vietnam",
        budget_shoestring_usd=22,
    ),
    _doc(
        "tips-cambodia",
        """
        Cambodia backpacker notes. Daily budget: shoestring USD 20-25, mid USD 35-45; the
        Angkor pass is the single biggest line item at USD 37 for one day, USD 62 for three.
        Buy the three-day pass and use it across a week, and go in at 5am for sunrise at
        Angkor Wat then do the outer temples in the afternoon when the tour buses have gone.
        Kampot and Kep are the quiet, cheap, slow-travel stop most people wish they had
        given more time. Koh Rong Sanloem is the calmer alternative to party-heavy Koh Rong.
        Phnom Penh's Tuol Sleng and Choeung Ek are essential and emotionally heavy - plan a
        light evening afterwards. Cash is king: USD for anything over a dollar, riel as
        small change. Safety note: bag-snatching from moving motorbikes is a real and
        frequent problem in Phnom Penh - do not walk with a phone out or a bag on the road
        side of the pavement.
        """,
        "tips",
        "cambodia",
        budget_shoestring_usd=22,
    ),
    _doc(
        "tips-laos",
        """
        Laos backpacker notes. Daily budget: shoestring USD 18-25, the cheapest country on
        the circuit alongside Cambodia. The two-day Mekong slow boat from Huay Xai to Luang
        Prabang (around USD 35, overnight stop in Pakbeng) is the classic arrival from
        Thailand - bring a cushion and food. Luang Prabang: Kuang Si falls, the morning alms
        procession watched respectfully from a distance and never with a flash, and Mount
        Phousi at sunset. Vang Vieng has shifted from the infamous tubing scene to
        kayaking, caves and ballooning and is worth a stop again. The new China-Laos high
        speed railway (Vientiane-Vang Vieng-Luang Prabang-Boten) has cut journeys from ten
        hours to under two and is cheap, but tickets sell out days ahead in peak season and
        buying them requires either an app or an agent. Unexploded ordnance remains a real
        hazard in the east - stay on marked paths around the Plain of Jars.
        """,
        "tips",
        "laos",
        budget_shoestring_usd=20,
    ),
    _doc(
        "tips-indonesia",
        """
        Indonesia backpacker notes. Daily budget: shoestring USD 22-30 on Bali, less on Java
        and Sumatra. Bali dorms USD 7-12, and Canggu's hostel scene is the social centre for
        long-stay backpackers and digital nomads. Beyond Bali: Nusa Penida as a day or
        overnight trip, the Gilis for cheap diving (Gili Trawangan for the scene, Gili Air
        for the balance, Gili Meno for quiet), and on Java the Mount Bromo and Ijen crater
        blue-fire sunrise pairing, usually done as a two-night tour from Yogyakarta or
        Probolinggo. Yogyakarta itself is the cheap culture stop for Borobudur and Prambanan.
        Renting a scooter is standard at around USD 5 a day, but police stops targeting
        foreigners without an international driving permit are routine in Bali, and your
        travel insurance will not pay out for a scooter accident if you were not licensed to
        ride - this is the single most common way backpackers get badly hurt in the region.
        """,
        "tips",
        "indonesia",
        budget_shoestring_usd=25,
    ),
    _doc(
        "tips-malaysia",
        """
        Malaysia backpacker notes. Daily budget: shoestring USD 25-30, slightly above its
        neighbours but with much better infrastructure. Penang's George Town is the big draw
        - street art, clan jetties, and hawker food that is the best-value eating in the
        region at a few dollars a meal; Penang alone justifies the stop. The Cameron
        Highlands offer cheap tea-plantation walks and cool air. Taman Negara is accessible
        rainforest with a canopy walkway. In Borneo, Sepilok's orangutan centre and the
        Kinabatangan river cruise are the wildlife highlights, and Mount Kinabalu is a
        two-day climb that must be booked months ahead with a mandatory guide and permit.
        Intercity buses are comfortable and cheap and the KL-Singapore and KL-Penang runs
        are painless. Malaysia is the easy-mode stop when you want a week of good transport,
        fast wifi and no visa pressure.
        """,
        "tips",
        "malaysia",
        budget_shoestring_usd=28,
    ),
    _doc(
        "tips-philippines",
        """
        Philippines backpacker notes. Daily budget: shoestring USD 25-35 - higher than
        mainland SE Asia because inter-island flights and boats add up and there is no cheap
        overland alternative. Budget for domestic flights (Cebu Pacific sales) rather than
        assuming buses. Highlights on the backpacker route: El Nido and Coron island-hopping
        tours (the standard Tour A/B/C/D menu, around PHP 1,200-1,800 each), Siargao for
        surfing and the cheapest long-stay scene, Moalboal for the sardine run and free
        shore snorkelling, Kawasan falls canyoneering, and the Banaue and Batad rice terraces
        in the north of Luzon. The Palawan underground river needs a permit arranged ahead.
        Bring cash outside the cities; ATMs on small islands run dry and charge PHP 250 per
        withdrawal with a low limit.
        """,
        "tips",
        "philippines",
        budget_shoestring_usd=30,
    ),
    _doc(
        "tips-nepal",
        """
        Nepal backpacker notes. Daily budget: shoestring USD 20-25 in Kathmandu and Pokhara,
        rising to USD 30-40 a day on a teahouse trek once you add food at altitude, where
        prices climb the higher you walk. The Annapurna Base Camp trek (7-12 days) and the
        Poon Hill trek (4-5 days) are the accessible classics; Everest Base Camp (12-14 days)
        needs the Lukla flight, which is weather-dependent and regularly delayed - build in
        buffer days or you will miss an onward international flight. Teahouse trekking means
        you need no tent or cooking kit, which keeps costs down. Kathmandu's Thamel is where
        you rent or buy gear cheaply, and renting a down jacket and sleeping bag for a couple
        of dollars a day beats carrying your own across Asia. Altitude sickness is the real
        risk, not the walking: ascend slowly above 3,000m and know that Diamox is widely
        available in Thamel pharmacies.
        """,
        "tips",
        "nepal",
        region="south asia",
        budget_shoestring_usd=22,
    ),
    _doc(
        "tips-srilanka",
        """
        Sri Lanka backpacker notes. Daily budget: shoestring USD 20-30. The Kandy to Ella
        train through the tea country is the single best cheap experience in the country -
        book a reserved second-class seat a few days ahead, or ride third class unreserved
        and stand at the door. Ella for Little Adam's Peak and the Nine Arches Bridge,
        Mirissa for whale watching (season November to April), Arugam Bay for surf (May to
        September), Sigiriya rock or the cheaper Pidurangala alternative directly opposite
        with a better view of Sigiriya itself, and Adam's Peak climbed overnight for sunrise
        during the December to May pilgrimage season. Tuk-tuk rental for self-driving is
        popular and cheap but requires a local permit. Buses are extremely cheap and
        extremely crowded. Guesthouses and family homestays, rather than hostels, are the
        norm outside the main backpacker towns and are often better value.
        """,
        "tips",
        "sri lanka",
        region="south asia",
        budget_shoestring_usd=25,
    ),
    _doc(
        "tips-route-sea-overland",
        """
        The standard Southeast Asia overland circuit and how long it actually takes. The
        "banana pancake trail" loop runs Bangkok - Chiang Mai - (slow boat via Huay Xai) -
        Luang Prabang - Vang Vieng - Vientiane - (bus or train) - Hanoi - south through
        Vietnam to Ho Chi Minh City - Phnom Penh - Siem Reap - back to Bangkok, and doing it
        properly takes about three months; two months is brisk, one month means flying
        several legs. Key overland realities: Bangkok to Siem Reap by bus is 8-9 hours plus
        an unpredictable border; Hanoi to Luang Prabang overland is a punishing 24 hours and
        most people fly it for around USD 100; Ho Chi Minh City to Phnom Penh is an easy
        6-hour bus with a straightforward border; the Laos high-speed rail has made
        Vientiane to Luang Prabang a two-hour trip instead of ten. Budget airlines (AirAsia,
        VietJet, Scoot) frequently undercut a 20-hour bus once you price in the lost day, so
        the "always go overland to save money" instinct is often wrong for the long legs.
        """,
        "tips",
        "southeast asia",
    ),
    _doc(
        "tips-safety-sea-general",
        """
        Region-wide backpacker safety and money notes for Southeast Asia. Scooter accidents
        are by a wide margin the most common cause of serious injury to backpackers; most
        travel insurance policies void scooter claims unless you hold a licence valid for
        that engine size and were wearing a helmet. Methanol poisoning from adulterated
        spirits in cheap buckets and free-pour shots has killed backpackers in Laos,
        Indonesia and Thailand - stick to beer or bottled drinks you see opened in party
        towns. Dengue is a bigger practical risk than malaria on the standard circuit and
        there is no prophylaxis, so daytime mosquito repellent matters. On money: ATMs in
        Thailand charge a flat 220 THB foreign card fee per withdrawal regardless of amount,
        so take the maximum out at once; always decline dynamic currency conversion when the
        machine offers to bill you in your home currency. Border-crossing scams cluster at
        Poipet (Thailand-Cambodia) and at the Laos slow-boat ticket offices. Keep a
        photographed copy of your passport and a spare card separate from your wallet.
        """,
        "tips",
        "southeast asia",
    ),
]

SEED_DOCUMENTS: list[dict[str, Any]] = VISA_DOCS + SEASONAL_DOCS + TIPS_DOCS


def documents_by_type(content_type: str) -> list[dict[str, Any]]:
    return [d for d in SEED_DOCUMENTS if d["metadata"]["content_type"] == content_type]


KNOWN_DESTINATIONS = sorted(
    {d["metadata"]["destination"] for d in SEED_DOCUMENTS if d["metadata"]["destination"]}
)
