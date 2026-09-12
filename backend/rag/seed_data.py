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
    _doc(
        "visa-india-western",
        """
        India e-Visa: UK, US, Australian, Canadian, Irish and New Zealand passport
        holders apply online for an e-Tourist Visa before travel - there is no visa
        on arrival for these nationalities. Options are 30 days (double entry, around
        USD 25-40), 1 year (multiple entry, around USD 40-80) or 5 years (multiple
        entry, around USD 80-120), with the 1-year and 5-year versions capping any
        single stay at 90 days (180 for US, UK and Japanese citizens) regardless of
        the visa's overall validity. Apply only at the official indianvisaonline.gov.in
        - third-party sites charge large markups. Processing is officially "within
        72 hours" but budget 4-5 working days in practice, and note a fixed number of
        designated entry airports/ports apply to e-Visa holders. Passport needs 6
        months validity and two blank pages. Registration (FRRO) is generally not
        required for stays under 180 days on a tourist e-Visa.
        """,
        "visa",
        "india",
        region="south asia",
        nationalities=WESTERN_PASSPORTS,
        lead_time_days=5,
    ),
    _doc(
        "visa-mongolia-western",
        """
        Mongolia visa-free entry: UK, US, and most EU passport holders can enter
        visa-free for tourism - UK citizens get 30 days, but the popular allowance
        varies by nationality and by exactly which bilateral agreement is current, so
        confirm your specific nationality's allowance before flying since these
        agreements are renewed and occasionally lapse. Canadian, Australian and New
        Zealand passport holders have historically needed to apply for a visa in
        advance through a Mongolian embassy or consulate (around USD 50-80, several
        working days), so do not assume visa-free purely from being "Western" -
        check per passport. Extensions beyond the visa-free window are handled at the
        Immigration Agency office in Ulaanbaatar. Land border crossings from Russia
        and China exist but have limited operating hours and are far less
        straightforward than flying into Ulaanbaatar's Chinggis Khaan airport.
        """,
        "visa",
        "mongolia",
        region="east asia",
        nationalities=WESTERN_PASSPORTS,
    ),
    _doc(
        "visa-myanmar-western",
        """
        Myanmar e-Visa: UK, US, Australian, Canadian, Irish and New Zealand passport
        holders can apply online for a tourist e-Visa (around USD 50, 28 days,
        single entry, processing a few working days), entering through Yangon,
        Mandalay or Naypyidaw international airports. IMPORTANT SAFETY CONTEXT, not
        just a bureaucratic note: Myanmar has been in a state of civil war and
        military rule since the February 2021 coup, and most Western governments
        (UK FCDO, US State Department, Australian DFAT) advise against all but
        essential travel to large parts of the country outside the main tourist
        circuit (Yangon, Bagan, Mandalay, Inle Lake), citing armed conflict, arbitrary
        detention risk, and patchy insurance coverage in conflict-affected states and
        regions. Internal flights and overland routes between the main tourist towns
        can be curtailed at short notice depending on the security situation. Check
        current government travel advisories immediately before booking, not months
        in advance - this situation moves fast and this document cannot track it.
        """,
        "visa",
        "myanmar",
        nationalities=WESTERN_PASSPORTS,
        lead_time_days=4,
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
    _doc(
        "seasonal-india",
        """
        North and central India (Delhi, Rajasthan, Agra, Varanasi, Uttarakhand foothills)
        has three seasons, not two: a pleasant, dry, cool winter (October to March, the
        best window for almost everything except beaches - Rajasthan in December can drop
        near freezing at night in the desert); a brutal pre-monsoon hot season (April to
        June) when Rajasthan and the Gangetic plain regularly hit 43-47C and daytime
        sightseeing becomes genuinely dangerous; and the monsoon (roughly late June to
        September) which cools things down but brings heavy rain, humidity and flooding
        risk, especially in the hills. The Himalayan trekking regions (Himachal, Ladakh,
        Uttarakhand) invert this: Ladakh's short season is June to September precisely
        because it is a high-altitude desert cut off by snow the rest of the year, while
        Himachal trekking (Kasol, Tosh, the Parvati Valley) is best May-June and
        September-October, avoiding both winter snow and the monsoon.
        """,
        "seasonal",
        "india",
        region="south asia",
        monsoon_months=[6, 7, 8, 9],
    ),
    _doc(
        "seasonal-india-south",
        """
        South India and the west coast (Goa, Kerala, Karnataka, Tamil Nadu) run on the
        opposite clock to the north. The southwest monsoon hits Kerala first and hardest,
        roughly June to September, with Goa's beach shacks and most water-based tourism
        shutting down for the season - many close completely from June to September and
        rebuild for the winter. The dry season, October/November to March, is peak
        season for Goa and Kerala's backwaters alike, with December-January the most
        expensive and crowded stretch (Goa's New Year parties especially). Tamil Nadu's
        east coast gets a second, separate northeast monsoon October to December,
        driven by the retreating monsoon crossing the Bay of Bengal, which can bring
        cyclones - check forecasts specifically if travelling the Tamil Nadu coast in
        that window, since it does not follow the west coast's calendar at all.
        """,
        "seasonal",
        "india",
        region="south asia",
        monsoon_months=[6, 7, 8, 9],
    ),
    _doc(
        "seasonal-mongolia",
        """
        Mongolia has one short travel season and everything else is a hard closure. The
        window is late May to early September, and even within it July and August are
        the only months most Gobi Desert and steppe tour operators run full itineraries,
        because the shoulder months bring cold nights and unpredictable early/late snow.
        Winters (November to March) are ferociously cold - Ulaanbaatar is one of the
        coldest capital cities on Earth, regularly below -20C, and most tourist
        infrastructure outside the capital simply closes. The Naadam festival (July)
        is the single best-known cultural event and also the most expensive, busiest
        week to visit. Pack for enormous day-to-night temperature swings even in
        summer - a 30C desert afternoon in the Gobi can drop to near freezing overnight.
        """,
        "seasonal",
        "mongolia",
        region="east asia",
        monsoon_months=[],
    ),
    _doc(
        "seasonal-myanmar",
        """
        Myanmar's climate follows the same three-season pattern as its neighbours:
        a cool, dry season (November to February, the best time to visit - Bagan's
        temple sunrises are least hazy then), a hot season (March to May, often over
        40C in the central plain around Bagan and Mandalay), and a wet monsoon (June to
        October, heaviest on the Rakhine and Tanintharyi coasts and in the delta,
        lighter and more travellable in the central dry zone around Bagan and Mandalay
        which sits in a genuine rain shadow). Inle Lake's floating gardens and stilt
        villages are pleasant nearly year-round but coolest and clearest October to
        February. Whatever the season, current safety conditions (see the visa
        document's note on the post-2021 conflict) matter far more to a trip than the
        weather does - check government travel advisories before the forecast.
        """,
        "seasonal",
        "myanmar",
        monsoon_months=[6, 7, 8, 9, 10],
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
    _doc(
        "tips-india",
        """
        India backpacker notes. Daily budget: shoestring USD 15-25 - among the cheapest
        countries in Asia to travel if you eat and sleep like a local, though intercity
        distances are enormous, so budget real money for overnight trains and the
        occasional flight. The classic first-timer route is the "Golden Triangle plus"
        - Delhi, Agra (Taj Mahal at sunrise, before the tour buses), Jaipur and Pushkar -
        extendable west to Jodhpur, Udaipur and Jaisalmer for a full Rajasthan loop.
        Rishikesh (yoga, the Ganges, the Beatles Ashram) and Varanasi (the ghats at dawn,
        genuinely one of the most intense travel experiences in Asia) are the other two
        first-timer must-sees. Sleeper trains booked on the IRCTC app or via a hostel
        are the backbone of budget travel here; book the "Tatkal" quota if you left it
        late. Goa and Kerala's backwaters are the beach/relaxation leg, usually done
        separately from the north given the distance. Belly trouble in the first week
        is close to universal - stick to bottled or filtered water, freshly cooked hot
        food, and be cautious with roadside dairy. Train and hotel touts at major
        stations (especially Delhi and Agra) routinely claim your booked hotel is
        "closed" or "full" to redirect you to one paying them commission - confirm
        directly with your guesthouse if this happens, never trust the tout.
        """,
        "tips",
        "india",
        region="south asia",
        budget_shoestring_usd=20,
    ),
    _doc(
        "tips-mongolia",
        """
        Mongolia backpacker notes. Daily budget: shoestring USD 25-40 - cheaper than it
        looks on paper for food and guesthouses in Ulaanbaatar, but a multi-day Gobi or
        steppe tour (driver, guide, jeep, ger accommodation, all meals) is the main
        expense and typically runs USD 50-80 a day per person in a shared group, which
        is close to unavoidable since public transport barely reaches the sites that
        justify the trip. Independent budget travel is realistic in Ulaanbaatar itself
        but the Gobi Desert (Khongoryn Els sand dunes, the Flaming Cliffs), Lake
        Khövsgöl in the north, and the nomadic homestay experience genuinely require a
        driver-guide and 4x4 - hitchhiking and hostel-organised group tours (splitting
        a jeep 3-4 ways) are how budget travellers make this affordable. Terelj National
        Park, 1.5-2h from Ulaanbaatar, is the accessible taste of the steppe if time or
        budget doesn't stretch to the Gobi. Ger camps range from tourist-facing (with
        beds and stoves) to genuine nomadic family homestays, and the latter is what
        people mean when they say Mongolia was the highlight of a wider Asia trip.
        Cashmere is genuinely cheap and good quality in Ulaanbaatar's markets.
        """,
        "tips",
        "mongolia",
        region="east asia",
        budget_shoestring_usd=30,
    ),
    _doc(
        "tips-myanmar",
        """
        Myanmar backpacker notes, written alongside the safety context in the visa
        document - check current government travel advisories before treating any of
        this as current. Historically, daily budget: shoestring USD 20-30. The main
        circuit, when accessible, is Yangon (Shwedagon Pagoda at sunset, colonial
        downtown) - Bagan (thousands of temples across a plain, best seen by e-bike at
        sunrise, hot-air balloon flights are a splurge worth considering) - Mandalay
        (U Bein teak bridge at sunset, day trips to Amarapura and Sagaing) - Inle Lake
        (stilt villages, floating gardens, leg-rowing fishermen, and Kalaw as the
        trekking-in approach over 2-3 days instead of the bus). Domestic flights
        between these towns are common even for backpackers because overland travel
        between regions can be slow, restricted, or currently inadvisable depending on
        the security situation - this is not the country to wing overland routes on a
        whim the way you might in Thailand or Vietnam. Cash (crisp, unfolded USD plus
        local kyat) has historically been essential outside Yangon due to unreliable
        card and ATM infrastructure. This is a Buddhist-majority country where modest
        dress at temples (covered shoulders and knees, shoes off) is expected everywhere.
        """,
        "tips",
        "myanmar",
        budget_shoestring_usd=25,
    ),
    _doc(
        "tips-bhutan-overview",
        """
        Bhutan is deliberately not a shoestring-backpacker destination, and a traveller
        asking about it should be told that plainly rather than given a daily budget
        figure that doesn't apply. Independent budget travel is not possible: all
        tourists (except Indian, Bangladeshi and Maldivian nationals, who face separate
        rules) must book through a licensed Bhutanese tour operator and pay a
        Sustainable Development Fee (SDF) of USD 100 per person per night as of the
        post-2023 reduced rate (down from USD 200), on top of accommodation, food.
        transport and a guide, which the operator arranges as a package - there is no
        walk-in hostel scene or DIY overland route the way there is elsewhere on this
        circuit. A visa is arranged by the operator as part of booking, not applied for
        independently. The upside of the cost floor is a country that has deliberately
        avoided mass tourism: the Tiger's Nest monastery hike near Paro and the
        Punakha valley are the headline sights, and trekking (Druk Path, Jomolhari) is
        exceptional and uncrowded. For a genuinely budget-constrained backpacker, this
        is realistically a "save up for a short, focused trip" destination rather than
        part of an open-ended regional loop.
        """,
        "tips",
        "bhutan",
        region="south asia",
    ),
    _doc(
        "tips-connectivity-work-sea",
        """
        Connectivity and long-stay work notes across the Southeast/South Asia circuit.
        Physical SIM cards (AIS/dtac in Thailand, Viettel in Vietnam, Smart/Globe in
        the Philippines, Airtel/Jio in India) are cheap - typically USD 5-10 for a
        tourist SIM with several GB - and sold at every airport arrivals hall, usually
        faster than queueing for an eSIM provider's activation support. eSIMs (Airalo,
        Holafly) trade a small price premium for not needing a physical shop, and are
        the practical choice for a short multi-country hop where buying a new local SIM
        every few days is wasted effort. Coworking-adjacent cafe culture is strongest in
        Canggu and Ubud (Bali), Chiang Mai, and increasingly Da Nang and Ho Chi Minh
        City - these four towns are where the actual "digital nomad" scene concentrates,
        with reliable fibre wifi as a genuine selling point of specific hostels rather
        than an assumption. Long-stay visa options exist in a few places: Thailand's
        Destination Thailand Visa (DTV) and long-term resident routes, and Indonesia's
        second-home and remote-worker visa categories for Bali, are the two most
        commonly used by backpackers extending into semi-permanent stays - both need
        planning well before the standard tourist entry expires, not a same-week
        decision.
        """,
        "tips",
        "southeast asia",
    ),
    _doc(
        "tips-diving-scuba-sea",
        """
        Diving and scuba certification across the region, since this is one of the
        cheapest places in the world to learn. Koh Tao (Thailand) is the single
        cheapest and most popular Open Water certification spot on Earth, typically
        USD 250-300 all in for a 3-4 day PADI course including basic accommodation -
        the sheer volume of dive schools keeps prices competitive. The Gili Islands
        (Indonesia, especially Gili Trawangan and Gili Air) are the main alternative,
        slightly pricier but with less of a party-hostel atmosphere around the dive
        schools. Amed and Tulamben (Bali) for the shore-accessible USAT Liberty wreck,
        one of the best cheap wreck dives anywhere. El Nido and Coron (Philippines) for
        wreck diving on the sunken WWII Japanese fleet at Coron specifically, world
        class and comparatively uncrowded. Sipadan (Malaysian Borneo) is the outlier -
        genuinely world-class wall diving with turtles and schooling barracuda, but
        access is permit-limited (a strict daily diver cap) and priced well above
        shoestring, worth knowing before planning a Borneo diving detour on a tight
        budget. Certification lasts for life - get it early in a trip and use it
        everywhere after.
        """,
        "tips",
        "southeast asia",
    ),
    _doc(
        "tips-solo-female-travel-sea",
        """
        Solo female travel notes across the region - genuinely one of the more solo
        female-friendly parts of the world by backpacker consensus, with real
        country-to-country and town-to-town variation worth knowing rather than a
        single blanket verdict. The Southeast Asia hostel circuit (Chiang Mai, Pai,
        Luang Prabang, Hoi An, Canggu, El Nido) is heavily solo-female travelled with
        an established social infrastructure of female-friendly hostels and group tours
        specifically because so many women already do this route solo. Dress modestly
        at temples and in more conservative rural areas regardless of gender, but this
        matters more visibly for women in India and Myanmar than on the beach-hostel
        circuit. India warrants a specific, honest note: solo female travellers
        consistently report more unwanted attention and a higher baseline vigilance
        requirement than the Southeast Asia circuit, particularly around transport hubs
        and after dark - booking women-only train compartments/berths where available,
        sticking to well-reviewed guesthouses, and avoiding solo late-night arrivals
        into unfamiliar towns are the standard, widely-repeated pieces of advice rather
        than excessive caution. Facebook groups (Girls Love Travel and country-specific
        ones) are where most real-time, current safety chatter actually happens, more
        current than any static document like this one.
        """,
        "tips",
        "southeast asia",
    ),
    _doc(
        "tips-visa-runs-comparison-sea",
        """
        Comparing visa-run and long-stay options across the region for anyone trying to
        stay longer than a single tourist entry allows. Thailand: the most run-heavy
        country on the circuit historically, with land border runs to Laos, Cambodia or
        Malaysia resetting a 60-day exemption, though immigration scrutiny of
        back-to-back land entries has increased and the 60-day extension (one extra 30
        days, in-country) is now the more reliable route to a longer single stay than
        repeated runs. Indonesia: the 30-day visa on arrival extends once for 30 more
        days; beyond that, leaving and re-entering restarts the clock but a social/
        cultural visa or the newer long-stay options are the real route to months, not
        a border run. Vietnam and the Philippines both tolerate in-country extensions
        (Vietnam via agents, the Philippines via Bureau of Immigration) more readily
        than repeated exits. Malaysia's 90-day allowance is generous enough that most
        backpackers never need to think about this there at all, which is exactly why
        it pairs so well as a "reset" stop for people juggling shorter allowances
        elsewhere on the circuit (see tips-route-sea-overland).
        """,
        "tips",
        "southeast asia",
    ),
    _doc(
        "tips-street-food-safety-sea",
        """
        Street food across the region is generally safe and is a major reason budget
        travel here works at all, but the practical rule that actually prevents
        illness is simple and repeated by every experienced backpacker: eat where the
        turnover is high and the queue is long, especially with local customers rather
        than only tourists, because high turnover means food isn't sitting. Ice in
        Thailand, Vietnam and Cambodia's cities is almost universally made in
        factories from filtered water and is safe; ice in rural areas or at a stall
        with no visible ice delivery is the actual risk, not ice as a category. Bottled
        or filtered water is the safe default everywhere on this circuit outside major
        Malaysian and Singaporean cities, where tap water is genuinely potable. Dishes
        worth specifically seeking out: khao soi and som tam in northern Thailand, pho
        and bun cha in Vietnam, amok in Cambodia, laap in Laos, nasi campur in
        Indonesia, and thali in India (vegetarian thalis are the easiest safe,
        filling, cheap meal across the whole subcontinent). A first bout of stomach
        trouble in the first one to two weeks of a trip is close to universal rather
        than a sign anything was done wrong - pack rehydration salts before you need
        them, not after.
        """,
        "tips",
        "southeast asia",
    ),
    _doc(
        "tips-south-asia-overland",
        """
        Overland logistics for the South Asia leg (India, Nepal, Sri Lanka, Bhutan),
        which behaves differently from the Southeast Asia mainland circuit. The
        Kathmandu-India land border (Sunauli/Belahiya or Kakarbhitta) is open to
        foreigners and cheap, but genuinely slow and chaotic by Southeast Asian
        standards - budget a full day, expect crowding, and arrange the onward Indian
        leg (a long sleeper train from the border town) rather than assuming a single
        smooth bus. There is no land border between India/Nepal and Sri Lanka - Sri
        Lanka is reached only by air, most cheaply via Chennai, Bengaluru or Chennai-
        Colombo budget routes, or via Kuala Lumpur/Bangkok if arriving from Southeast
        Asia. Bhutan has no independent overland entry either: the sole land crossing
        (Phuentsholing, from West Bengal) is used by tour operators as part of a
        pre-booked package, not something a backpacker walks across freely (see
        tips-bhutan-overview). Within India, sleeper trains booked well ahead (or via
        the Tatkal short-notice quota) are dramatically cheaper and more comfortable
        than long-distance buses for any journey over about 8 hours.
        """,
        "tips",
        "south asia",
    ),
    _doc(
        "tips-himalaya-trekking-regionwide",
        """
        Comparing Himalayan trekking options across Nepal and India for anyone deciding
        where to do a mountain trek rather than assuming Nepal is the only option.
        Nepal remains the best-infrastructured choice: teahouse trekking (see
        tips-nepal) means no tent or cooking gear, well-worn trails, and routes from
        4-5 days (Poon Hill) to 12-14 days (Everest Base Camp). India's Himachal
        Pradesh and Ladakh offer a genuinely different, less crowded style - the
        Hampta Pass and Kheerganga treks near Kasol are 2-4 day options needing far
        less commitment than Nepal's classics, while Ladakh's Markha Valley trek (June
        to September only, since Ladakh is snowbound the rest of the year) is a true
        high-altitude desert trek requiring more self-sufficiency and often a hired
        guide, as teahouse infrastructure is thinner than Nepal's. Permits differ
        sharply: Nepal's TIMS/conservation permits are bought in Kathmandu or Pokhara
        in a day; India's Inner Line Permit for parts of Ladakh and other border-
        adjacent areas can take longer and is worth checking well ahead. Altitude
        sickness risk is identical regardless of country - ascend slowly above 3,000m
        and know the symptoms, not just the itinerary.
        """,
        "tips",
        "south asia",
    ),
    _doc(
        "tips-lost-passport-emergency-sea",
        """
        Lost or stolen passport and general emergency procedure across the region,
        worth knowing before it happens rather than after. First step everywhere:
        file a police report immediately (a copy is required by every embassy to issue
        an emergency travel document) - most tourist police stations in this region are
        used to processing these and can move fast if you insist politely. Embassy/
        consulate presence for Western nationalities is concentrated in Bangkok, Hanoi,
        Ho Chi Minh City, Phnom Penh, Vientiane, Jakarta, Kuala Lumpur, Manila,
        Kathmandu, Colombo and Delhi/Mumbai - a traveller in a smaller town needs to
        budget a day or more of travel to reach one. An Emergency Travel Document
        (ETD) typically takes 24-72 hours once the police report and passport photos
        are in hand, and is valid only for direct return travel, not further onward
        travel - plan to fly home or to a hub with a full consulate, not to continue
        the trip on it. Keep a photographed copy of your passport's photo page (cloud-
        stored, not just on the phone that might be what's stolen) and your travel
        insurance policy number accessible from a second device or printed copy - this
        single habit is what turns a lost-passport day into a lost-passport week.
        """,
        "tips",
        "southeast asia",
    ),
    _doc(
        "tips-ethical-wildlife-sea",
        """
        Ethical wildlife tourism across the region, expanding on the brief elephant note
        in tips-thailand because the same pattern (an attraction that looks
        animal-friendly but isn't) repeats region-wide. Elephant riding and shows are
        now widely understood to involve harmful training methods and should be
        avoided everywhere they're offered, not just in Thailand; observation-only
        sanctuaries (feeding and bathing, no riding) are the standard ethical
        alternative and cost more precisely because they're not subsidised by the
        volume that riding operations rely on. Tiger selfie parks (still found in parts
        of Thailand) are unambiguously to be avoided - the animals are typically
        drugged or declawed. In Borneo (Malaysia and Indonesia), Sepilok's orangutan
        rehabilitation centre and similar accredited sanctuaries are genuinely
        conservation-focused and worth the visit; roadside "orangutan photo"
        operations are not the same thing and fund a different, exploitative industry.
        Whale shark "swim with" tours (Oslob, Philippines specifically) are
        controversial among marine biologists for artificially feeding wild sharks to
        guarantee sightings - Donsol, also in the Philippines, is the more responsible
        alternative that does not feed the animals. When in doubt, the rule that holds
        up region-wide: if an animal performs a trick, is ridden, or is guaranteed to
        appear on demand, it usually isn't the ethical option.
        """,
        "tips",
        "southeast asia",
    ),
    _doc(
        "tips-nightlife-party-towns-sea",
        """
        Comparing the region's party-town scenes, since "best nightlife" means
        different things in different places and a mismatch is a common source of
        disappointment. Vang Vieng (Laos) has shifted hard away from its infamous
        2000s-2010s tubing scene toward a calmer bar-and-adventure-sports crowd - do
        not go expecting the old reputation. Koh Phangan's Full Moon Party (Thailand)
        remains the single biggest one-night event on the circuit, monthly, and is
        genuinely worth timing a trip around if that's what you want, but the rest of
        the island outside party week is comparatively quiet. Gili Trawangan
        (Indonesia) is the most consistently party-oriented of the three Gili islands
        night after night, not just on a schedule, while Gili Air and Gili Meno next
        door are deliberately the calmer alternatives a short boat ride away. Canggu
        (Bali) is less a "party" scene than an all-day surf-cafe-sunset-bar culture
        that runs later on weekends - closer to a long-stay social scene than a
        short-term rager. Boracay (Philippines) rebuilt its nightlife after a 2018
        environmental closure and rebuild, and is now more regulated (earlier noise
        curfews, no more open bonfires on the main beach) than its pre-2018
        reputation suggests.
        """,
        "tips",
        "southeast asia",
    ),
    _doc(
        "tips-money-transfer-banking-sea",
        """
        Money and banking notes across the region, beyond the basic ATM-fee warning in
        tips-safety-sea-general. A Wise (or Revolut) multi-currency card is the
        standard backpacker setup now: it gets the real interbank exchange rate on ATM
        withdrawals and card payments, versus the 3-5% typically lost through a home
        bank's card or through in-person currency exchange. Always choose to be
        charged in the LOCAL currency when a card machine or ATM offers a choice
        (dynamic currency conversion, DCC) - agreeing to be billed in your home
        currency always uses a worse, inflated rate set by the merchant's bank, not
        your own. Cash-heavy countries on this circuit: Laos, Cambodia and Myanmar,
        where card acceptance outside city-centre hotels is genuinely limited and USD
        cash (crisp, undamaged notes - torn or heavily marked bills are refused) is
        often preferred to local currency for larger purchases. Card-friendly
        countries: Malaysia, Thailand's cities, and India's cities, where a Wise card
        covers most daily spending. Notify your bank of travel dates only if it still
        uses old-style fraud flagging - most large banks no longer need this, but a
        smaller local bank might still block a first foreign transaction without it.
        """,
        "tips",
        "southeast asia",
    ),
    _doc(
        "tips-onward-flights-budget-airlines-sea",
        """
        Budget airline strategy across the region, since flights are cheaper and more
        useful here than the "always go overland" backpacker instinct assumes for the
        longer legs (see tips-route-sea-overland). AirAsia, VietJet, Scoot and Cebu
        Pacific between them cover almost every useful regional route, and their
        headline fares are genuinely cheap - but budget for add-ons: checked baggage
        is rarely included and costs more added at the airport than pre-booked online,
        and seat selection, meals and priority boarding are all separate charges that
        add up fast if not deliberately skipped. "Proof of onward travel" is
        sporadically enforced at check-in, most strictly and consistently for the
        Philippines and reasonably often for Thailand and Indonesia - budget airlines
        themselves enforce this more than immigration does, since the airline is fined
        for carrying someone who gets refused entry. The standard workaround for a
        genuinely one-way, open-ended trip is a fully refundable dummy onward booking
        (via a service like OnwardTicket) or booking the cheapest possible onward
        flight and simply not using it, rather than lying about having a return date
        booked at all. Domestic flight sales (especially AirAsia's periodic seat
        sales) are worth signing up for even mid-trip if the route is flexible.
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
