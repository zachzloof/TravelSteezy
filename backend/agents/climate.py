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
            3: ("mixed", "Hot. Burning season is at its worst in the north this month - Chiang Mai air quality regularly among the worst in the world."),
            4: ("mixed", "Hottest month (38C+). Burning season is tailing off in the north through the month as rain approaches - usually cleared by Songkran. Songkran mid-month is busy and expensive."),
            5: ("mixed", "Southwest monsoon starts on the Andaman coast. Gulf islands still fine."),
            6: ("mixed", "Andaman coast wet; Gulf islands (Koh Tao, Samui, Phangan) are at their best."),
            7: ("mixed", "Andaman wet, Gulf good. Split your plan by coast."),
            8: ("mixed", "Andaman wet, Gulf good."),
            9: ("avoid", "Wettest month on the Andaman coast. Ferries cancelled, some islands effectively shut."),
            10: ("avoid", "Andaman monsoon peak continues. Gulf side starting to turn."),
            11: ("mixed", "Andaman clearing and excellent; Gulf islands now in their wet period."),
            12: ("good", "Dry and cool nationwide; Gulf islands (Samui/Phangan/Tao) still carrying meaningful rain most of the month as the wet season tails off, clearing by January."),
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
            9: ("avoid", "Typhoon and flood season begins on the central coast - Hoi An floods most years - but this is simultaneously one of the best months in the northern mountains: Sapa/Ha Giang's rice terraces turn gold with the harvest. Ask which region before defaulting to 'avoid' for the whole country."),
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
        "summary": "Wet Nov-Mar (heaviest Jan-Feb, but travellable); dry Apr-Oct with Jul-Aug the busiest.",
        "months": {
            1: ("mixed", "Wet season peak (Bali's rainiest month) - but rain is mostly short, heavy afternoon downpours rather than all-day washouts, so it stays travellable; quieter and cheaper than dry season. Road flooding and rough Gili crossings are real risks."),
            2: ("mixed", "Wet season peak continues, same trade-off as January. Poor diving visibility."),
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
            8: ("mixed", "Good nationwide, but west-coast rain (Langkawi especially) is already building toward its August-October peak."),
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
            10: ("avoid", "Typhoon peak continues; September and October together are historically the worst stretch for landfalls."),
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
    "india": {
        "summary": "Three seasons, not two: cool/dry Oct-Mar (best), brutal heat Apr-Jun, monsoon Jul-Sep.",
        "months": {
            1: ("good", "Cool and dry across the north. Best month for Rajasthan and the plains; cold at night in the desert."),
            2: ("good", "Still cool and dry, warming toward the end of the month."),
            3: ("mixed", "Heat building fast on the plains; hill regions and the north still comfortable."),
            4: ("avoid", "Brutal heat on the Gangetic plain and Rajasthan, regularly 43C+. Head to the hills instead."),
            5: ("avoid", "Peak heat before the monsoon breaks. Genuinely dangerous daytime sightseeing on the plains."),
            6: ("mixed", "Monsoon arrives in the south and west first (Kerala); north still hot and dry until late month."),
            7: ("avoid", "Monsoon in full swing nationwide except Ladakh, which is in its own short dry trekking window."),
            8: ("avoid", "Monsoon continues; heavy rain and flooding risk, especially in the hills."),
            9: ("mixed", "Monsoon retreating from the west/north; Tamil Nadu's northeast monsoon can still bring rain."),
            10: ("good", "Post-monsoon window opens - clear, warm, excellent nationwide."),
            11: ("good", "Excellent nationwide; the true start of peak season."),
            12: ("good", "Peak season - cool, dry, busy and pricier for it."),
        },
    },
    "mongolia": {
        "summary": "One short travel season, late May to early Sept; winters are ferociously cold and most tourism infrastructure closes.",
        "months": {
            1: ("avoid", "Extreme cold, often below -20C. Almost no tourist infrastructure operating outside Ulaanbaatar."),
            2: ("avoid", "Still bitterly cold. Not a travel window."),
            3: ("avoid", "Cold, with unpredictable late snow. Still off-season."),
            4: ("avoid", "Shoulder cold and unpredictable; most Gobi operators not yet running full tours."),
            5: ("mixed", "Season opening late in the month; nights still cold, some operators starting up."),
            6: ("good", "Season properly open - warm days, cold nights, full Gobi/steppe tours running."),
            7: ("good", "Peak season and Naadam festival - best weather, busiest and most expensive week of the year."),
            8: ("good", "Excellent, slightly quieter and cheaper than July."),
            9: ("mixed", "Season closing - cold nights returning, some operators winding down mid-month."),
            10: ("avoid", "Season over for most tour operators; snow risk returning."),
            11: ("avoid", "Winter arriving hard. Not a travel window."),
            12: ("avoid", "Deep winter. Not a travel window outside Ulaanbaatar itself."),
        },
    },
    "myanmar": {
        "summary": "Cool/dry Nov-Feb is best; hot Mar-May; monsoon Jun-Oct heaviest on the coasts, lighter around Bagan/Mandalay's rain shadow.",
        "months": {
            1: ("good", "Cool and dry - the best month, especially for Bagan's temple sunrises."),
            2: ("good", "Still cool and dry nationwide."),
            3: ("mixed", "Heat building, especially in the central plain around Bagan and Mandalay."),
            4: ("mixed", "Very hot, often 40C+ around Bagan and Mandalay. Thingyan water festival mid-month is a highlight but the hottest week."),
            5: ("mixed", "Pre-monsoon heat and building humidity; rains beginning on the coasts."),
            6: ("mixed", "Monsoon established on the Rakhine/Tanintharyi coasts; central dry zone (Bagan, Mandalay) still relatively light rain."),
            7: ("mixed", "Wet on the coasts and in the delta; the central dry zone remains the most travellable region."),
            8: ("mixed", "Similar to July - coastal areas wet, central plain comparatively dry."),
            9: ("mixed", "Rains easing; still unsettled on the coasts."),
            10: ("good", "Monsoon ending, conditions improving nationwide."),
            11: ("good", "Cool season begins - excellent conditions return."),
            12: ("good", "Cool and dry, peak season."),
        },
    },
    "bhutan": {
        "summary": "Spring (Mar-May) and autumn (Sep-Nov) are prime for clear Himalayan views and festivals; monsoon Jun-Aug, cold Dec-Feb.",
        "months": {
            1: ("mixed", "Cold, especially at altitude, but clear skies. Lower-valley sightseeing (Paro, Thimphu, Punakha) still fine."),
            2: ("mixed", "Still cold; clearing toward spring. Rhododendrons not yet blooming."),
            3: ("good", "Spring begins - rhododendrons bloom, clear mountain views, good trekking lower down."),
            4: ("good", "Excellent - Paro Tshechu festival season, good weather nationwide."),
            5: ("mixed", "Warming, building humidity ahead of the monsoon; still workable."),
            6: ("avoid", "Monsoon arrives - heavy rain, landslide risk on mountain roads, obscured views."),
            7: ("avoid", "Monsoon peak. Trekking routes muddy and leech-heavy; poor visibility."),
            8: ("avoid", "Monsoon continues. Not a good trekking or sightseeing window."),
            9: ("mixed", "Monsoon easing through the month; improving toward the excellent autumn window."),
            10: ("good", "Prime season - clear skies, best mountain views, popular festival season."),
            11: ("good", "Excellent - clear, cool, and the second major festival window (Thimphu Tshechu)."),
            12: ("mixed", "Cold arriving but generally still clear; good for lower-altitude sightseeing."),
        },
    },
    "australia": {
        "summary": "Two opposite systems: temperate south has 4 seasons (summer Dec-Feb); tropical north runs wet Nov-Apr (cyclone/stinger risk) vs dry May-Oct (its best window).",
        "months": {
            1: ("mixed", "Peak summer in the south - hot, crowded, priciest fortnight of the year. The tropical north is deep in wet/cyclone season with box jellyfish in the water."),
            2: ("mixed", "Still peak summer south; still cyclone and stinger season north - same trade-off as January."),
            3: ("mixed", "South cooling into a pleasant autumn shoulder. North's wet season is easing but cyclone risk continues into April."),
            4: ("good", "Excellent autumn shoulder in the south. North's wet season is ending - a good transition month either way."),
            5: ("good", "South mild and pleasant. North's dry season begins - excellent, and increasingly the better half of the country to be in."),
            6: ("good", "North's dry season in full swing - the best month for Cairns/Darwin/the reef. South is cool-cold, good for the Australian Alps and Tasmania."),
            7: ("good", "North at its dry-season best, peak visiting season there. South is winter - cold on the coast, good in the Alps and Tasmania for snow."),
            8: ("good", "Still excellent in the tropical north. South remains winter-cool."),
            9: ("good", "North's dry season winding down but still good. South's spring shoulder begins - a genuinely excellent nationwide window opening."),
            10: ("mixed", "South in full, excellent spring. North's 'build-up' begins - humidity rising, first stinger warnings return in the far north."),
            11: ("mixed", "South heading into early summer, still good. North's wet/cyclone/stinger season begins in earnest."),
            12: ("mixed", "South's summer peak begins (Christmas price spike). North deep in wet season - the riskiest month to be swimming or driving remote roads up there."),
        },
    },
    "new zealand": {
        "summary": "Reverse-hemisphere seasons: summer (best weather, Great Walks season) Dec-Feb; South Island ski season mid-Jun-early Oct, peaking Jul-Aug.",
        "months": {
            1: ("good", "Peak summer. Best hiking and Great Walks conditions, warm and long days - also the busiest, priciest fortnight of the year."),
            2: ("good", "Still excellent summer weather, slightly quieter and cheaper than January."),
            3: ("good", "Late summer into autumn - Great Walks season still open, fewer crowds, harvest season in wine country."),
            4: ("good", "Autumn, still pleasant. Great Walks season (with full hut services) ends mid-to-late April - book before, not after."),
            5: ("mixed", "Cooling fast. Great Walks huts now unserviced; South Island weather turning genuinely wintry at altitude."),
            6: ("mixed", "Ski season opens mid-month in the South Island - great for skiers, but tramping is now a serious cold-weather undertaking, not a casual walk."),
            7: ("mixed", "Peak ski season (best snow) in Queenstown/Wanaka. Elsewhere it's cold, wet and short-dayed - the low season for general backpacking."),
            8: ("mixed", "Still peak ski season. Rest of the country remains cold, wet winter."),
            9: ("mixed", "Ski season winding down through the month. Spring is starting but weather is still unsettled and Great Walks huts aren't yet serviced."),
            10: ("mixed", "Great Walks season reopens with hut services, but early-season weather is genuinely variable - snow is still possible at altitude on the higher tracks."),
            11: ("good", "Spring turning to early summer - reliably good hiking weather, Great Walks in full swing, before the December crowds."),
            12: ("good", "Early summer begins, Great Walks season at its best, Christmas crowds and prices building toward the January peak."),
        },
    },
    "south korea": {
        "summary": "Narrow jangma monsoon late Jun-Jul; typhoon risk clusters late Aug-mid Sep; Oct is the true peak (dry, foliage); cold dry winters.",
        "months": {
            1: ("mixed", "Coldest, driest month (Seoul averages -6 to 2C) but clear and sunny - good for skiing (Yongpyong, Vivaldi Park), cold for a full day of walking sightseeing."),
            2: ("mixed", "Still cold and dry, warming toward the end of the month; ski season continuing."),
            3: ("mixed", "Transitional - cold easing, but this is also when 'yellow dust' (fine sand blown in from China/Mongolia) starts; Jeju's cherry blossoms begin very late in the month."),
            4: ("good", "Cherry blossom peak nationwide, moving north to Seoul by early April (Jinhae festival first week); mild and pleasant, though yellow dust can still flare up on a given day."),
            5: ("good", "Warm, dry, comfortable - one of the best all-round months, before the monsoon and before peak summer heat."),
            6: ("mixed", "Dry and warm early in the month; jangma (the monsoon) typically arrives around June 19-25, starting in Jeju and the south first."),
            7: ("avoid", "Peak jangma monsoon - the wettest, most humid month nationwide, with rain continuing to around July 20 most years."),
            8: ("mixed", "Hottest, most humid month (feels-like temperatures near 38C); monsoon rain has usually ended, but typhoon season risk is building toward its peak."),
            9: ("good", "Monsoon and worst heat are both over - genuinely one of the best months. A tail typhoon risk lingers into the first half of the month (most landfalls cluster late Aug-mid Sept) but that's the exception, not a reason to avoid the month."),
            10: ("good", "The true peak month: dry, mild, minimal rain, and peak autumn foliage sweeps south from Seoraksan through the month."),
            11: ("good", "Cooling further; foliage reaches Seoul and the south (Naejangsan) by early-to-mid November; dry and comfortable."),
            12: ("mixed", "Cold and dry, clear skies; ski season opens in earnest by mid-month; good for city sightseeing wrapped up warm."),
        },
    },
    "japan": {
        "summary": "Honshu-focused: tsuyu rains Jun-mid Jul, typhoon risk peaks Aug-Sep, cherry blossoms move north Mar-May, foliage peaks Nov. Okinawa runs on its own subtropical calendar - see the seasonal-japan-okinawa doc.",
        "months": {
            1: ("good", "Cold, dry, clear on the Pacific side (Tokyo/Kyoto/Osaka); prime ski season in Hokkaido and the Japan Alps. New Year (Jan 1-3) closes many shops/restaurants and is busy for travel right around it."),
            2: ("good", "Still cold and dry; peak powder season for Hokkaido skiing; plum blossoms start late in the month."),
            3: ("mixed", "Transitional and unpredictable - early cherry blossoms possible in Kyushu/southern Honshu late in the month, but Tokyo/Kyoto are usually still a week or two from bloom."),
            4: ("mixed", "Cherry blossom peak in Tokyo/Kyoto/Osaka (usually Apr 5-10) - stunning, but the single most crowded and expensive week of the year; book accommodation months ahead."),
            5: ("good", "Warm, dry, comfortable - one of the best all-round months, apart from Golden Week at the very start (Apr 29-May 6), when transport and hotels nationwide are booked solid and priced up."),
            6: ("mixed", "Tsuyu (rainy season) sets in across Honshu, persistent rain and high humidity; Okinawa's own rainy season is just ending by month's end."),
            7: ("mixed", "Tsuyu continues into mid-month on Honshu, then breaks into full humid summer heat; Okinawa is already in its dry beach season."),
            8: ("avoid", "Peak heat and humidity nationwide (Tokyo/Kyoto/Osaka routinely mid-30sC and stifling); typhoon season building toward its peak; Obon (around Aug 13-16) is the single most congested, most expensive week for domestic transport and hotels all year."),
            9: ("mixed", "Typhoon risk peaks this month (hardest on Okinawa and the southern coast); heat and humidity linger into early September before starting to ease."),
            10: ("good", "Typhoon risk fading fast, heat breaking, comfortable temperatures return; early autumn colour starts in Hokkaido and the north."),
            11: ("good", "One of the best months: dry, mild, clear skies, and peak autumn foliage sweeps south through Kyoto and Tokyo (Kyoto's maples usually peak mid-to-late November)."),
            12: ("mixed", "Cold and dry with clear skies; ski season opens in earnest in Hokkaido/the Japan Alps by mid-month; late December sees a travel and closure spike around New Year."),
        },
    },
    "peru": {
        "summary": "Andes dry May-Oct (best trekking); wet Nov-Apr peaking Jan-Feb; Inca Trail closed all of February for maintenance; coast/Amazon run on separate cycles.",
        "months": {
            1: ("mixed", "Cusco/Andes wet season, afternoon rain common but Machu Picchu stays open by train; Lima's coastal summer is hot and dry."),
            2: ("avoid", "Wettest month in the Andes and the Inca Trail closes all month for maintenance - Machu Picchu itself stays open via train."),
            3: ("mixed", "Rains easing through the month; Inca Trail reopens 1 March but early permits sell out fast on pent-up demand."),
            4: ("good", "Shoulder-season sweet spot - trails drying, landscapes still green, crowds and prices below the June-August peak."),
            5: ("good", "Dry season begins in the Andes. Excellent trekking conditions."),
            6: ("good", "Peak dry season, cold clear nights in Cusco, trekking crowds and prices climbing."),
            7: ("good", "Height of the dry season and the busiest month on the Inca Trail - permits booked months ahead."),
            8: ("good", "Dry and excellent, still very busy."),
            9: ("good", "Dry season continuing, slightly quieter than July-August."),
            10: ("good", "Last reliably dry month in the Andes; still a good trekking window."),
            11: ("mixed", "Rains building in the Andes; still workable, noticeably thinner crowds."),
            12: ("mixed", "Wet season established in the Andes; Lima's coastal summer is in full swing by contrast."),
        },
    },
    "colombia": {
        "summary": "Bimodal nationwide: dry Dec-Mar and Jul-Aug, wetter Apr-May and Oct-Nov; regions vary (Caribbean coast driest Dec-Mar, Amazon wet year-round).",
        "months": {
            1: ("good", "Dry season. Caribbean coast (Cartagena, Santa Marta, Tayrona) at its best."),
            2: ("good", "Dry season continues nationwide."),
            3: ("mixed", "Rains building toward the wetter April-May stretch."),
            4: ("avoid", "One of the wettest months in the Andean region; landslide risk on mountain roads."),
            5: ("mixed", "Rains easing off through the month."),
            6: ("mixed", "Short dry spell beginning."),
            7: ("good", "Second dry season begins, good conditions nationwide."),
            8: ("good", "Dry season continues; Pacific coast whale-watching season underway."),
            9: ("mixed", "Rains returning."),
            10: ("avoid", "One of the wettest months nationwide."),
            11: ("mixed", "Rains easing toward the December dry season."),
            12: ("good", "Dry season begins, Caribbean coast excellent, but Cartagena and Medellin get busy and pricier for the holidays."),
        },
    },
    "ecuador": {
        "summary": "Four climates on four different clocks: highlands dry Jun-Sep, coast dry/warm Dec-May, Amazon driest Jun-Oct, Galapagos cool-dry Jun-Nov / warm-wet Dec-May.",
        "months": {
            1: ("mixed", "Coast hot and wet (beach season); highlands wetter; Galapagos entering its warm, wet season."),
            2: ("mixed", "Similar to January - coast warm and rainy, Galapagos hot and humid."),
            3: ("mixed", "Wettest month in the highlands; coast still in its warm rainy peak."),
            4: ("mixed", "Highland rain easing; coast in the tail of its wet season."),
            5: ("mixed", "Transition month across all regions."),
            6: ("good", "Highland dry season begins - best hiking conditions; Galapagos turning cool and dry."),
            7: ("good", "Peak dry season in the highlands and Amazon; Galapagos excellent for wildlife."),
            8: ("good", "Dry season continues in the highlands and Amazon; Galapagos good."),
            9: ("good", "Dry highlands, good Amazon conditions, Galapagos good."),
            10: ("mixed", "Highland rain returning; coast's dry season beginning; Amazon still good."),
            11: ("mixed", "Coast entering its dry, better-beach-weather season; highlands wetter; Galapagos warming."),
            12: ("mixed", "Coast dry and warm (good beach time); highlands wet; Galapagos turning hot and humid."),
        },
    },
    "bolivia": {
        "summary": "Altiplano dry season May-Oct gives full salt-flat access; wet season Dec-Mar (peak Jan-Feb) floods Uyuni into its famous mirror but cuts some routes.",
        "months": {
            1: ("mixed", "Wet season peak - Uyuni's mirror effect at its best, but some salt-flat areas and Incahuasi Island can be inaccessible."),
            2: ("mixed", "Wettest month, same tradeoffs as January."),
            3: ("mixed", "Rains easing; still good mirror conditions at Uyuni."),
            4: ("good", "Shoulder month - lingering water for mirror photography alongside mostly-dry, accessible terrain."),
            5: ("good", "Dry season begins, full physical access across the salt flats."),
            6: ("good", "Dry, cold nights on the Altiplano - La Paz and Uyuni can drop below freezing after dark."),
            7: ("good", "Peak dry season, coldest nights, clearest skies for stargazing."),
            8: ("good", "Dry season continues."),
            9: ("good", "Dry, warming slightly."),
            10: ("mixed", "Dry season ending, rains beginning to build."),
            11: ("mixed", "Transition into the wet season."),
            12: ("mixed", "Wet season established; salt-flat mirror season beginning."),
        },
    },
    "chile": {
        "summary": "Opposite logics in one country: Atacama desert (north) workable year-round, mildest in shoulder months; Patagonia (south) only fully open Nov-Mar.",
        "months": {
            1: ("mixed", "Patagonia at peak season - warm, all trails open, busiest and priciest; Atacama fine but hot and crowded."),
            2: ("mixed", "Same as January - Patagonia's warmest, windiest month."),
            3: ("good", "Patagonia's shoulder season - fewer crowds, milder wind; Atacama pleasant. Good month to combine both."),
            4: ("mixed", "Patagonia's season closing, some refugios shutting; Atacama excellent."),
            5: ("mixed", "Patagonia largely closed for the season; Atacama mild and uncrowded."),
            6: ("avoid", "Patagonia deep off-season - cold, most trekking infrastructure closed; Atacama still fine but this is a bad month for the country's headline attraction."),
            7: ("avoid", "Patagonia mid-winter closure continues; Atacama fine."),
            8: ("avoid", "Patagonia still closed; Atacama fine."),
            9: ("mixed", "Patagonia reopening late in the month; Atacama excellent."),
            10: ("mixed", "Patagonia opening, weather still unpredictable; Atacama excellent."),
            11: ("good", "Patagonia's sweet spot - milder winds, fewer crowds than summer; Atacama great. Best month to combine both regions."),
            12: ("mixed", "Patagonia's peak season beginning - busy, pricier; Atacama hot but fine."),
        },
    },
    "argentina": {
        "summary": "Buenos Aires and the north (Iguazu, Salta) best in shoulder seasons Mar-May/Sep-Nov; Patagonia only fully open Nov-Mar, largely shut Jun-Aug.",
        "months": {
            1: ("mixed", "Patagonia at peak season - busiest, priciest, all trails open; Buenos Aires and the north hot and humid."),
            2: ("mixed", "Same pattern - Iguazu Falls still impressive, BA/north humidity continuing."),
            3: ("good", "Shoulder sweet spot - BA and the north cooling into pleasant weather, Patagonia still open and less busy."),
            4: ("good", "Excellent for Iguazu and Salta's wine-harvest season; Patagonia's trekking season closing by month end."),
            5: ("mixed", "Patagonia mostly closing for the season; BA and the north remain pleasant."),
            6: ("avoid", "Patagonia deep winter - roads and trails closed outside ski resorts; BA cool but workable."),
            7: ("mixed", "Patagonia's ski season (Bariloche) is good if that's the goal, otherwise closed for trekking; BA cold."),
            8: ("avoid", "Patagonia still shut for trekking (skiing continues); BA cold."),
            9: ("mixed", "Patagonia reopening late in the month; BA and the north entering their best stretch."),
            10: ("good", "Patagonia opening up, BA and the north excellent - a good month to see the whole country."),
            11: ("good", "Patagonia's ideal shoulder window - milder winds, fewer crowds; BA and the north still pleasant before summer humidity."),
            12: ("mixed", "Patagonia's summer season begins - busy, pricier; BA and the north turning hot and humid."),
        },
    },
    "brazil": {
        "summary": "Rio/south best Sep-Mar (incl. Carnival); Amazon dry season roughly May-Oct; Northeast beaches warm year-round, driest Sep-Mar.",
        "months": {
            1: ("mixed", "Rio/south hot, festive and humid, peak beach season; Amazon in its wet season - better for flooded-forest canoe routes than trails."),
            2: ("good", "Carnival season (dates vary) - Rio and Salvador at their most vivid but also most expensive and crowded."),
            3: ("good", "Carnival tail some years; Rio/south still excellent; Amazon still wet."),
            4: ("mixed", "Rio/south cooling into a pleasant shoulder; Amazon transitioning toward its dry season."),
            5: ("good", "Amazon dry season begins - good for jungle lodges and trail-based wildlife; Northeast beaches entering their driest, sunniest stretch."),
            6: ("good", "Dry season established in the Amazon and Northeast; southern Brazil turns genuinely cold, occasional snow in the far south."),
            7: ("good", "Similar to June - good Amazon/Northeast conditions; Brazilian winter in the south."),
            8: ("good", "Dry season continues in the Amazon and Northeast."),
            9: ("good", "Amazon dry season ending, Northeast winds peak for kitesurfing; Rio/south entering a pleasant, quieter shoulder."),
            10: ("mixed", "Amazon rains returning; Rio/south good and less crowded than summer."),
            11: ("mixed", "Amazon wet season building; Rio/south warming toward the summer peak."),
            12: ("mixed", "Rio/south summer season and holiday crowds building; Amazon in its wet season."),
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
