---
id: severe-winter
title: Prolonged severe winter
icon: snowflake
order: 13
summary: A week or more of deep snow and hard frost with heating fuel short. Cold-Health Alerts, 18 degrees in one room, gas and power cuts, frozen pipes, falls.
modules: [shelter-heat, power, food, water, medical, vehicles-fuel, comms, community]
overlays: [health, fuel, rail]
reviewed: null
sources:
  - title: National Risk Register 2025
    doc: nrr-2025
    as_at: 2025-01-16
  - title: Adverse Weather and Health Plan 2026 to 2027 (UKHSA)
    doc: awhp-2026
    as_at: 2026-03-31
  - title: Keep warm, keep well (NHS)
    kiwix: nhs_uk/www.nhs.uk/live-well/seasonal-health/keep-warm-keep-well/
    as_at: 2026-09
  - title: Hypothermia (NHS)
    kiwix: nhs_uk/www.nhs.uk/conditions/hypothermia/
    as_at: 2026-09
  - title: Cold Weather Payment (GOV.UK)
    kiwix: govuk_resilience/www.gov.uk/cold-weather-payment
    as_at: 2026-09
  - title: Approved Document J
    doc: ad-j
    as_at: 2022-06
  - title: Winter of 1962–1963 in the United Kingdom (Wikipedia)
    kiwix: wikipedia_en_all_maxi/Winter_of_1962–1963_in_the_United_Kingdom
    as_at: 2026-02-15
  - title: Winter of 1946–47 in the United Kingdom (Wikipedia)
    kiwix: wikipedia_en_all_maxi/Winter_of_1946–47_in_the_United_Kingdom
    as_at: 2026-02-15
  - title: Condensing boiler (Wikipedia)
    kiwix: wikipedia_en_all_maxi/Condensing_boiler
    as_at: 2026-02-15
---

## Right now

{{#if heating}}**Heat one room and live in it.**{{else}}**One room, everyone in it.**{{/if}} The temperature to aim for, the draught-proofing, the layers and what may and may not burn indoors are in the [shelter and heat module](module:shelter-heat) below; the first hour is spent choosing the room, shutting the doors to the rest, and moving bedding into it.

**Read the alert.** Cold-Health Alerts run from 1 November to 30 March (the Cold Weather Payment window runs a day longer, to 31 March): yellow means impacts on the vulnerable, amber means the whole health service feels it, red means "significant risk to life for even the healthy population" ([AWHP, p. 34](doc:awhp-2026#page=34); [Cold Weather Payment](kiwix:govuk_resilience/www.gov.uk/cold-weather-payment)). The register's scenario is snow over 30 cm lying for at least seven days across lowland Britain, daily means below minus 3 °C and nights below minus 10 °C, with falls, road accidents, hypothermia and excess deaths ([NRR 2025, p. 143](doc:nrr-2025#page=143)).

**Falls** are the commonest injury: grit the path, wear boots with grip, and keep older people in until it thaws ([NRR 2025, p. 143](doc:nrr-2025#page=143)).

{{module:shelter-heat}}

## First 72 hours

- **Hypothermia** starts with shivering and clumsiness and ends with drowsiness and no shivering; confusion means an emergency — [[call 999]] ([Hypothermia (NHS)](kiwix:nhs_uk/www.nhs.uk/conditions/hypothermia/)); the first aid is on the [hypothermia card](card:hypothermia). Frostbite and chilblains are the outdoor injuries ([Frostbite (WikiMed)](kiwix:wikipedia_en_medicine_maxi/Frostbite)).
- **Fuel.** Gas boilers stop without electricity ([What still works](page:what-still-works)); heating oil and LPG deliveries fail on snowbound roads ([NRR 2025, p. 69](doc:nrr-2025#page=69)); if gas supply itself fails in winter the plan is 3-hour rolling power cuts while domestic gas is protected ([NRR 2025, p. 94](doc:nrr-2025#page=94)). Ration fuel to the warm room from day one.
- **Boiler locked out in a hard frost?** A condensing boiler that stops on a freezing night has usually frozen its external condensate pipe, the thin plastic pipe that drips outside; thaw it with warm (not boiling) water or a hot-water bottle, reset the boiler, and lag the pipe before the next frost ([Condensing boiler](kiwix:wikipedia_en_all_maxi/Condensing_boiler)).
- **Pipes.** Lag every pipe you can reach in the loft, the garage and outside, and the loft tank; open the loft hatch in a hard frost so house warmth reaches the tank; know where the stopcock is; {{#if water}}if you leave the house for more than a night, turn the water off at the stopcock and drain the system, because a burst shows when it thaws{{else}}with the mains already off, turn the stopcock off now so that a burst does not flood the house when supply and thaw arrive together{{/if}} ([Pipe insulation](kiwix:wikipedia_en_all_maxi/Pipe_insulation); [Stopcock](kiwix:wikipedia_en_all_maxi/Stopcock); [Tools and repair module](module:tools-repair)).
- **Food and drink.** Warm food and drinks matter; oats, soup, stew from the store ([Food module](module:food)). A fridge is not needed: a north-facing porch is one.
- **Phones and power.** Snow brings down lines; a regional outage in winter is the register's worst case for the electricity network ([NRR 2025, p. 92](doc:nrr-2025#page=92)); the [grid collapse playbook](playbook:grid-collapse) runs in parallel, and the operator needs telling — [[call 105]].

{{module:power}}

{{module:medical}}

{{module:food}}

## First month

- **Water.** Mains pipes freeze and burst under roads; standpipes and bowsers follow; store and treat as in the [water module](module:water); melted snow is water once boiled.
- **Snow on the house.** Wet snow is heavy and structures fail under snow load; flat roofs, conservatories, carports and lean-tos carry it worst, so clear them from the ground with a rake or a broom on a pole, never from a ladder on ice, and keep people out from under a sagging roof ([Snow](kiwix:wikipedia_en_all_maxi/Snow)). Clear paths early, before snow is trodden into ice, and grit with salt or sand; do not pour water on a path, which freezes into a worse hazard ([Snow removal](kiwix:wikipedia_en_all_maxi/Snow_removal)).
- **Vehicles.** The winter kit for the boot is in the [vehicles and fuel module](module:vehicles-fuel) below; do not set out in a red warning; a stuck car is a shelter, so stay with it, keep the exhaust clear of snow if the engine is run at all, and wait for help rather than walking into a whiteout ([Snow chains](kiwix:wikipedia_en_all_maxi/Snow_chains)).
- **Money.** Cold Weather Payments are paid automatically to eligible households for each seven-day period of mean temperature at or below 0 °C between 1 November and 31 March ([Cold Weather Payment](kiwix:govuk_resilience/www.gov.uk/cold-weather-payment)); Winter Fuel Payments and the Priority Services Register cover the rest ([Priority Services Register](kiwix:govuk_resilience/www.thepsr.co.uk/)).
- **Warm hubs.** Councils, libraries, churches and village halls open warm spaces (warm banks) in a cold spell, usually with a hot drink and a charger; ask the council, the library or the parish noticeboard which is open and when, and take anyone whose house cannot be kept warm ([Warming center](kiwix:wikipedia_en_all_maxi/Warming_center); [Community module](module:community)).
- **Neighbours.** The people who die in a cold spell are older, alone and indoors; a daily knock is the intervention ([Community module](module:community); [AWHP, p. 22](doc:awhp-2026#page=22)).
- **Illness.** Flu, pneumonia, heart attacks and strokes all rise in cold weather; the cards and the NHS pages are in the box ([Flu (NHS)](kiwix:nhs_uk/www.nhs.uk/conditions/flu/); [Heart attack card](card:heart-attack); [Stroke card](card:stroke)).

{{module:water}}

{{module:vehicles-fuel}}

{{module:community}}

## Long term

The winter of 1962 to 1963 froze Britain from Boxing Day to March, the sea iced over at Herne Bay and the ground stayed frozen for two months ([Winter of 1962–1963 in the United Kingdom](kiwix:wikipedia_en_all_maxi/Winter_of_1962–1963_in_the_United_Kingdom)); 1947 added a coal shortage, power cuts and ration cuts to the snow ([Winter of 1946–1947 in the United Kingdom](kiwix:wikipedia_en_all_maxi/Winter_of_1946–47_in_the_United_Kingdom)). A house that has been through one is insulated to current standards ([Approved Document L volume 1](doc:ad-l1)), has a stove with a safe flue and a season's fuel ([Approved Document J, p. 11](doc:ad-j#page=11)), a lawfully sited oil tank if it burns oil ([Approved Document J, p. 65](doc:ad-j#page=65)), and a community that has a warm hub with a generator ([Warming center](kiwix:wikipedia_en_all_maxi/Warming_center); [Community module](module:community)). A winter that does not end is the [impact winter playbook](playbook:impact-winter).

{{module:comms}}

## UK specifics

- **Alerts.** Cold-Health Alerts (1 November to 30 March) come from UKHSA and the Met Office and are cascaded to the public through the news ([AWHP, p. 34](doc:awhp-2026#page=34); [AWHP, p. 22](doc:awhp-2026#page=22)); Met Office snow and ice warnings are yellow, amber and red ([National Severe Weather Warning Service](kiwix:wikipedia_en_all_maxi/National_Severe_Weather_Warning_Service)).
- **The 2018 "Beast from the East"** is the register's reference event: transport disruption, school closures and power cuts across the UK ([NRR 2025, p. 143](doc:nrr-2025#page=143); [2018 British Isles cold wave](kiwix:wikipedia_en_all_maxi/2018_British_Isles_cold_wave)).
- **Gas safety:** {{#if phones}}the gas emergency line is 0800 111 999 in Great Britain and 0800 002 001 in Northern Ireland; a smell of gas means windows open, no switches, out, and the call{{else}}a smell of gas means windows open, no switches, everyone out and the supply off at the meter; with the phones down, send someone to the nearest fire station rather than waiting for a line that will not connect{{/if}} ([HSE domestic gas](kiwix:govuk_resilience/www.hse.gov.uk/gas/domestic/index.htm); [UK numbers](page:uk-numbers)).
- **Heating oil and diesel at home.** Neither is covered by the petrol limits ([vehicles and fuel](module:vehicles-fuel)). A fixed heating-oil tank of up to 3,500 litres stands on a hard base extending 300 mm beyond it, at least 1.8 m from any part of a building or behind a 30-minute fire wall, at least 760 mm from a boundary or behind a fire wall, and inside a bund where a leak could reach a drain, a well or a watercourse ([Approved Document J, p. 65](doc:ad-j#page=65)). Jerrycans of diesel for a generator stay outside, in a ventilated store, away from anything that burns.
- **Support:** Cold Weather Payments, Winter Fuel Payments, the Priority Services Register, and council warm hubs, listed by the council and the library and on the hall noticeboard ([Cold Weather Payment](kiwix:govuk_resilience/www.gov.uk/cold-weather-payment); [Warming center](kiwix:wikipedia_en_all_maxi/Warming_center)).
- **Where the help is:** hospitals, pharmacies and open fuel stations on the map ([health and fuel overlay](map:?overlay=health&overlay=fuel)); stations on the [rail overlay](map:?overlay=rail).
- **Extreme weather** guidance for every hazard is on one GOV.UK page ([Extreme weather and natural hazards](kiwix:govuk_resilience/www.gov.uk/guidance/extreme-weather-and-natural-hazards)).

## Checklist

- [ ] One warm room chosen and everyone in it; 18 °C target; thermometer in it {#warm-room-18 now}
- [ ] Curtains shut at dusk, doors closed, draughts blocked, hats and layers on {#curtains-and-layers now}
- [ ] CO alarm tested; nothing burning indoors that belongs outdoors {#co-alarm-tested now}
- [ ] Stove flue swept and checked; a week of fuel by the stove {#stove-and-fuel hour}
- [ ] Stopcock found; exposed pipes, loft tank and boiler condensate pipe lagged {#pipes-protected hour}
- [ ] Path gritted; boots with grip; older people kept in until the thaw {#grit-and-boots hour}
- [ ] Neighbours over 65 or living alone knocked on every day {#daily-knock hour}
- [ ] Warm food, oats, soup and stock for two weeks {#warm-food-store today}
- [ ] Prescriptions for a fortnight collected before the snow {#prescriptions-collected today}
- [ ] Flat roof and conservatory cleared from the ground; nearest warm hub and its hours known {#snow-load-and-warm-hub today}
- [ ] Winter kit in the car; no journeys in a red warning {#car-winter-kit today}
- [ ] Cold Weather Payment eligibility and PSR registration checked {#payments-and-psr week}

## Go deeper

- [Shelter and heat module](module:shelter-heat)
- [Hypothermia card](card:hypothermia)
- [Carbon monoxide card](card:carbon-monoxide)
- [Adverse Weather and Health Plan, the alert levels](doc:awhp-2026#page=34)
- [Approved Document J, carbon monoxide alarms](doc:ad-j#page=43)
- [Approved Document J, oil storage tanks](doc:ad-j#page=65)
- [Winter of 1962–1963 (Wikipedia)](kiwix:wikipedia_en_all_maxi/Winter_of_1962–1963_in_the_United_Kingdom)
- [Wood-burning stove (Wikipedia)](kiwix:wikipedia_en_all_maxi/Wood-burning_stove)
- [Winter weather (Ready.gov)](kiwix:www.ready.gov_en/www.ready.gov/winter-weather)
- [The Great Outdoors Q&A](kiwix:outdoors.stackexchange.com_en_all/questions)
- [Hospitals and fuel on the map](map:?overlay=health&overlay=fuel)
- [Grid collapse playbook](playbook:grid-collapse)
- [Impact winter playbook](playbook:impact-winter)
- [Basic Cold Weather Manual, FM 31-70](doc:fm-31-70-cold-weather)
- [Canadian Prepper: winter prepping](kiwix:canadian-prepper_en_winterprepping/index.html)
- [Camping and Woodcraft (Kephart, 1917)](doc:kephart-camping-and-woodcraft)
- [Survival, ATP 3-50.21 (US Army, 2018)](doc:atp-3-50-21-survival)
- [Shelter and staying warm](page:fieldcraft-shelter)
- [Reading the weather and exposure](page:fieldcraft-weather)
- [Fire](page:fieldcraft-fire)
