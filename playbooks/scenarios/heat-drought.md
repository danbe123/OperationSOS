---
id: heat-drought
title: Heatwave, drought and water failure
icon: thermometer
order: 14
summary: Five days over 35 degrees, three dry winters, hosepipe bans, then standpipes and bowsers. Cooling people, saving water, wildfire, and growing food in a drought.
modules: [water, medical, shelter-heat, food, growing-food, livestock, community]
overlays: [water, health, flood-zones]
reviewed: null
sources:
  - title: National Risk Register 2025
    doc: nrr-2025
    as_at: 2025-01-16
  - title: Adverse Weather and Health Plan 2026 to 2027 (UKHSA)
    doc: awhp-2026
    as_at: 2026-03-31
  - title: Beat the heat (GOV.UK)
    kiwix: govuk_resilience/www.gov.uk/guidance/beat-the-heat-hot-weather-advice
    as_at: 2026-09
  - title: Heat exhaustion and heatstroke (NHS)
    kiwix: nhs_uk/www.nhs.uk/conditions/heat-exhaustion-heatstroke/
    as_at: 2026-09
  - title: Drinking water for consumers (DWI)
    kiwix: govuk_resilience/www.dwi.gov.uk/consumers/
    as_at: 2026-09
  - title: 2022 United Kingdom heatwaves (Wikipedia)
    kiwix: wikipedia_en_all_maxi/2022_United_Kingdom_heatwaves
    as_at: 2026-02-15
  - title: 1976 British Isles heatwave (Wikipedia)
    kiwix: wikipedia_en_all_maxi/1976_British_Isles_heatwave
    as_at: 2026-02-15
  - title: Approved Document O
    doc: ad-o
    as_at: 2021-12
---

## Right now

**Cool the people, then the house.** Heat-Health Alerts run from 1 June to 30 September; a red alert is "significant risk to life for even the healthy population" ([AWHP, p. 34](doc:awhp-2026#page=34)). The register's scenario is five days above 35 °C, approaching or passing 40 °C in south-eastern, eastern and central England, affecting 50 to 70% of the population, with excess deaths and failures of transport, power and water ([NRR 2025, p. 141](doc:nrr-2025#page=141)); it happened at Coningsby on 19 July 2022 at 40.3 °C ([2022 United Kingdom heatwaves](kiwix:wikipedia_en_all_maxi/2022_United_Kingdom_heatwaves)).

**Heat exhaustion** (sweating, dizziness, cramps, nausea) is cooled and rehydrated within 30 minutes; **heatstroke** (hot skin, confusion, fits, no better after 30 minutes) means cold water on the skin now and an ambulance — [[call 999]] ([Heat exhaustion and heatstroke (NHS)](kiwix:nhs_uk/www.nhs.uk/conditions/heat-exhaustion-heatstroke/); [Heat stroke card](card:heat-stroke)). Babies, older people and anyone on diuretics or mental-health medicines are the risk group ([Beat the heat](kiwix:govuk_resilience/www.gov.uk/guidance/beat-the-heat-hot-weather-advice)).

**The house:** blinds and curtains shut on the sunny side by day, windows open at night when it is cooler outside than in, sleep on the lowest floor, {{#if power}}wet sheets and a fan{{else}}wet sheets and a hand fan, since the electric one is off{{/if}}, no cooking with the oven ([Beat the heat](kiwix:govuk_resilience/www.gov.uk/guidance/beat-the-heat-hot-weather-advice)).

**Water:** {{#if water}}fill every container and the bath now, before a notice or a failure, and keep the butts covered{{else}}use the stored water and find the bowser or bottled water station the company has announced; the Priority Services Register gets deliveries{{/if}} ([Priority Services Register](kiwix:govuk_resilience/www.thepsr.co.uk/)).

{{module:medical}}

## First 72 hours

- **Drink before thirst;** pale urine is the target; two to three litres a day for an adult in heat, more with work; oral rehydration solution for anyone dizzy or cramping ([Dehydration card](card:dehydration); [Dehydration (NHS)](kiwix:nhs_uk/www.nhs.uk/conditions/dehydration/)).
- **Food safety.** Fridges struggle above 30 °C; keep them shut and full; chilled food above 8 °C for more than four hours is thrown away ([FSA chill and freeze](kiwix:govuk_resilience/www.gov.uk/government/publications/how-to-chill-freeze-and-defrost-food-safely)); food poisoning rises with the temperature ([Food poisoning (NHS)](kiwix:nhs_uk/www.nhs.uk/conditions/food-poisoning/)).
- **Power.** Demand for cooling and sagging lines bring outages in the heat ([NRR 2025, p. 141](doc:nrr-2025#page=141)); the [grid collapse playbook](playbook:grid-collapse) applies with the fridge as the priority.
- **Wildfire.** No barbecues or fires in the open, no glass left in grass; a fire in the heath or the field next to houses means leaving by the road away from the smoke, and the fire brigade — [[call 999]] ([Wildfire](kiwix:wikipedia_en_all_maxi/Wildfire); [NRR 2025, p. 127](doc:nrr-2025#page=127)); London lost houses to grass fires on 19 July 2022 ([2022 United Kingdom wildfires](kiwix:wikipedia_en_all_maxi/2022_United_Kingdom_wildfires)).
- **Water rationing.** Drinking, cooking, hand washing first; wash in a bowl and use it on the garden; flush with grey water ([Water module](module:water)). Do not drink from ponds, rivers or reservoirs: in a hot dry spell they carry blue-green algae ([Cyanobacteria](kiwix:wikipedia_en_all_maxi/Cyanobacteria)).
- **Air quality.** Ozone and particulates rise in hot still weather; asthma and COPD sufferers keep inhalers close and stay in at midday ([NRR 2025, p. 153](doc:nrr-2025#page=153); [Asthma (NHS)](kiwix:nhs_uk/www.nhs.uk/conditions/asthma/)).

{{module:water}}

{{module:shelter-heat}}

{{module:food}}

## First month

- **Drought.** A severe drought needs three consecutive dry winters; the register places it in south and east England with public supply restrictions, farm losses and a fire risk the fire service cannot fully fight for lack of water ([NRR 2025, p. 151](doc:nrr-2025#page=151)). Hosepipe bans come first ([Outdoor water-use restriction](kiwix:wikipedia_en_all_maxi/Outdoor_water-use_restriction)); the 1976 drought went as far as standpipes in streets ([1976 British Isles heatwave](kiwix:wikipedia_en_all_maxi/1976_British_Isles_heatwave); [Standpipe (street)](kiwix:wikipedia_en_all_maxi/Standpipe_(street))).
- **Supply failure.** The register's water scenario is the sudden loss of piped water or water "unfit for human consumption even after boiling" in one region, with alternative supplies prioritising the vulnerable ([NRR 2025, p. 120](doc:nrr-2025#page=120)). Water companies must supply bottled water and bowsers ([DWI consumers](kiwix:govuk_resilience/www.dwi.gov.uk/consumers/)).
- **Storing and harvesting.** Every water butt filled from every downpipe ([Rainwater harvesting](kiwix:wikipedia_en_all_maxi/Rainwater_harvesting); [Approved Document G](doc:ad-g)); rainwater is for the garden and the toilet unless treated ([Water disinfection](page:water-disinfection)). Cover butts against algae and mosquitoes. Legionella grows in warm stagnant water; run hoses and showers that have stood in the sun before using them ([Legionnaires' disease (NHS)](kiwix:nhs_uk/www.nhs.uk/conditions/legionnaires-disease/)).
- **Growing.** Mulch, water at the roots in the evening, shade seedlings, choose drought-tolerant crops; the gardening Q&A has the detail ([Growing food module](module:growing-food)). Goats need 5 to 10 litres a day, hens about 0.3; shade and water for every animal ([Livestock module](module:livestock)).
- **After the heat: flash floods.** Thunderstorms on baked ground flood roads and homes with 6 to 24 hours' warning ([NRR 2025, p. 149](doc:nrr-2025#page=149); [NRR 2025, p. 141](doc:nrr-2025#page=141)); the flood zones layer and the [storms and flooding playbook](playbook:storms-flooding).

{{module:growing-food}}

{{module:livestock}}

## Long term

Heatwaves are becoming more likely and mortality "increases significantly with increasing temperatures" ([NRR 2025, p. 141](doc:nrr-2025#page=141)); hotter summers, higher demand and a growing population make drought more likely ([NRR 2025, p. 151](doc:nrr-2025#page=151)). The lasting fixes are external shading, cross-ventilation and insulation designed against overheating ([Approved Document O](doc:ad-o)), rainwater and grey-water systems ([Greywater](kiwix:wikipedia_en_all_maxi/Greywater)), a garden planned for dry summers, and a street that checks on its older residents every hot day ([Community module](module:community)). Private supplies (wells and boreholes) are the owner's to test and treat ([DWI private supplies](kiwix:govuk_resilience/www.dwi.gov.uk/private-water-supplies/)).

{{module:community}}

## UK specifics

- **Alerts** come from UKHSA and the Met Office through the Weather-Health Alert system ([Weather-health alerting system](kiwix:govuk_resilience/www.gov.uk/guidance/weather-health-alerting-system); [AWHP, p. 22](doc:awhp-2026#page=22)); the government's heat pages are collected in one place ([Heat collection (GOV.UK)](kiwix:govuk_resilience/www.gov.uk/government/collections/heat)).
- **Restrictions** on water use are made under the Water Industry Act 1991 and drought orders ([Water Industry Act 1991](kiwix:legislation_uk/www.legislation.gov.uk/ukpga/1991/56/contents)); breaking a hosepipe ban is an offence.
- {{#if phones}}**Who to call:** your water company's number from the bill; the Environment Agency incident line 0800 80 70 60 for pollution and fish kills; [[call 999]] for wildfire and heatstroke ([UK numbers](page:uk-numbers)).{{else}}**Who to call:** nobody, until the lines are back: report a wildfire at the nearest fire station in person, take heatstroke to a hospital, and keep the numbers for later ([getting help without phones](page:no-phones); [UK numbers](page:uk-numbers)).{{/if}}
- **Reservoirs and water works** are on the map ([water overlay](map:?overlay=water)); the flood zones layer shows where the storm after the heat will go ([flood zones overlay](map:?overlay=flood-zones)).
- **Sunburn and skin:** cover up, factor 30, shade at midday; a burn that blisters is a burn ([Sunburn (NHS)](kiwix:nhs_uk/www.nhs.uk/conditions/sunburn/); [Burns card](card:burns)).

## Checklist

- [ ] Blinds shut by day on the sunny side; windows open at night; sleep low {#shade-and-ventilate}
- [ ] Two to three litres of water a person a day drunk; rehydration salts to hand {#drink-enough}
- [ ] Older neighbours and anyone alone checked twice a day in a red alert {#check-vulnerable}
- [ ] Fridge kept shut and full; chilled food above 8 °C for four hours thrown away {#fridge-discipline}
- [ ] Water butts filled and covered; grey water saved for the garden and the toilet {#butts-and-greywater}
- [ ] Stored drinking water for three days; bowser and bottled water station located {#drinking-water-stored}
- [ ] No fires or barbecues outdoors; wildfire escape route known {#no-open-fires}
- [ ] Inhalers and heart medicines within reach; midday indoors {#medicines-midday}
- [ ] Garden mulched; animals shaded and watered {#mulch-and-shade}
- [ ] Flood kit ready for the thunderstorm that follows {#flood-after-heat}

## Go deeper

- [Water module](module:water)
- [Heat stroke card](card:heat-stroke)
- [Dehydration card](card:dehydration)
- [Beat the heat (GOV.UK)](kiwix:govuk_resilience/www.gov.uk/guidance/beat-the-heat-hot-weather-advice)
- [Adverse Weather and Health Plan, heat](doc:awhp-2026#page=34)
- [2022 United Kingdom heatwaves (Wikipedia)](kiwix:wikipedia_en_all_maxi/2022_United_Kingdom_heatwaves)
- [Drought in the United Kingdom (Wikipedia)](kiwix:wikipedia_en_all_maxi/Drought_in_the_United_Kingdom)
- [Extreme heat (Ready.gov)](kiwix:www.ready.gov_en/www.ready.gov/heat)
- [Water Treatment Library](kiwix:zimgit-water_en/home)
- [Reservoirs and water works on the map](map:?overlay=water&overlay=health)
- [Famine playbook](playbook:famine)
- [Reading the weather and exposure](page:fieldcraft-weather)
- [Water outdoors](page:fieldcraft-water)
