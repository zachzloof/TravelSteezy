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
        Zealand passports enter visa-free for 30 days on arrival by air or land - cut down
        from the old 60-day allowance by a rule change effective 15 September 2026 - extendable
        once at an immigration office inside Thailand for a further 30 days (fee around
        1,900 THB), a 60-day ceiling per entry. Land border entries under this exemption are
        now capped at two per calendar year (air arrivals are not subject to this cap), so the
        old habit of unlimited back-to-back land "visa runs" no longer works - it's a hard rule,
        not just something that draws officer scrutiny. Proof of onward travel within the
        permitted window is occasionally requested at check-in by budget airlines even when
        immigration does not ask. Overstaying carries a 500 THB per day fine (capped at 20,000
        THB), payable at the airport, and overstays beyond 90 days trigger re-entry bans of a
        year or more. Backpacker note: a land visa run to Vientiane, Penang or Phnom Penh still
        works within the new two-per-year cap, but long-stay travellers now need to plan around
        that limit rather than assuming unlimited resets.
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
        Phnom Penh and Siem Reap airports, costing USD 30 plus a passport photo. An e-visa
        is available online at evisa.gov.kh for USD 30 (cut from USD 36 in January 2025 -
        third-party sites still quote the old, higher figure) and speeds up airport arrival.
        Extendable once for 30 days inside the country. IMPORTANT: the entire
        Thailand-Cambodia land border, including Poipet, has been closed since mid-2025 amid
        an armed border conflict, with no reopening date as of late 2026 - fly between
        Bangkok and Phnom Penh/Siem Reap instead (around 1-1.25h) rather than planning any
        overland crossing from Thailand; check current status immediately before travel,
        since this situation moves. VOA remains available at land borders with Vietnam
        (Bavet) and Laos (Tropaeng Kreal). If the Thai border does reopen: officials at
        Poipet have long been notorious for requesting extra "processing fees" of a few
        dollars, often demanded in Thai baht - paying the exact USD 30 and politely
        declining the extra usually works. Carry USD cash: land borders frequently have no
        working card facilities.
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
        extendable once for another 30 days - you can start the application online through
        the e-VOA portal, but since a June 2025 rule change every extension, with no
        exceptions, requires an in-person visit to an immigration office for mandatory
        biometrics (fingerprints and photo); without an agent handling it, budget about
        three visits (apply, biometrics, collection) over roughly a week, which matters if
        you are on a tight schedule. An e-VOA bought before
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
        pre-arrival form to skip a queue. Separately, trekking requires a conservation
        area/national park permit everywhere (ACAP for Annapurna, a Sagarmatha National Park
        permit plus a Khumbu Rural Municipality permit for Everest), plus a TIMS card - still
        required for Annapurna, Langtang and Manaslu, but no longer required in the
        Everest/Khumbu region, where the local municipality permit replaces it. Budget roughly
        USD 40-45 in permits (TIMS + ACAP) for a standard Annapurna trek, bought together in
        Kathmandu or Pokhara. Since March 2023, Nepal officially requires a licensed guide
        (booked through a registered trekking agency) for permit issuance in nearly every
        major trekking region - Annapurna, Everest, Langtang, Manaslu and more, not just
        isolated areas - though enforcement is inconsistent in practice, especially around
        Everest; budget for a guide as the default expectation, not an edge case.
        """,
        "visa",
        "nepal",
        region="south asia",
        nationalities=WESTERN_PASSPORTS,
    ),
    _doc(
        "visa-srilanka-western",
        """
        Sri Lanka ETA (Electronic Travel Authorisation): mandatory in advance for all Western
        passport holders - visa-on-arrival was discontinued 15 October 2025, so applying
        online before flying is now the only route in. As of 25 May 2026, the ETA is FREE for
        a 30-day double-entry stay for UK, US, Australian, Canadian and New Zealand passport
        holders (one of 40 nationalities granted a fee waiver); Irish passport holders are
        notably NOT on that free list and still pay the standard USD 50 fee - check per
        passport rather than assuming "Western = free". Approved within a day or two.
        Extending beyond 30 days in Colombo is not a simple flat jump to 90 days - it's a
        staged, paid, per-30-day-block process (confirm current fees directly on
        immigration.gov.lk, since this has changed multiple times recently). Apply only
        through the official eta.gov.lk site - agent sites still charge USD 50-80 even where
        the official fee is now zero. Passport must have 6 months validity.
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
        on arrival for these nationalities. Options are 30 days (multiple entry - changed
        from double entry on 12 June 2026 - USD 25 July-March or a discounted USD 10
        April-June low season), 1 year (multiple entry, a flat USD 40) or 5 years (multiple
        entry, USD 200 standard rate as of mid-2026, a sharp rise from a former USD 80 - some
        nationalities pay more under reciprocal pricing, notably UK passport holders at
        USD 484; confirm your specific nationality's current rate on the official portal
        before applying), with the 1-year and 5-year versions capping any single stay at
        90 days (180 for US, UK, Canadian and Japanese citizens) regardless of the visa's
        overall validity. Apply only at the official indianvisaonline.gov.in - third-party
        sites charge large markups. Processing is officially "within 72 hours" but budget
        8-10 working days in practice (real-world processing has slowed well past the old
        4-5 day estimate), and note a fixed number of designated entry airports/ports apply
        to e-Visa holders. Since 1 April 2026, every foreign national must also submit a
        digital e-Arrival Card within 72 hours before arrival via indianvisaonline.gov.in or
        the Su-Swagatam app - the old paper disembarkation form no longer exists, and turning
        up without having done this causes problems at immigration. Passport needs 6 months
        validity and two blank pages. Registration (FRRO) is generally not required for stays
        under 180 days on a tourist e-Visa; a June 2026 rule tightened the FRRO deadline for
        anyone staying beyond 180 days (register before day 180, no more grace period), which
        does not affect an ordinary tourist trip.
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
        visa-free for tourism - UK citizens get 30 days under Mongolia's temporary
        34-country tourism exemption (currently extended through 1 January 2027), while
        US citizens get 90 days under a separate, older, permanent bilateral agreement in
        force since 2001. Canadian passport holders are ALSO visa-free for 30 days, under
        a permanent bilateral arrangement in place since 2014 - no advance visa needed.
        Australian and New Zealand passport holders are currently visa-free for 30 days
        too, but under the same temporary 34-country exemption as the UK (through 1
        January 2027) rather than a permanent one - worth a quick check before flying
        since this is the allowance most likely to lapse or change, unlike Canada's or
        the US's. Confirm your specific nationality's current allowance before flying
        regardless, since these agreements are renewed and occasionally lapse. Extensions
        beyond the visa-free window are handled at the
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
        holders can apply online for a tourist e-Visa at the official evisa.moip.gov.mm
        portal (USD 50, 28 days, single entry, standard processing 3-5 working days),
        entering through Yangon, Mandalay or Naypyidaw international airports, or the
        Kawthaung land border from Thailand. The e-Visa system was suspended from
        3 April to 20 May 2025 after the devastating 28 March 2025 magnitude-7.7
        earthquake damaged infrastructure - a concrete example of why this situation
        needs checking immediately before booking, not assumed stable from any static
        document, this one included.

        IMPORTANT SAFETY CONTEXT, not just a bureaucratic note: Myanmar has been in a
        state of civil war and military rule since the February 2021 coup, and the
        situation has continued to deteriorate rather than stabilise - a military-run
        election in December 2025/January 2026, widely condemned as a sham, was
        accompanied by a spike in attacks (over 400 military air strikes killing at
        least 170 civilians during the election period alone), and the March 2025
        earthquake caused serious damage in Mandalay (the palace) and Bagan (multiple
        centuries-old temples) on top of the conflict. The US State Department (Level 4,
        Do Not Travel - the highest tier) and Australian DFAT (Do Not Travel) both advise
        against ALL travel to the ENTIRE country, including Yangon - not just to conflict
        regions or areas "outside" a tourist circuit. The UK FCDO takes a two-tier
        approach: it advises against all travel to specific conflict states/regions
        (Rakhine, Kachin, Chin, Kayah, Kayin, Mon, Sagaing, Magway, northern Shan State,
        and parts of Tanintharyi and Bago), and against all but essential travel to the
        REST of the country - which still includes Yangon, Bagan, Mandalay and Inle Lake,
        not a cleared or exempted zone. Internal flights and overland routes between the
        main tourist towns can be curtailed at short notice depending on the security
        situation, and domestic flight capacity has shrunk substantially since 2021.
        Check current government travel advisories immediately before booking, not months
        in advance - this situation moves fast, has gotten worse rather than better since
        2021, and this document cannot track it in real time.
        """,
        "visa",
        "myanmar",
        nationalities=WESTERN_PASSPORTS,
        lead_time_days=4,
    ),
    _doc(
        "visa-australia-western",
        """
        Australia requires almost every Western nationality to sort paperwork before arrival -
        there is no visa-free entry the way there often is in Southeast Asia. UK, Irish and most
        EU passport holders use the free eVisitor (subclass 651), applied for online, valid 12
        months with unlimited entries and up to 3 months per visit - no service fee. US and other
        non-eVisitor-eligible Western passports use the ETA (subclass 601) instead: apply through
        the official Australian ETA phone app only, AUD 20 service fee, decision usually within
        minutes to 24 hours, also 12 months multiple-entry with a 3-month-per-visit cap. New
        Zealand citizens are the outlier: under the 1973 Trans-Tasman Travel Arrangement they need
        no visa at all and are simply granted a Special Category Visa (subclass 444) on arrival,
        letting them live and work indefinitely. Watch for lookalike paid "ETA visa service"
        websites charging a large markup over the AUD 20 app fee - only the AustralianETA app and
        immi.homeaffairs.gov.au are official.

        Working holiday: Subclass 417 (UK, Ireland, Canada and roughly 16 other mostly
        European/East Asian passports) and Subclass 462 (US and around 30 other countries, with
        extra requirements like proof of funds or education) both grant 12 months of unrestricted
        work and travel, extendable to a second and third year by completing specified regional
        work. Age limit is 18-30 for most nationalities, 18-35 for UK, Irish, Canadian, French,
        Italian and Danish passport holders. The application charge rose to AUD 840 for a first
        application (AUD 1,000 for a second or third) from 1 July 2026 - budget for this on top of
        flights, since it's the single biggest fixed cost of the whole working-holiday plan.
        """,
        "visa",
        "australia",
        region="oceania",
        nationalities=WESTERN_PASSPORTS,
    ),
    _doc(
        "visa-newzealand-western",
        """
        New Zealand requires visa-waiver nationalities - UK, US, Canadian and Irish passport
        holders among them - to hold an NZeTA (Electronic Travel Authority) before boarding, plus
        pay the International Visitor Levy (IVL). Apply via the official NZeTA mobile app (NZD 17)
        or the immigration.govt.nz website (NZD 23); the IVL, which jumped from NZD 35 to NZD 100
        on 1 October 2024, is charged in the same transaction, for a combined cost of roughly
        NZD 117 (app) to NZD 123 (web). It's valid 2 years multiple-entry once granted and must be
        arranged before departure, not on arrival - there is no visa-on-arrival option. Everyone,
        including exempt nationalities, must also complete the New Zealand Traveller Declaration
        (NZTD) shortly before travel. Australian citizens are the exception: under the Trans-Tasman
        Travel Arrangement they need no NZeTA, no IVL and no advance visa at all, and are simply
        issued a resident visa on arrival.

        Working holiday: New Zealand runs a separate bilateral scheme per passport rather than one
        uniform visa. The standard terms - 18-30, 12 months, NZD 770 - apply to US and most
        nationalities, but UK citizens can be granted up to 36 months from first entry without
        needing to extend, and Canadians up to 23 months; several countries (UK, Canada plus a
        handful of others) also raise the age ceiling to 35. Applicants must show roughly NZD 4,200
        in available funds (less with a booked return ticket) and, for capped countries, apply
        promptly once the annual quota opens - the US scheme currently has no cap, so there's no
        rush there specifically.
        """,
        "visa",
        "new zealand",
        region="oceania",
        nationalities=WESTERN_PASSPORTS,
    ),
    _doc(
        "visa-southkorea-western",
        """
        South Korea visa-free entry: UK, US, Australian, Irish and New Zealand passport
        holders get 90 days visa-free for tourism; Canadians get an unusually generous 180
        days under a separate bilateral agreement, both multiple-entry. The K-ETA (Korea
        Electronic Travel Authorization) is normally a mandatory pre-arrival online
        authorization (10,000 KRW, about USD 9, apply only at k-eta.go.kr, valid 3 years),
        but it is currently suspended for a list of 22 countries - including the UK, US,
        Australia, Canada and New Zealand - through 31 December 2026, so those nationalities
        need nothing beyond a passport right now. Ireland is NOT on that 22-country
        suspension list even though Irish citizens are otherwise visa-exempt, so Irish
        passport holders currently still need to apply for and pay for a K-ETA before flying
        - check per-passport rather than assuming "Western = exempt". K-ETA is due to become
        mandatory again for everyone from 1 January 2027. Separately, every arriving
        traveller regardless of K-ETA status must complete the free e-Arrival Card online
        within 3 days of arrival. Passport validity is unusually relaxed: Korea only requires
        it to cover the length of your stay, not the usual 6-month buffer (K-ETA applications
        do ask for 6 months). Land/sea entry barely applies here - nearly everyone flies into
        Incheon or Gimhae (Busan); the one real option is the Camellia Line ferry from Busan
        to Fukuoka, Japan (6-11.5h, roughly USD 80-150), now the only ferry link since the
        faster JR Beetle hydrofoil was discontinued in December 2024.
        """,
        "visa",
        "south korea",
        region="east asia",
        nationalities=WESTERN_PASSPORTS,
    ),
    _doc(
        "visa-japan-western",
        """
        Japan visa-free entry: UK, US, Australian, Canadian and New Zealand passport holders
        get a 90-day visa-free stamp on arrival for tourism, no application needed
        beforehand. UK and Irish passport holders specifically get a better deal: their
        visa-exempt status can be extended in-country, before the initial 90 days expire, to
        a total of 6 months, by applying at a Regional Immigration Bureau - worth knowing if
        a long Japan stint is the plan. No electronic pre-authorization is required yet:
        Japan's planned system, JESTA (modelled on the US ESTA), is not live - it's currently
        targeted for fiscal year 2028 (by law no later than March 2029), with an expected fee
        around JPY 2,000-3,000 (roughly USD 13-20) once it launches, but as of now (2026) it
        does not apply to anyone. Every traveller must still complete the free Japan Arrival
        Card (the disembarkation/customs forms) via the Visit Japan Web portal, ideally
        before flying, to get a QR code for immigration. Passport validity: no fixed minimum
        is legally required for the visa-exempt stamp itself, but the practical "6 months
        from arrival" rule still matters because airlines routinely refuse boarding without
        it. Land/sea entry is essentially moot - Japan is reached almost exclusively by air
        (or the Camellia Line ferry from Busan, South Korea; see the South Korea route notes).
        """,
        "visa",
        "japan",
        region="east asia",
        nationalities=WESTERN_PASSPORTS,
    ),
    _doc(
        "visa-peru-western",
        """
        Peru visa exemption, with a real split by nationality that is easy to flatten
        incorrectly. US passport holders get an unusually generous stay of up to 183
        days, granted at immigration officer discretion. UK, Australian, Canadian,
        Irish and New Zealand passport holders get up to 90 days, also at officer
        discretion - ask for the full amount on arrival, since officers sometimes
        default to a shorter stamp. Since August 2021, Peru generally does not allow
        tourist-visa extensions for any of these nationalities: once your stamped
        period ends you are expected to leave, not apply for more days in-country.
        Overstaying is not a grey area - it is a fixed daily fine (0.1% of the UIT,
        around S/5.50/day in 2026) payable online via Pagalo.pe or at a Banco de la
        Nacion branch before you fly out; paying the fine is a penalty, not a
        legalisation of extra days. Arrival/departure is recorded via the Tarjeta
        Andina de Migracion (TAM), now completed digitally rather than on paper.
        Passport needs 6 months validity remaining.
        """,
        "visa",
        "peru",
        region="south america",
        nationalities=WESTERN_PASSPORTS,
    ),
    _doc(
        "visa-colombia-western",
        """
        Colombia visa exemption: UK, US, Australian, Canadian, Irish and New
        Zealand passport holders all enter visa-free for tourism, granted for up
        to 90 days on arrival at officer discretion. This can be extended once,
        for a further 90 days, at a Migracion Colombia office or online, for
        around COP 110,000 - apply before the original stamp expires, not after.
        The combined maximum is 180 days of tourist stay within any calendar year,
        after which you must leave; there is no simple visa run to reset the
        clock the way there sometimes is in Southeast Asia. Since 2024 Colombia
        has rolled out "Check-Mig", an online pre-arrival/pre-departure
        registration - as of mid-2026 Migracion Colombia's own guidance lists it
        as not strictly mandatory, but most airlines still require proof it was
        completed before they will let you board, so treat it as required in
        practice. It is free and must be done 72 hours to 1 hour before each
        flight, on the official Migracion Colombia portal only. Passport needs 6
        months validity.
        """,
        "visa",
        "colombia",
        region="south america",
        nationalities=WESTERN_PASSPORTS,
    ),
    _doc(
        "visa-ecuador-western",
        """
        Ecuador visa exemption: UK, US, Australian, Canadian, Irish and New
        Zealand passport holders all get a T-3 tourist stamp on arrival, no
        application, no fee, no pre-approval. The allowance is 90 days within any
        rolling 12-month period, not 90 days per entry - leaving and re-entering
        does not reset the clock, which catches out long-stay travellers who try
        a quick border-hop expecting a fresh 90 days. One additional 90-day
        extension can be granted by the Direccion de Extranjeria, capping total
        tourist time at 180 days within any rolling 12 months. Since 29 July 2025
        all arrivals, including these visa-exempt nationalities, must also
        complete a free online customs registration (the FRA form) before
        travelling, which generates a QR code shown on arrival - a new
        requirement worth flagging since it postdates most existing guides.
        Passport needs 6 months validity remaining, and proof of onward travel is
        sometimes requested at check-in.
        """,
        "visa",
        "ecuador",
        region="south america",
        nationalities=WESTERN_PASSPORTS,
    ),
    _doc(
        "visa-bolivia-western",
        """
        Bolivia visa: as of 1 December 2025, the United States was moved onto
        Bolivia's visa-free list, ending nearly two decades of a USD 160
        reciprocity fee for American passport holders - a genuinely recent
        change worth double-checking against the embassy site before relying on
        older guides that still describe the old fee. UK, Australian, Canadian,
        Irish and New Zealand passport holders were already visa-free before this
        change. All six nationalities now get the same deal: visa-free entry for
        tourism, up to 90 days within a 12-month period. The one requirement that
        now applies to everyone regardless of nationality is SIGEMIG, Bolivia's
        mandatory digital pre-registration (migracion.gob.bo) - free, takes
        8-10 minutes, opens 30 days before travel, and produces a QR code you
        show at the border or airport; arriving without having done it can mean
        delays or being asked to complete it on the spot with patchy border wifi.
        Passport needs 6 months validity remaining. Land borders (from Peru at
        Desaguadero/Copacabana, from Chile at San Pedro/Uyuni routes, from
        Argentina at Villazon) are all functional for these nationalities but
        slower and less streamlined than flying into La Paz.
        """,
        "visa",
        "bolivia",
        region="south america",
        nationalities=WESTERN_PASSPORTS,
    ),
    _doc(
        "visa-chile-western",
        """
        Chile visa exemption: UK, US, Canadian, Irish and New Zealand passport
        holders have long entered visa-free for up to 90 days with no fee.
        Australia was the outlier for years - Chile charged Australians a
        reciprocity fee (around USD 117 at the end) until it was scrapped in
        2019, and Australians still needed a visa in advance after that. That
        changed again on 17 September 2025, when Chile unexpectedly dropped the
        visa requirement for Australian citizens entirely: Australians now get
        the same visa-free 90-day entry as the other five nationalities, with no
        fee. As of 2026 there is no reciprocity fee currently active for any of
        the six nationalities covered here - a genuine change from the
        2000s-2010s pattern where several South American countries charged
        Americans, Canadians and Australians fees mirroring their own visa costs,
        so do not assume an old reciprocity-fee figure is still current. A
        90-day extension is possible once via the extranjeria (immigration
        office) for a fee, or by leaving and re-entering. Passport needs 6
        months validity; a Chilean customs declaration form covering food/plant
        items is taken seriously at the airport.
        """,
        "visa",
        "chile",
        region="south america",
        nationalities=WESTERN_PASSPORTS,
    ),
    _doc(
        "visa-argentina-western",
        """
        Argentina visa exemption: UK, US, Australian, Canadian, Irish and New
        Zealand passport holders all enter visa-free for tourism for up to 90
        days, extendable once for a further 90 days at the Direccion Nacional de
        Migraciones in Buenos Aires or by leaving and re-entering. This is one
        of the more genuinely simplified entries in South America for Western
        passports: the once-notorious "reciprocity fee" (a one-off charge,
        historically USD 100-160, mirroring what each country charged Argentine
        visitors) has been suspended for all six nationalities for years now -
        the US since August 2016, Australia since July 2017, Canada since
        January 2018 - and remains suspended as of 2026. Do not confuse this
        with the AVE (Autorizacion de Viaje Electronica): that online
        authorisation exists for a small set of third-country nationals who hold
        a valid US or Schengen visa, not for these six passports directly, which
        need no pre-arrival authorisation of any kind. Passport needs 6 months
        validity.
        """,
        "visa",
        "argentina",
        region="south america",
        nationalities=WESTERN_PASSPORTS,
    ),
    _doc(
        "visa-brazil-western",
        """
        Brazil is the one country in this region where the six "Western"
        passports genuinely split three ways, so do not give one blanket answer.
        US, Canadian and Australian passport holders currently need an e-Visa,
        reinstated 10 April 2025 after Brazil had waived it unilaterally since
        2019 - apply online in advance (around USD 80.90), valid 10 years for
        US citizens and 5 years for Canadians/Australians, but each individual
        stay is capped at 90 days and total time in Brazil at 180 days within
        any 12-month period; this is a policy that has flip-flopped before and
        could change again, so verify immediately before booking rather than
        trusting any cached guide. UK and New Zealand passport holders remain
        visa-free for up to 90 days, no application needed. Irish passport
        holders got a brand-new visa-waiver effective 24 February 2026 (Ireland
        was one of a small group of countries added, alongside China, France and
        others): 30 days visa-free, extendable to 90 days within 12 months.
        Passport needs 6 months validity and proof of onward/return travel for
        all nationalities.
        """,
        "visa",
        "brazil",
        region="south america",
        nationalities=WESTERN_PASSPORTS,
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
        near freezing and the rice terraces are bare; the terraces are green from planting in
        May/June through August, then turn golden with the harvest from early September
        through mid-October. Central Vietnam (Hue, Hoi An, Da Nang) has a
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
        at its best then - Arugam Bay's surf season runs April to October, with the best
        waves June through August. The
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
        window is late May to early September, and even within it June through August are
        the months most Gobi Desert and steppe tour operators run full itineraries,
        while May and September are real shoulder months, with cold nights and a genuine
        chance of early/late snow.
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
    _doc(
        "seasonal-australia",
        """
        Australia is too big for one season to mean anything nationwide, and it genuinely runs two
        opposite climate systems - see seasonal-australia-north for the tropical half. The
        temperate south and east (Sydney, Melbourne, Adelaide, Perth, Tasmania) has four real
        seasons on the reverse of the northern-hemisphere calendar: summer December-February (hot,
        25-30C+ in Sydney/Melbourne, peak season and prices, Christmas/New Year the single busiest
        and most expensive stretch), autumn March-May and spring September-November (the genuine
        sweet spot - mild, fewer crowds, best value), and winter June-August (cool rather than cold
        on the mainland coast - Sydney highs around 17C - but this is when the Victorian and NSW
        alpine areas and Tasmania get properly cold). Tasmania runs cooler than the mainland
        year-round and its best hiking window (the Overland Track booking season) runs October to
        May, narrowing toward summer for the most reliable weather. Bushfire risk on the mainland
        peaks in the hot, dry summer months, especially January-March in the southeast, and can
        close national parks and trails at short notice - check state fire service (Rural Fire
        Service/CFA) total fire ban alerts before a bush walk in summer.
        """,
        "seasonal",
        "australia",
        region="oceania",
    ),
    _doc(
        "seasonal-australia-north",
        """
        Tropical northern Australia (Darwin and the Top End, Cairns and tropical North Queensland,
        Broome) runs on a wet/dry cycle completely opposite to the southern states' four seasons,
        and mixing the two up is a common planning mistake. Dry season, May to October, is the
        prime time to visit: sunny, low humidity, comfortable heat, and the safe window for
        swimming off Cairns beaches and camping in Kakadu. Wet season, November to April, brings
        monsoonal downpours, high humidity, and a genuine tropical cyclone season that can disrupt
        flights and roads with little notice - some Kakadu and Kimberley routes become impassable.
        Wet season also brings marine stinger (box jellyfish and Irukandji) season to the tropical
        coast: swimming outside stinger nets or a full-body stinger suit is genuinely dangerous
        roughly November to May around Cairns, and October to June further north beyond Port
        Douglas, where estuarine crocodiles are also a real, non-theoretical risk in rivers, creeks
        and even some beaches - check local signage and don't swim or wade in the tropical north
        outside patrolled, netted areas regardless of how inviting a creek looks. The Great Barrier
        Reef itself is diveable year-round, but visibility and calm seas are best in the dry season.
        """,
        "seasonal",
        "australia",
        region="oceania",
    ),
    _doc(
        "seasonal-newzealand",
        """
        New Zealand's seasons run opposite the northern hemisphere - December to February is
        summer, June to August is winter - which regularly catches travellers out planning a
        "European summer" itinerary for the wrong half of the year. Summer (Dec-Feb) is peak
        season nationwide: warm (20-25C), long days, the Great Walks and general hiking season at
        its best, and the busiest, priciest stretch, especially over the Christmas/New Year school
        holidays. The Great Walks hut/booking season runs late October to April; outside that
        window huts are unserviced (no warden, sometimes no gas) and conditions get genuinely
        alpine at altitude, so hiking the Milford or Kepler Track in July is a different, much more
        serious undertaking than in January. The South Island ski season, centred on Queenstown and
        Wanaka, runs mid-June to early October, with July and August the reliable deep-snow months
        - this is the one part of the country where winter is the peak season, not the off-season.
        Spring (Sep-Nov) and autumn (Mar-Apr) are the shoulder sweet spots: fewer crowds, lower
        prices, and, in autumn especially, Central Otago's stone-fruit and wine-country colour.
        Weather changes fast and without warning at altitude and on the coast year-round - a fine
        morning is not a promise about the afternoon on any NZ tramping track.
        """,
        "seasonal",
        "new zealand",
        region="oceania",
    ),
    _doc(
        "seasonal-southkorea",
        """
        South Korea's seasons are sharply defined and the narrow "monsoon" label causes real
        damage if applied to the wrong months. Jangma, the actual monsoon, is short: it
        typically arrives in the south (Jeju first) around June 19-25 and finishes by roughly
        July 20, dumping 30-50% of the year's rain in about a month; July is the wettest,
        most humid month nationwide (near 80% humidity). Typhoon season runs July-September
        but the real landfall risk clusters late August to mid-September, mainly hitting Jeju
        and the southern/east coasts - it is not a reason to write off the whole autumn. By
        contrast, September itself is one of the best months to visit: the monsoon is over,
        the worst heat has broken, humidity drops, and any lingering typhoon risk is a
        tail-end exception rather than the rule. October is the true peak: dry, mild, and
        carrying the famous autumn foliage, which starts in the northern mountains
        (Seoraksan) in mid-to-late October and reaches Seoul and the south by
        early-to-mid November. Spring is similarly narrow: cherry blossoms move north from
        Jeju (~mid-March) to Seoul (~early April), with the Jinhae festival the first week of
        April, but March-May is also "yellow dust" season - fine Mongolian/Chinese desert
        sand that peaks in April and can turn air quality genuinely bad for a few days at a
        time. Winter (Dec-Feb) is cold and very dry with clear skies, Seoul averaging around
        -6 to 2C in January - good for skiing, less good for wandering outdoors all day.
        """,
        "seasonal",
        "south korea",
        region="east asia",
        monsoon_months=[6, 7],
        hazard="typhoon",
    ),
    _doc(
        "seasonal-japan",
        """
        Japan's seasons are dramatic and timing mistakes are common, especially around three
        names that get treated as monoliths when they shouldn't be. Cherry blossom (sakura)
        timing moves with latitude and altitude, not a fixed calendar date: it opens in
        Okinawa as early as January, reaches Tokyo and Kyoto in full bloom around April 5-10
        most years, and finishes in Hokkaido in early-to-mid May - check a live forecast
        rather than booking a date months out, since a mild or cold spring shifts it by a
        week or more. Tsuyu, the rainy season, is a genuine Honshu-wide event running roughly
        early June to mid-July (Okinawa's own tsuyu is separate and earlier, mid-May to late
        June) - persistent rain and high humidity, though rarely all-day downpours. Typhoon
        season runs May-October but the real risk concentrates in August and September,
        hitting Okinawa hardest (6-7 storms a year on average) and the main islands less
        often. Late April-early May brings Golden Week (Apr 29-May 6 in 2026), when domestic
        transport and hotels nationwide sell out and prices spike - avoid travelling ON those
        dates even if the weather is perfect. August also brings Obon (around Aug 13-16), the
        year's single busiest, most expensive domestic travel week, on top of the year's
        worst heat and humidity. November is the autumn-foliage peak in Kyoto and Tokyo,
        following Hokkaido's earlier colour in October. Winter (Dec-Feb) is cold and dry on
        the Pacific side, but Hokkaido and the Japan Alps get serious snow and are prime ski
        season December-March.
        """,
        "seasonal",
        "japan",
        region="east asia",
        monsoon_months=[6, 7],
        hazard="typhoon",
    ),
    _doc(
        "seasonal-japan-okinawa",
        """
        Okinawa runs on a different climate from the rest of Japan and is worth treating
        separately rather than folding into the mainland's seasonal calendar. It's genuinely
        subtropical: winter (Dec-Feb) stays mild, around 15-20C, roughly 10C warmer than the
        mainland at the same time, though the sea is too cool for casual swimming. Its rainy
        season (tsuyu) starts about a month before Honshu's, typically mid-May to late June,
        so a late-May Honshu itinerary can dodge rain that Okinawa is already having. The
        beach season is long by Japanese standards, roughly April through October, with peak
        swimming July-September. The trade-off for that long season is typhoon exposure:
        Okinawa takes the brunt of Japan's typhoons, an average of 6-7 direct hits a year,
        concentrated August-September, more frequent and more disruptive to inter-island
        ferries and flights than anywhere on the mainland - check forecasts specifically
        before island-hopping to the Yaeyama or Kerama chains in late summer.
        """,
        "seasonal",
        "japan",
        region="east asia",
        monsoon_months=[5, 6],
        hazard="typhoon",
    ),
    _doc(
        "seasonal-peru-highlands",
        """
        The Andes (Cusco, the Sacred Valley, Machu Picchu, the Inca Trail) run on a
        single clear dry/wet cycle that dominates most backpacker planning here. Dry
        season is May to October, with June to September the coldest, clearest and
        most crowded stretch - nights in Cusco regularly drop near freezing even
        though days are warm and sunny. The wet season, November to April, peaks in
        January and February: trails get muddy and landslide risk rises on mountain
        roads, though Machu Picchu itself stays open year-round via train. The one
        hard closure to know: the Inca Trail itself shuts completely for the whole
        of February every year for government-mandated maintenance (bridge repair,
        landslide clearing) - Machu Picchu is still reachable by train during the
        closure, just not via the trek. March is a mixed reopening month with heavy
        demand for the first permits back. April, and September-October, are the
        shoulder-season sweet spots: drying or still-dry trails, green-tinged
        landscapes, and noticeably thinner crowds than the June-August peak.
        """,
        "seasonal",
        "peru",
        region="south america",
        monsoon_months=[11, 12, 1, 2, 3],
    ),
    _doc(
        "seasonal-peru-coast-amazon",
        """
        Lima and the desert coast run on the opposite logic to the Andes: this is a
        true coastal desert, so there is fog (garua) rather than rain. May to
        October is Lima's grey, cool, overcast "winter" - overcast skies most days,
        rarely above 20C, and the sun barely appears in the city itself even though
        it is technically the Andes' dry season. December to March is Lima's warm,
        sunny summer, the best window for the coastal towns and for Huacachina's
        sandboarding. The Peruvian Amazon (Puerto Maldonado, Iquitos) has its own
        cycle again: a drier, easier-trail season May to September/October with
        better wildlife visibility along shrinking riverbanks, and a wetter
        November-to-March season when rivers rise and canoe access into flooded
        forest (igapo-style routes) actually improves even as trail-walking gets
        harder. The practical upshot: a single Peru itinerary crossing coast,
        highlands and jungle will hit three different weather logics at once, and
        "best time to visit Peru" genuinely depends on which of the three you
        prioritise.
        """,
        "seasonal",
        "peru",
        region="south america",
        monsoon_months=[12, 1, 2, 3],
    ),
    _doc(
        "seasonal-colombia",
        """
        Colombia has two dry and two wet seasons nationwide rather than a single
        monsoon, and the pattern shifts by region on top of that. The two reliable
        dry windows are December to March and July to August; the wetter stretches
        are April to May and October to November, with October typically the
        single wettest month countrywide. The Caribbean coast (Cartagena, Santa
        Marta, Tayrona) is at its best and driest December to March, and gets
        genuinely wet and quieter October-November. The Andean cities (Bogota,
        Medellin) see a bimodal pattern with rain spread more evenly across the
        year and cooler temperatures driven by altitude rather than season - pack
        a layer for Bogota regardless of month. The Amazon (Leticia) is wet nearly
        year-round, and counter-intuitively the higher-water rainy months are
        often better for wildlife-boat access than the drier months. The Pacific
        coast (Nuqui, Bahia Solano) has its own draw July to October: humpback
        whale migration season, when the coast is at its wettest but also its most
        worthwhile for that specific reason.
        """,
        "seasonal",
        "colombia",
        region="south america",
        monsoon_months=[4, 5, 10, 11],
    ),
    _doc(
        "seasonal-ecuador",
        """
        Ecuador is small but genuinely splits into four different climates that
        do not share a calendar. The Andean highlands (Quito, Banos, Cuenca,
        Cotopaxi) have their dry, clear season June to September - the best
        hiking and volcano-viewing window - with a wetter, cloudier stretch
        October to May, though "wet" here usually means overcast afternoons
        rather than washed-out days. The Pacific coast (Montanita, Guayaquil)
        runs the opposite way: December to May is warm, wet-but-sunny beach
        season with the warmest sea, while June to November is cooler, greyer and
        less appealing for swimming despite technically being the "dry" season by
        highland logic. The Amazon (the Oriente, reached from Quito or Coca) is
        driest and best for wildlife spotting June to October, wetter but still
        very travellable the rest of the year. The Galapagos run on their own
        cycle again: a cooler, dry garua season June to November with rougher
        seas but calmer surface wildlife-viewing conditions, and a warmer, wetter,
        calmer-seas season December to May that many divers actually prefer for
        visibility. Trying to time one trip for all four regions at once is not
        really possible - decide which region is the priority first.
        """,
        "seasonal",
        "ecuador",
        region="south america",
        monsoon_months=[],
    ),
    _doc(
        "seasonal-bolivia",
        """
        Bolivia's Altiplano (La Paz, Uyuni, the Andean highlands) is a genuine
        high-altitude desert, and its two seasons produce completely different
        versions of the same headline attraction. Dry season, May to October,
        gives full physical access across the Uyuni salt flats, the vivid white
        hexagonal crust patterns, and the clearest stargazing conditions anywhere
        on the continent - but no mirror effect. Wet season, roughly December to
        March (peaking January-February), floods a thin layer of water over parts
        of the salt flat, creating the famous sky-mirror reflection that fills
        Instagram feeds - at the cost of some areas, including Incahuasi Island,
        becoming inaccessible, and rural roads elsewhere in the country turning
        difficult. Late April is often cited as the single best compromise week:
        a lingering thin water layer for photography alongside mostly-dry, still
        accessible terrain. Nights on the Altiplano are cold year-round because of
        the altitude (La Paz sits around 3,600-4,100m) - expect near-freezing
        nights even in the dry season, worse in June-July. Lowland Bolivia (the
        Amazon-fringe Yungas around Rurrenabaque) runs on the opposite, wetter-in-
        summer logic typical of the Amazon basin.
        """,
        "seasonal",
        "bolivia",
        region="south america",
        monsoon_months=[12, 1, 2, 3],
    ),
    _doc(
        "seasonal-chile",
        """
        Chile is absurdly long north to south, and its two headline regions run
        on genuinely opposite logics within the same hemisphere and season.
        The Atacama Desert (San Pedro de Atacama) in the north is a
        high-altitude desert that is workable essentially year-round: December
        to February is its busiest, warmest high season, while the shoulder
        months (September-November and March-May) bring the mildest days,
        clearest skies and noticeably fewer crowds and lower prices. Chilean
        Patagonia (Torres del Paine, Puerto Natales) is the opposite story: it
        only properly opens November to March, with December-February the
        warmest but also the windiest and most crowded window, and effectively
        shuts down June-August when most refugios and campsites close entirely
        for the season. The result is that "best time for Chile" genuinely
        depends on which region matters more - November and March are the best
        compromise months if you are trying to combine both desert and
        Patagonia in one trip, since Patagonia is open-but-calmer and the
        Atacama is mild rather than at its hottest.
        """,
        "seasonal",
        "chile",
        region="south america",
        monsoon_months=[],
    ),
    _doc(
        "seasonal-argentina",
        """
        Argentina spans subtropical north to sub-Antarctic south, and Buenos
        Aires sits temperately in between with its own separate calendar again.
        Iguazu Falls and the northern regions (Salta, the wine country around
        Cafayate) are best in the shoulder seasons, April-May and
        September-October, avoiding both winter cold in the northwest highlands
        and the sometimes brutal summer humidity further north. Buenos Aires
        itself is most pleasant spring (September-November) and autumn
        (March-May); December-February is hot and humid, June-August is cool but
        still very workable for city sightseeing. Patagonia (Bariloche, El
        Calafate, Ushuaia) is the real hard seasonal boundary: it is only fully
        open and accessible November to March, with December-February the
        warmest, busiest, priciest window and June-August a genuine winter
        closure for most trekking infrastructure outside Bariloche's ski season.
        November and March are the shoulder sweet spots for Patagonia - milder
        winds, thinner crowds, still-open trails. A single round-the-country trip
        hits at least three different climate logics, so pin down priority
        regions before picking dates.
        """,
        "seasonal",
        "argentina",
        region="south america",
        monsoon_months=[],
    ),
    _doc(
        "seasonal-brazil",
        """
        Brazil is continent-sized and its regions do not share a season. Rio de
        Janeiro and the southeast are best September to March: hot, festive, and
        including Carnival (dates move year to year, usually February or early
        March) - the single busiest and most expensive fortnight in the country,
        genuinely worth planning around rather than accidentally colliding with
        if budget matters. The Amazon's dry season runs roughly May to October,
        the better window for jungle-lodge trail walks and wildlife spotting
        along lower rivers; the wet season (especially around February) actually
        suits canoe-based exploration of flooded forest (igapo) better, so "dry
        is always best" does not fully hold here. The Northeast beaches (Bahia/
        Salvador, Ceara/Jericoacoara) are warm and sunny nearly year-round, driest
        and brightest September to March, with a specific kitesurfing/windsurfing
        peak around July-September when trade winds are strongest. Southern
        Brazil (Florianopolis, the far south around Rio Grande do Sul) has a real
        temperate winter - June-July brings genuinely cold weather and
        occasional snow in higher towns like Gramado, unusual for a country this
        associated with heat.
        """,
        "seasonal",
        "brazil",
        region="south america",
        monsoon_months=[],
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
        class sleeper cost around 940-1,200 THB and save a night's accommodation. Standard
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
        it costs around USD 250-350 all in for an easy-rider driver over 3-4 days (self-drive,
        no guide, comes in cheaper at roughly USD 100-150). As of June 2026 foreign tourists
        also need a Border Area Entry Permit (around USD 10) to enter the regulated Ha Giang
        loop districts - arrange it through your easy-rider operator or homestay rather than
        assuming the old no-paperwork version of the loop still applies. Sleeper buses are
        cheap and ubiquitous but genuinely uncomfortable if you are over about 180cm; the
        reunification train is slower and much more pleasant. Phong Nha's caves are world
        class and still cheap to visit at the Paradise Cave and Dark Cave level. Bank on
        losing a day to the Hanoi traffic before you find your feet.
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
        Prabang (around USD 20-25 booked direct at the pier, more like USD 60-80 via a
        pre-booked package from Chiang Mai/Chiang Rai that includes border transport;
        overnight stop in Pakbeng) is the classic arrival from
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
        Mirissa for whale watching (season November to April), Arugam Bay for surf (April to
        October, best waves June-August), Sigiriya rock or the cheaper Pidurangala alternative directly opposite
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
        classic "banana pancake trail" loop runs Bangkok - Chiang Mai - (slow boat via Huay
        Xai) - Luang Prabang - Vang Vieng - Vientiane - (bus or train) - Hanoi - south through
        Vietnam to Ho Chi Minh City - Phnom Penh - Siem Reap - back to Bangkok, and doing it
        properly takes about three months; two months is brisk, one month means flying
        several legs. IMPORTANT: the Siem Reap-back-to-Bangkok leg of that classic loop is
        currently not possible overland - every Thailand-Cambodia land border, including
        Poipet, has been closed since mid-2025 due to an armed border conflict, with no
        reopening date as of late 2026; fly Siem Reap-Bangkok instead and check current
        border status before assuming the loop can be closed on land. Other key overland
        realities: Hanoi to Luang Prabang overland is a punishing 20-25 hours and most people
        fly it for around USD 100-150 (fares vary well above that); Ho Chi Minh City to Phnom
        Penh is an easy 6-8 hour bus with a straightforward border; the Laos high-speed rail
        has made Vientiane to Luang Prabang a two-hour trip instead of ten. Budget airlines
        (AirAsia, VietJet, Scoot) frequently undercut a 20-hour bus once you price in the lost
        day, so the "always go overland to save money" instinct is often wrong for the long
        legs - and is now a hard requirement, not just a preference, for the Cambodia-Thailand
        leg specifically.
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
        expense and typically runs USD 60-140 a day per person in a shared group - budget
        around USD 80-120/day for a hostel-organised shared-jeep trip, noticeably more
        than a few years ago - which is close to unavoidable since public transport
        barely reaches the sites that
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
        figure that doesn't apply. Independent budget travel is not possible for Western
        passport holders: all such tourists must book through a licensed Bhutanese tour
        operator and pay a Sustainable Development Fee (SDF) of USD 100 per person per
        night - the post-September-2023 reduced rate (down from USD 200), officially
        guaranteed through 31 August 2027 - on top of accommodation, food, transport and a
        guide, which the operator arranges as a package - there is no walk-in hostel scene
        or DIY overland route the way there is elsewhere on this circuit. Indian, Bangladeshi
        and Maldivian nationals face separate, much cheaper rules: Indians pay an SDF of
        INR 1,200/night (about USD 14) and can travel independently without a licensed
        operator, though a guide is still compulsory for temples/dzongs and travel outside
        the Thimphu-Paro-Punakha corridor; Bangladeshis pay USD 15/night for the first
        15,000 tourists annually. Children under 6 are free, ages 6-12 pay half the standard
        rate. A visa is arranged by the operator as part of booking, not applied for
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
        Physical SIM cards (AIS/dtac in Thailand ~USD 9-13, Viettel in Vietnam ~USD 3-7,
        Airtel/Jio in India ~USD 4-6) are cheap and sold at every airport arrivals hall,
        usually faster than queueing for an eSIM provider's activation support. Smart/Globe
        in the Philippines run noticeably higher for a real data package - typically
        USD 18-40 rather than the USD 5-10 you'd pay elsewhere on the circuit, so budget for
        that difference specifically. eSIMs (Airalo,
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
        stay longer than a single tourist entry allows. Thailand: historically the most
        run-heavy country on the circuit, but since a 15 September 2026 rule change cut the
        visa exemption from 60 to 30 days and capped land-border entries under it at two per
        calendar year, unlimited back-to-back runs no longer work - the 30-day in-country
        extension (one extra 30 days) plus at most two land visa runs a year is now the real
        ceiling on how long an exemption-only stay can run. Indonesia: the 30-day visa on arrival extends once for 30 more
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
        smooth bus. There is no land border between India/Nepal and Sri Lanka, and it's
        no longer air-only either: a passenger ferry (Nagapattinam, India, to Kankesanthurai
        near Jaffna) has run since October 2023, open to foreign tourists with a valid ETA,
        at roughly USD 75-80 one-way - a genuine alternative to flying. Otherwise Sri Lanka
        is reached by air, most cheaply via Chennai, Bengaluru or Chennai-Colombo budget
        routes, or via Kuala Lumpur/Bangkok if arriving from Southeast Asia. Bhutan has no
        independent overland entry either: the sole land crossing
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
        sharply: Nepal's conservation-area/TIMS permits are issued in Kathmandu or Pokhara
        in a day, but since 2023 rule changes they require booking through a registered
        trekking agency with a licensed guide attached rather than a same-day DIY counter
        transaction (TIMS itself no longer applies to the Everest region specifically -
        see the visa doc); India's Inner Line Permit for parts of Ladakh and other border-
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
    _doc(
        "tips-australia",
        """
        Australia backpacker notes - genuinely expensive by backpacker standards, closer to
        Western Europe than Southeast Asia. Daily budget: shoestring USD 60-80, mid USD
        100-150; hostel dorms run AUD 30-45 (roughly USD 20-30) in Sydney and Melbourne, more
        on the Gold Coast and Whitsundays in peak season. The classic circuit is the east coast
        run, either direction, Cairns to Melbourne (or Sydney to Cairns): Cairns for the Great
        Barrier Reef (day trips AUD 220-350) and the Daintree, the Whitsundays for a 2-3 day
        sailing trip (backpacker boats around AUD 250-300/day), Byron Bay, and Sydney to
        Melbourne via the Great Ocean Road. A Greyhound "Whimit" hop-on-hop-off pass covers the
        whole Cairns-Sydney leg from around AUD 289. Campervan relocation deals (Imoova,
        Wicked, DriveNow) move a company's van between cities for as little as AUD 1-5/day,
        sometimes with free fuel - the standard cheap way backpackers see the coast on their
        own schedule; expect 5-6 days allowed for a Cairns-Sydney relocation. Perth and the
        west coast are a genuinely separate, much less-visited leg due to the distance - most
        first-time backpackers skip it. Safety: rip currents are Australia's single deadliest
        beach hazard (over a third of beach drowning deaths) - always swim between the
        red-and-yellow patrol flags, since international visitors unfamiliar with them are
        disproportionately represented in the drowning statistics. Use SPF50+ sunscreen and a
        hat without exception - Australia has among the highest UV and skin cancer rates in the
        world even on a cloudy day.
        """,
        "tips",
        "australia",
        region="oceania",
        budget_shoestring_usd=70,
    ),
    _doc(
        "tips-newzealand",
        """
        New Zealand backpacker notes - small but not cheap; budget closer to Australia than to
        Asia. Daily budget: shoestring USD 70-90 (one backpacker-budget estimate lands around
        NZD 130/day for dorms, cooked-not-bought food, buses and a couple of activities), mid
        USD 110-150; hostel dorms run NZD 25-40 in the main towns, cheaper in small South Island
        towns, pricier in Queenstown in ski season. The standard split is North Island
        (Auckland, Rotorua for geothermal fields, Wellington for the Te Papa museum and the
        ferry) then a 3-3.5h Interislander/Bluebridge ferry crossing the Marlborough Sounds to
        the South Island (Queenstown for bungy jumping and Milford Sound day trips, Abel
        Tasman, Franz Josef, Fiordland). Hop-on-hop-off bus networks (Kiwi Experience, Stray) or
        the fixed-route InterCity network are how most backpackers without a car get around; a
        multi-day hop-on pass runs roughly NZD 40-45/day of travel. The genuine planning
        gotcha: Great Walks bookings (Milford, Kepler, Routeburn, Abel Tasman and others) for a
        given October-April season open the previous May, staggered by track over about ten
        days, and the popular huts on Milford and Routeburn can sell out within days of booking
        opening - decide your Great Walk and book it months ahead, not on arrival in
        Queenstown. Weather on any tramping track can turn cold, wet and genuinely dangerous
        within hours regardless of season - check the DOC track and hut status and a mountain
        forecast (not just a town forecast) before setting out, and tell someone your
        intentions.
        """,
        "tips",
        "new zealand",
        region="oceania",
        budget_shoestring_usd=80,
    ),
    _doc(
        "tips-southkorea",
        """
        South Korea backpacker notes. Daily budget: shoestring USD 40-55 (KRW 50,000-70,000),
        mid USD 70-100 - noticeably pricier than Southeast Asia, driven mostly by
        accommodation. Dorm beds run USD 15-25 in Seoul (Hongdae and Myeongdong have the
        biggest hostel scene), a bit cheaper in Busan and inland cities. The standard
        first-timer route is Seoul - a DMZ/JSA day tour (USD 40 for DMZ only, USD 120+ for
        full JSA access, book 1-2 weeks ahead since JSA needs security clearance and doesn't
        run Sun/Mon) - then KTX south to Busan (2h15, around USD 43-50 one-way, trains every
        20-30 minutes), with Gyeongju's temples and royal tombs as an easy day trip from
        Busan, and Jeju Island as a cheap ~1-hour domestic flight add-on (often under USD 30
        one-way on budget carriers). Get a T-money card on day one (sold at any convenience
        store/subway station) for buses and subways - it is completely separate from the
        KORAIL/KTX system, and a KORAIL Pass only pays off if you're doing several
        long-distance legs in a short window. Rent a pocket wifi "egg" at the airport or buy
        a tourist SIM/eSIM - Korean map apps (Naver Map, KakaoMap) work far better than
        Google Maps here, so data matters more than usual. Convenience stores (CU, GS25,
        7-Eleven) are a genuine backpacker institution: hot food, cheap beer, ATMs and free
        wifi, open 24/7, and often cheaper and more reliable than a restaurant for a fast meal.
        """,
        "tips",
        "south korea",
        region="east asia",
        budget_shoestring_usd=48,
    ),
    _doc(
        "tips-japan",
        """
        Japan backpacker notes. Daily budget: shoestring USD 55-70 (JPY 9,500-12,500)
        covering a hostel/capsule bed, convenience-store and casual food, and local trains
        only - noticeably pricier than Southeast Asia and closer to Western Europe. Hostel
        dorms run JPY 4,000-5,000 (about USD 26-33) in Tokyo and a bit cheaper in Kyoto
        (USD 8-24). The standard first-timer route is Tokyo - Kyoto - Osaka, with Hiroshima
        (and Miyajima) as the common extension. Bullet trains are a real budget line item:
        Tokyo-Kyoto is 2h15 for about USD 95-100 one-way (JPY 13,320-14,570), Kyoto-Hiroshima
        1h40 for about USD 65 (JPY 10,570), Osaka-Hiroshima 1h26 for about USD 60
        (JPY 9,710). The 7-day nationwide JR Pass costs JPY 50,000 (about USD 330) as of
        2026 - after a 70% price hike in October 2023 - and rises again to JPY 53,000 in
        October 2026 via overseas agents; do the arithmetic before buying, since a
        straightforward one-way Tokyo-Kyoto-Osaka-Hiroshima run (roughly USD 220-240 in
        individual tickets) can come in cheaper than the pass unless you're also covering a
        return leg or extra long-distance hops. For city transport, a Suica, Pasmo or ICOCA
        IC card (tap-to-pay on every train, bus and at convenience stores) is essential and
        works nationwide. Despite Japan's tech reputation, carry cash: contactless cards now
        cover most chain restaurants and stations, but small independent izakayas, older
        guesthouses and rural areas are still cash-only - keep JPY 10,000-20,000 on hand.
        """,
        "tips",
        "japan",
        region="east asia",
        budget_shoestring_usd=62,
    ),
    _doc(
        "tips-peru",
        """
        Peru backpacker notes. Daily budget: shoestring USD 25-35, mid USD 45-65 -
        among the cheaper Andean countries, though Inca Trail/Machu Picchu costs are
        a fixed large line item regardless of budget level. Standard route: Lima -
        Huacachina (sandboarding and pisco in a desert oasis) - Nazca (the Lines, by
        plane or viewing tower) - Arequipa (the "White City", base for Colca
        Canyon's condors) - Cusco - Machu Picchu. The classic 4-day Inca Trail costs
        around USD 129 in permits alone (S/444: trail permit plus Machu Picchu
        entrance, now sold separately as of 2026) on top of the guided-tour price,
        and permits for the May-September high season sell out 4-6 months ahead -
        book early or take the (also excellent, less regulated) Salkantay trek as
        the fallback alternative. Machu Picchu entrance alone is USD 65. Rainbow
        Mountain is a popular, punishing high-altitude day trip from Cusco (5,200m).
        Safety/scam note: Lima's Miraflores and Barranco districts are the
        tourist-safe base; fake police and inflated "photocopy" or "fee" demands
        target travellers at the Bolivia land border near Desaguadero specifically -
        genuine officials do not charge cash processing fees. Carry soles cash
        outside major cities; card acceptance thins out fast beyond Lima and Cusco.
        """,
        "tips",
        "peru",
        region="south america",
        budget_shoestring_usd=30,
    ),
    _doc(
        "tips-colombia",
        """
        Colombia backpacker notes. Daily budget: shoestring USD 30-40, mid USD 50-70. Standard
        first-timer route: Bogota - Medellin - (Guatape as a day trip) - Cartagena/Santa Marta
        - Tayrona National Park, often extended south to Salento in the coffee region (Cocora
        Valley's wax palms, a coffee farm tour) or San Gil for whitewater rafting and
        paragliding. Bogota to Medellin is 8-10h by bus or a cheap 1h flight; Medellin to
        Cartagena is a long 13-15h overnight bus or a 1h flight - most backpackers fly this leg
        given the distance. Medellin's Comuna 13 graffiti tour is genuinely worth doing, but go
        with an established operator and before late afternoon rather than wandering into the
        surrounding residential comunas alone. Safety/scam note: scopolamine ("devil's breath")
        drink-spiking robberies are a real and specifically Colombian risk in nightlife areas -
        never accept a drink, cigarette or scented item from a stranger; use Uber, InDriver or
        Cabify rather than hailing street taxis, and agree fares upfront if you do. El Poblado,
        Laureles and Envigado are Medellin's safe backpacker bases; Centro is fine by day, avoid
        at night. Cash (pesos) is still needed for small purchases and rural areas despite
        decent card coverage in cities.
        """,
        "tips",
        "colombia",
        region="south america",
        budget_shoestring_usd=35,
    ),
    _doc(
        "tips-ecuador",
        """
        Ecuador backpacker notes. Daily budget: shoestring USD 30-40, mid USD 45-60 - and
        unusually for the region, Ecuador is fully dollarised (the US dollar is the official
        currency), so there is no exchange-rate guesswork or local-currency ATM confusion at
        all, a genuine convenience versus every other country in this batch. Standard route:
        Quito - Banos (waterfalls, hot springs, adventure sports - swinging at "the end of the
        world" at Casa del Arbol is the famous photo) - Cuenca (a quieter, UNESCO-listed
        colonial city, less touristed than Quito) - onward to the Amazon or the coast. Quito to
        Banos is 4h/USD 5 by direct bus from Quitumbe terminal; Banos to Cuenca is a genuinely
        slow, winding 8-10h with no fast option. Galapagos: budget travellers go land-based
        rather than on a cruise - island-hop by public ferry (USD 30-38 each way) between Santa
        Cruz, Isabela and San Cristobal and do free/cheap DIY sites (Tortuga Bay, Las Grietas)
        rather than paid tours, though the USD 200 park entrance fee and flights from the
        mainland are unavoidable and account for most of the cost. Safety note: Quito's
        historic centre is fine by day but has a real pickpocketing/robbery reputation after
        dark - take a taxi rather than walking back to your hostel late.
        """,
        "tips",
        "ecuador",
        region="south america",
        budget_shoestring_usd=35,
    ),
    _doc(
        "tips-bolivia",
        """
        Bolivia backpacker notes. Daily budget: shoestring USD 20-30, the cheapest country in
        this batch and one of the cheapest in South America outright. Standard route: La Paz -
        Uyuni (salt flats) - Sucre or onward to Chile/Argentina via Villazon or the Uyuni-San
        Pedro de Atacama border crossing. The classic Uyuni experience is a 3-day 4x4 tour
        (from around USD 150-200 shared) taking in the salt flats, coloured lagoons and geysers
        before crossing into Chile at San Pedro de Atacama - book through a reputable La Paz or
        Uyuni agency with recent reviews, since safety and vehicle quality varies a lot at the
        cheapest end. The Death Road (Yungas Road) mountain-bike descent from La Paz costs
        around USD 100-160 for a full day with a certified operator - do not go with the
        cheapest bike-rental-only option, since fatalities have happened on this route and
        equipment quality matters. Sucre, Bolivia's constitutional capital, is the whitewashed,
        laid-back Spanish-school town most backpackers wish they'd budgeted more days for.
        Safety/scam note: the Peru-Bolivia land border near Desaguadero has a pattern of
        officials inventing "processing fees" or steering travellers to overpriced
        photocopy/photo shops - genuine Bolivian border fees do not exist for these
        nationalities post-SIGEMIG. Cash (bolivianos, with USD as backup) is essential outside
        La Paz and Sucre; ATMs are sparse and unreliable in smaller towns.
        """,
        "tips",
        "bolivia",
        region="south america",
        budget_shoestring_usd=25,
    ),
    _doc(
        "tips-chile",
        """
        Chile backpacker notes. Daily budget: shoestring USD 35-45, mid USD 60-85 - the most
        expensive country in this batch, on a par with parts of Europe once you add Patagonia's
        food and gear costs. Standard route: Santiago - Valparaiso (coastal, colourful,
        hillside funiculars) - north to San Pedro de Atacama for desert tours (Valle de la
        Luna, geysers, salt flats), or south to Puerto Natales as the gateway to Torres del
        Paine National Park. The W Trek (4-5 days) needs its accommodation booked months ahead
        for December-February - the park splits between two private operators (Las Torres and
        Vertice Patagonia) who run separate, non-interchangeable booking systems, which trips
        up a lot of independent hikers; camping is far cheaper (roughly USD 12-50/night
        depending on operator and site) than the refugio dorm beds (USD 40-100+). Park entrance
        itself is around USD 49 for foreigners staying more than 3 days. Santiago to San Pedro
        is a genuinely long overnight-plus bus (20-23h, or fly in ~2h); Santiago to Puerto
        Natales for Patagonia is far enough south that almost everyone flies (3.5h) rather than
        buses. Money note: Chile is largely card-friendly in cities, but bring cash for
        Patagonia's smaller towns where card machines and ATMs are unreliable.
        """,
        "tips",
        "chile",
        region="south america",
        budget_shoestring_usd=40,
    ),
    _doc(
        "tips-argentina",
        """
        Argentina backpacker notes. Daily budget: shoestring USD 30-45, mid USD 55-80 - but
        treat these figures cautiously, because Argentina's currency situation moves fast:
        after President Milei's government lifted most currency controls (the "cepo
        cambiario") in April 2025, the old huge gap between the official exchange rate and the
        informal "blue dollar" rate has largely closed - as of September 2026 the gap is
        roughly 1-5%, a fraction of what it was in the mid-2020s. This means the old standard
        backpacker advice to "bring cash USD and change on the blue market for a much better
        rate" barely applies any more; a Wise-style card at the near-official rate is now close
        enough to any cash rate that chasing a "cueva" exchange house is no longer the free win
        it used to be - verify the current gap before travelling, since Argentine monetary
        policy has changed direction repeatedly in the past decade. Standard route: Buenos
        Aires - Mendoza (wine country, Andes views) - Bariloche (Lake District, chocolate,
        hiking) - El Calafate (Perito Moreno Glacier) - sometimes extended to Ushuaia, the
        world's southernmost city, or diverted north to Salta and Iguazu Falls. Iguazu is worth
        visiting from both the Argentine side (close-up walkways) and the Brazilian side
        (panoramic views) if your visas allow - see the Brazil visa note on the reinstated
        e-Visa requirement for Americans, Canadians and Australians specifically before
        planning that crossing.
        """,
        "tips",
        "argentina",
        region="south america",
        budget_shoestring_usd=37,
    ),
    _doc(
        "tips-brazil",
        """
        Brazil backpacker notes. Daily budget: shoestring USD 35-50, mid USD 60-90 - pricier
        than the Spanish-speaking Andean countries, closer to Chile. Standard first-timer
        route: Rio de Janeiro - Paraty (colonial coastal town, 4-5h bus, around R$70) -
        Florianopolis or Ilha Grande for beach time - or north to Salvador for
        Afro-Brazilian culture and the historic Pelourinho district. Carnival, if timing
        around it, is biggest and best-known in Rio and Salvador but both get extremely
        booked and expensive months ahead. Iguazu Falls (Foz do Iguacu on the Brazilian
        side) pairs naturally with a visit to the Argentine side across the border - see the
        Argentina tips doc, and check your specific e-Visa status before planning the
        crossing if you are American, Canadian or Australian. Safety note: Rio's Copacabana
        and Ipanema are fine by day but phone/bag snatching from the sand and beachfront
        promenade is common - bring only cash and a card in a waterproof pouch to the beach,
        leave everything else at the hostel. After dark, stick to well-lit, busy streets;
        favela tours are genuinely worthwhile culturally but only with an established
        community-based operator, never independently. Money note: Brazil is heavily card-
        and Pix-based domestically now, but carry some reais cash for small vendors and bus
        fares. Portuguese, not Spanish, is spoken here - a surprising number of first-time
        South America backpackers assume otherwise and it is worth 20 minutes learning basic
        phrases before arrival.
        """,
        "tips",
        "brazil",
        region="south america",
        budget_shoestring_usd=42,
    ),
]

SEED_DOCUMENTS: list[dict[str, Any]] = VISA_DOCS + SEASONAL_DOCS + TIPS_DOCS


def documents_by_type(content_type: str) -> list[dict[str, Any]]:
    return [d for d in SEED_DOCUMENTS if d["metadata"]["content_type"] == content_type]


KNOWN_DESTINATIONS = sorted(
    {d["metadata"]["destination"] for d in SEED_DOCUMENTS if d["metadata"]["destination"]}
)
