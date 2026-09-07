---
id: grid-collapse
title: National grid collapse
icon: bolt
order: 4
summary: A nationwide or regional blackout lasting days to weeks. What stops, 105 and your network operator, water and sewage, rest centres, cash, and staying warm.
modules: [power, water, food, shelter-heat, comms, medical, sanitation, community, vehicles-fuel]
overlays: [fuel, health, water, rail]
reviewed: null
sources:
  - title: National Risk Register 2025
    doc: nrr-2025
    as_at: 2025-01-16
  - title: UK CMOs' public health advice during a national power outage
    kiwix: govuk_resilience/www.gov.uk/government/publications/public-health-advice-from-uk-cmos-during-a-national-power-outage
    as_at: 2025-12-16
  - title: Prepare, power cuts
    kiwix: prepare_uk/prepare.campaign.gov.uk/be-informed-about-hazards/power-cuts/
    as_at: 2026-09
  - title: Preparing for and responding to energy emergencies (GOV.UK)
    kiwix: govuk_resilience/www.gov.uk/guidance/preparing-for-and-responding-to-energy-emergencies
    as_at: 2026-09
  - title: Wales Resilience Framework 2025
    doc: wales-resilience-framework-2025
    as_at: 2025-05
  - title: Black start (Wikipedia)
    kiwix: wikipedia_en_all_maxi/Black_start
    as_at: 2026-02-15
  - title: Electricity meter (Wikipedia)
    kiwix: wikipedia_en_all_maxi/Electricity_meter
    as_at: 2026-02-15
  - title: Storm Arwen (Wikipedia)
    kiwix: wikipedia_en_all_maxi/Storm_Arwen
    as_at: 2026-02-15
---

## Right now

**Is it just you?** Check the trip switches in the consumer unit and look out of the window. If the street is dark, tell your network operator — [[call 105]] (Northern Ireland: NIE Networks 03457 643 643) ([UK numbers](page:uk-numbers)). If the phones are dead too, it is bigger than your street.

**In the first ten minutes:** torch, radio on, fridge and freezer doors shut, cooker and hob knobs off so nothing comes on unattended when power returns, {{#if water}}fill the kettle, pans and bath while the water still runs{{else}}and the water has gone too, so start on the stored bottles and the hot-water cylinder ([Water module](module:water)){{/if}} ([CMO outage advice](kiwix:govuk_resilience/www.gov.uk/government/publications/public-health-advice-from-uk-cmos-during-a-national-power-outage)). Unplug computers and the TV against the surge when it comes back ([Prepare, power cuts](kiwix:prepare_uk/prepare.campaign.gov.uk/be-informed-about-hazards/power-cuts/)).

**Anyone in a lift** presses the alarm and uses the lift phone if it has one; only a lift designated for emergency use has to carry a second power supply, so an ordinary one stops where it is ([Elevator](kiwix:wikipedia_en_all_maxi/Elevator)). Wait for the building's engineer or the fire brigade rather than forcing the doors — [[call 999]] if someone inside is ill.

**Never** run a generator, barbecue or camping stove indoors, in a garage or a conservatory ([Carbon monoxide card](card:carbon-monoxide)). Torches, not candles: the [power module](module:power) explains why, and covers your network operator, generators, batteries and the compensation claim.

**Assume days, not hours.** The register's worst case is a total failure in winter, all customers off without warning, taking mobile, internet, water, sewage, fuel and gas with it ([NRR 2025, p. 90](doc:nrr-2025#page=90)); the timescales are under UK specifics.

{{module:power}}

## First 72 hours

- **Water.** Mains water usually keeps flowing for hours to days on backup power, but not in high-rise flats when booster pumps stop; when it fails, sewage pumping fails with it ([CMO outage advice](kiwix:govuk_resilience/www.gov.uk/government/publications/public-health-advice-from-uk-cmos-during-a-national-power-outage)). Use stored water in the order drinking, cooking, washing, flushing; flush with a bucket ([Water module](module:water)).
- **Food.** A shut fridge keeps for about 4 hours, a full freezer 48 hours, half full 24; throw away chilled food that has been above 8 °C for over 4 hours ([FSA chill and freeze](kiwix:govuk_resilience/www.gov.uk/government/publications/how-to-chill-freeze-and-defrost-food-safely)). Eat the fridge first, then the freezer, then the store cupboard.
- **Heat and gas.** Gas boilers stop without electricity even when gas flows; gas hobs light with a match. One warm room, everyone in it, curtains shut at dusk ([Shelter and heat module](module:shelter-heat)). If the gas itself fails, turn every gas appliance off at its tap and wait for the network's instruction before relighting: homes take longer than industry to reconnect after a disconnection, for safety reasons, which is why they get priority for supply ([NRR 2025, p. 43](doc:nrr-2025#page=43)); smell gas — call 0800 111 999 ([UK numbers](page:uk-numbers)).
- **What has stopped** (Digital Voice landlines, most masts after about an hour, cash machines, pumps, lifts) and what still works is on [What still works](page:what-still-works); BBC local radio on FM carries the official picture, and the phone stays off between check-ins.
- **Medical equipment.** Anyone on oxygen, a stairlift, dialysis or refrigerated medicines should already be on the Priority Services Register ([UK numbers](page:uk-numbers)); if they are not, the operator needs telling. Insulin out of the fridge: keep it cool and dark and use the current pen ([Insulin (NHS)](kiwix:nhs_medicines/www.nhs.uk/medicines/insulin/)).
- **Cash.** Cash machines and card terminals are dead; shops that open take cash only ([NRR 2025, p. 102](doc:nrr-2025#page=102)).
- **Fuel.** Pumps need electricity; keep the tank above half and do not queue on rumours ([Vehicles and fuel module](module:vehicles-fuel)).

{{module:water}}

{{module:food}}

{{module:shelter-heat}}

{{module:comms}}

## First month

- **Rota disconnection.** If generation is short after the grid is rebuilt, or gas supply fails, the plan is rolling cuts of up to 3 hours at a time, spread across Great Britain with critical sites protected ([NRR 2025, p. 94](doc:nrr-2025#page=94)); every address has a load block letter, printed on some bills, that says when its turn comes ([Prepare, power cuts](kiwix:prepare_uk/prepare.campaign.gov.uk/be-informed-about-hazards/power-cuts/)), and the schedules are published by network area under the National Emergency Plan for Downstream Gas and Electricity ([Energy emergencies (GOV.UK)](kiwix:govuk_resilience/www.gov.uk/guidance/preparing-for-and-responding-to-energy-emergencies)).
- **Prepayment meters.** A prepayment or smart meter in prepay mode has a small emergency credit you switch on from the meter itself when the money runs out ([Electricity meter](kiwix:wikipedia_en_all_maxi/Electricity_meter)); with shops and top-up terminals down you cannot buy credit, so use it early in a long cut and tell the supplier as soon as the lines are back.
- **Rest centres and warm hubs.** Councils open them in halls and leisure centres; the village hall with a generator became the hub in Wales during Storm Darragh in December 2024 ([Wales Resilience Framework, p. 29](doc:wales-resilience-framework-2025#page=29)). Find yours through the parish or town council and the Local Resilience Forum ([Community module](module:community)).
- **Illness.** Cold homes, cold food and no lifts mean falls, chest infections and hypothermia in older people; check on them daily ([Hypothermia card](card:hypothermia)). Sanitation failure means diarrhoea; rehydration salts matter more than antibiotics ([Dehydration card](card:dehydration)).
- **Compensation.** Write down the time it went off and came back; the claim is described in the [power module](module:power).

{{module:medical}}

{{module:sanitation}}

## Long term

A grid does not simply switch back on; it is black-started. A battery starts a small diesel at a hydro or gas-turbine station, that station energises the lines to a large base-load plant, the base-load plant restarts the others, and only then is the distribution network re-energised, in steps, because switching everything on at once in a cold winter would collapse it again ([Black start](kiwix:wikipedia_en_all_maxi/Black_start)). Britain's operator keeps contracts with particular stations to do this, and in 2020 a Scottish wind farm black-started part of the grid ([Black start](kiwix:wikipedia_en_all_maxi/Black_start)). The register's order is: small pockets of intermittent supply within hours, a stable skeletal network within a few days, full restoration in up to 7 days, with rural areas likely to be reconnected before cities because their networks are simpler, and northern regions before southern because of where the generation is; critical services may take months ([NRR 2025, p. 91](doc:nrr-2025#page=91)). So the long-term shape for a household is intermittent power that arrives, goes, and arrives again, with priority to hospitals and water works rather than homes: the 1974 Three-Day Week rationed electricity for two months ([Three-Day Week](kiwix:wikipedia_en_all_maxi/Three-Day_Week)). Live to the rota, charge everything in every window of supply, and keep the one warm room until the operator says the network is stable ([Solar panels in a power cut](page:solar-islanding)).

{{module:community}}

{{module:vehicles-fuel}}

## UK specifics

- **Who to call.** 105 reaches whichever operator covers your postcode in Great Britain; the operator list, NIE Networks, ESB Networks and the Crown dependencies are on [UK numbers](page:uk-numbers), with the Priority Services Register.
- **Restoration timescales.** National: pockets in hours, a skeletal network in days, up to 7 days for full restoration, months for some critical services ([NRR 2025, p. 45](doc:nrr-2025#page=45)). Regional storms: 1 to 4 days, more than 5 in remote rural places ([NRR 2025, p. 139](doc:nrr-2025#page=139)); Storm Arwen in November 2021 left thousands of homes in the North East and Scotland without power for over a week ([Storm Arwen](kiwix:wikipedia_en_all_maxi/Storm_Arwen)) and Storm Éowyn in January 2025 cut power to about 240,000 customers in Northern Ireland and 106,000 in Scotland ([Storm Éowyn](kiwix:wikipedia_en_all_maxi/Storm_Éowyn)); the government's post-storm review is why operators now have to do better ([NRR 2025, p. 92](doc:nrr-2025#page=92)).
- **What the government asks of you now:** know your PSR eligibility, test smoke alarms monthly, write 105 and your numbers on paper, teach children 999, sign up for flood and weather warnings ([NRR 2025, p. 21](doc:nrr-2025#page=21)); a battery radio, torch and power bank ([Prepare, power cuts](kiwix:prepare_uk/prepare.campaign.gov.uk/be-informed-about-hazards/power-cuts/)). The government's baseline is three days of water and food; this box plans for 14 days at 3 litres a person a day, food for two weeks, and cash for two weeks of essentials in small notes ([Prepare](kiwix:prepare_uk/prepare.campaign.gov.uk/get-prepared-for-emergencies/)).
- **Emergency Alerts** work while any 4G or 5G mast is up, with no app and no data ([How alerts work](kiwix:govuk_resilience/www.gov.uk/alerts/how-alerts-work)).
- **Generators, back-feed and petrol** are covered in the [power module](module:power) and [vehicles and fuel](module:vehicles-fuel).

## Checklist

- [ ] {{#if phones}}Trip switches checked, then 105 called (GB) or NIE 03457 643 643 (NI); note what they say and when{{else}}Trip switches checked; the time the power went and how far the dark street runs written down, because nobody can be told until a phone works{{/if}} {#call-105 now}
- [ ] Torch out, radio on BBC local FM, phone brightness down, power bank found {#torch-radio-powerbank now}
- [ ] Kettle, pans, bottles and bath filled while the water still runs {#fill-water now}
- [ ] Fridge and freezer doors shut, and the time they lost power written on them {#fridge-freezer-shut now}
- [ ] Cooker and hob off at the knobs; computers and TV unplugged against the return surge {#appliances-off now}
- [ ] Generator, barbecue and stove outdoors only; CO alarm tested {#no-co-indoors now}
- [ ] {{#if phones}}Anyone medically dependent on power identified; PSR status checked; 105 told{{else}}Anyone medically dependent on power identified and checked on in person, hour by hour{{/if}} {#medical-dependents hour}
- [ ] Neighbours checked, especially older people living alone {#check-neighbours hour}
- [ ] Cash counted; card-free shopping list written; tank above half {#cash-and-fuel hour}
- [ ] One warm room chosen; curtains shut at dusk; everyone sleeps there {#one-warm-room today}
- [ ] Bucket-flush routine started and grey water saved once the mains stops {#bucket-flush today}
- [ ] Time off and time on written down for the compensation claim {#log-outage-times week}

## Go deeper

- [Power module](module:power)
- [What still works in an outage](page:what-still-works)
- [UK emergency numbers](page:uk-numbers)
- [Solar panels in a power cut](page:solar-islanding)
- [CMO advice during a national power outage](kiwix:govuk_resilience/www.gov.uk/government/publications/public-health-advice-from-uk-cmos-during-a-national-power-outage)
- [NRR 2025, failure of the transmission system](doc:nrr-2025#page=90)
- [Black start (Wikipedia)](kiwix:wikipedia_en_all_maxi/Black_start)
- [Rolling blackout (Wikipedia)](kiwix:wikipedia_en_all_maxi/Rolling_blackout)
- [National Grid (Great Britain) (Wikipedia)](kiwix:wikipedia_en_all_maxi/National_Grid_(Great_Britain))
- [Power outages (Ready.gov)](kiwix:www.ready.gov_en/www.ready.gov/power-outages)
- [Fuel, hospitals and water works on the map](map:?overlay=fuel&overlay=health&overlay=water)
- [Storms and flooding playbook](playbook:storms-flooding)
- [Severe winter playbook](playbook:severe-winter)
- [Field Hygiene and Sanitation, FM 21-10](doc:fm-21-10-field-hygiene)
- [Canadian Prepper: winter prepping](kiwix:canadian-prepper_en_winterprepping/index.html)
- [Water outdoors](page:fieldcraft-water)
- [Living in the field: hygiene](page:fieldcraft-hygiene)
- [Getting help without phones](page:no-phones)
