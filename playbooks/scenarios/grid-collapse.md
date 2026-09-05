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
  - title: Prepare, be informed about hazards
    kiwix: prepare_uk/prepare.campaign.gov.uk/be-informed-about-hazards/
    as_at: 2026-09
  - title: Priority Services Register
    kiwix: govuk_resilience/www.thepsr.co.uk/
    as_at: 2026-09
  - title: Preparing for and responding to energy emergencies (GOV.UK)
    kiwix: govuk_resilience/www.gov.uk/guidance/preparing-for-and-responding-to-energy-emergencies
    as_at: 2026-09
  - title: Wales Resilience Framework 2025
    doc: wales-resilience-framework-2025
    as_at: 2025-05
  - title: 2025 Iberian Peninsula blackout (Wikipedia)
    kiwix: wikipedia_en_all_maxi/2025_Iberian_Peninsula_blackout
    as_at: 2026-02-15
  - title: Storm Arwen (Wikipedia)
    kiwix: wikipedia_en_all_maxi/Storm_Arwen
    as_at: 2026-02-15
---

## Right now

**Is it just you?** Check the trip switches in the consumer unit and look out of the window. If the street is dark, call **105** (free, any phone, Great Britain) to reach your electricity network operator and hear what they know; Northern Ireland uses NIE Networks on 03457 643 643 ([UK numbers](page:uk-numbers); [NRR 2025, p. 21](doc:nrr-2025#page=21)). If phones are dead too, it is bigger than your street.

**Assume it will last.** The register's reasonable worst case is a total failure of the National Electricity Transmission System, all customers off "instantaneously and without warning", in winter, taking down mobile and internet, water, sewage, fuel and gas with it ([NRR 2025, p. 90](doc:nrr-2025#page=90)). Restoration comes in pockets within hours, a "skeletal network" within a few days, full restoration in up to 7 days, and critical services possibly months ([NRR 2025, p. 45](doc:nrr-2025#page=45)). A regional storm outage can run for weeks in remote areas ([NRR 2025, p. 139](doc:nrr-2025#page=139)).

**In the first ten minutes:** torch, radio on, fridge and freezer doors shut, cooker and hob knobs off so nothing comes on unattended when power returns, fill the kettle, pans and bath while the water still runs ([CMO outage advice](kiwix:govuk_resilience/www.gov.uk/government/publications/public-health-advice-from-uk-cmos-during-a-national-power-outage)). Unplug computers and the TV against the surge when it comes back.

**Never** run a generator, barbecue or camping stove indoors, in a garage or a conservatory ([Carbon monoxide card](card:carbon-monoxide)).

{{module:power}}

## First 72 hours

- **Water.** Mains water usually keeps flowing for hours to days on backup power, but not in high-rise flats when booster pumps stop; when it fails, sewage pumping fails with it ([CMO outage advice](kiwix:govuk_resilience/www.gov.uk/government/publications/public-health-advice-from-uk-cmos-during-a-national-power-outage)). Use stored water in the order drinking, cooking, washing, flushing; flush with a bucket ([Water module](module:water)).
- **Food.** A shut fridge keeps for about 4 hours, a full freezer 48 hours, half full 24; throw away chilled food that has been above 8 °C for over 4 hours ([FSA chill and freeze](kiwix:govuk_resilience/www.gov.uk/government/publications/how-to-chill-freeze-and-defrost-food-safely)). Eat the fridge first, then the freezer, then the store cupboard.
- **Heat.** Gas boilers stop without electricity even when gas flows; gas hobs light with a match. One warm room, everyone in it, curtains shut at dusk ([Shelter and heat module](module:shelter-heat)).
- **Phones and radio.** Digital Voice landlines die unless you have a battery unit; masts mostly last about an hour; texts get through when calls do not; 999 uses any network ([What still works](page:what-still-works)). BBC local radio on FM carries the official picture; keep the phone off between check-ins.
- **Medical equipment.** Anyone on oxygen, a stairlift, dialysis or refrigerated medicines should already be on the Priority Services Register, which is one registration for water, electricity and gas ([Priority Services Register](kiwix:govuk_resilience/www.thepsr.co.uk/)); if they are not, call 105 and say so. Insulin out of the fridge: keep it cool and dark and use the current pen ([Insulin (NHS)](kiwix:nhs_medicines/www.nhs.uk/medicines/insulin/)).
- **Cash.** Cash machines and card terminals are dead; shops that open take cash only ([NRR 2025, p. 102](doc:nrr-2025#page=102)).
- **Fuel.** Pumps need electricity; keep the tank above half and do not queue on rumours ([Vehicles and fuel module](module:vehicles-fuel)).

{{module:water}}

{{module:food}}

{{module:shelter-heat}}

{{module:comms}}

## First month

- **Rota disconnection.** If generation is short after the grid is rebuilt, or gas supply fails, the plan is rolling cuts of up to 3 hours at a time, spread across Great Britain with critical sites protected ([NRR 2025, p. 94](doc:nrr-2025#page=94)); the schedules are published by network area under the National Emergency Plan for Downstream Gas and Electricity ([Energy emergencies (GOV.UK)](kiwix:govuk_resilience/www.gov.uk/guidance/preparing-for-and-responding-to-energy-emergencies)).
- **Rest centres and warm hubs.** Councils open them in halls and leisure centres; the village hall with a generator became the hub in Wales during Storm Darragh in December 2024 ([Wales Resilience Framework, p. 29](doc:wales-resilience-framework-2025#page=29)). Find yours through the parish or town council and the Local Resilience Forum ([Community module](module:community)).
- **Illness.** Cold homes, cold food and no lifts mean falls, chest infections and hypothermia in older people; check on them daily ([Hypothermia card](card:hypothermia)). Sanitation failure means diarrhoea; rehydration salts matter more than antibiotics ([Dehydration card](card:dehydration)).
- **Compensation** under Ofgem's guaranteed standards is claimed from the network operator once power is back; keep a note of when it went off and on ([Power module](module:power)).

{{module:medical}}

{{module:sanitation}}

## Long term

A grid does not simply switch back on: it is rebuilt by black start, islands of generation synchronised one by one ([Black start](kiwix:wikipedia_en_all_maxi/Black_start)). Spain and Portugal lost their whole grid on 28 April 2025 and had most of it back within about ten hours ([2025 Iberian Peninsula blackout](kiwix:wikipedia_en_all_maxi/2025_Iberian_Peninsula_blackout)); Britain's 1974 Three-Day Week rationed electricity to industry for two months ([Three-Day Week](kiwix:wikipedia_en_all_maxi/Three-Day_Week)). If damage is physical (storm, attack, solar storm) the wait is for transformers that take months to build; plan the house for intermittent power: a battery, LED lights, a way to cook, a way to keep one room warm ([Solar panels in a power cut](page:solar-islanding)).

{{module:community}}

{{module:vehicles-fuel}}

## UK specifics

- **105 and the network operators.** Great Britain: UK Power Networks (London, South East, East), National Grid Electricity Distribution (Midlands, South West, South Wales), SP Energy Networks (central and southern Scotland, Merseyside, Cheshire, North Wales), SSEN (north of Scotland, central southern England), Northern Powergrid (North East, Yorkshire), Electricity North West; all through 105. NIE Networks 03457 643 643; ESB Networks 1800 372 999; Manx Utilities, Jersey Electricity and Guernsey Electricity by the number on the bill ([UK numbers](page:uk-numbers)).
- **Priority Services Register:** free; for medical dependence on power, disability, age, a child under five, or needing information in another format; it gets you proactive calls, bottled water and, in long outages, welfare visits ([Priority Services Register](kiwix:govuk_resilience/www.thepsr.co.uk/)).
- **Restoration timescales.** National: up to 7 days for full restoration, months for some critical services ([NRR 2025, p. 45](doc:nrr-2025#page=45)). Regional storms: 1 to 4 days, more than 5 in remote rural places ([NRR 2025, p. 139](doc:nrr-2025#page=139)); Storm Arwen in November 2021 left thousands of homes in the North East and Scotland without power for over a week ([Storm Arwen](kiwix:wikipedia_en_all_maxi/Storm_Arwen)) and Storm Éowyn in January 2025 cut power to hundreds of thousands in Northern Ireland and Scotland for days ([Storm Éowyn](kiwix:wikipedia_en_all_maxi/Storm_Éowyn)); the government's post-storm review is why operators now have to do better ([NRR 2025, p. 92](doc:nrr-2025#page=92)).
- **What the government asks of you now:** know your PSR eligibility, test smoke alarms monthly, write 105 and your numbers on paper, teach children 999, sign up for flood and weather warnings ([NRR 2025, p. 21](doc:nrr-2025#page=21)); a battery radio, torch, power bank and three days of water and food ([Prepare, hazards](kiwix:prepare_uk/prepare.campaign.gov.uk/be-informed-about-hazards/)).
- **Emergency Alerts** work while any 4G or 5G mast is up, with no app and no data ([How alerts work](kiwix:govuk_resilience/www.gov.uk/alerts/how-alerts-work)).
- **Generators** must be outdoors, 6 metres from doors and windows, never back-fed into house wiring except through a transfer switch fitted by an electrician ([Approved Document P, p. 7](doc:ad-p#page=7)); petrol at home is limited to 30 litres ([Petroleum regulations 2014](kiwix:legislation_uk/www.legislation.gov.uk/uksi/2014/1637/contents)).

## Checklist

- [ ] Call 105 (GB) or NIE 03457 643 643 (NI); note what they say and when {#call-105}
- [ ] Torch, radio on BBC local FM, phone brightness down, power bank found {#torch-radio-powerbank}
- [ ] Cooker and hob off at the knobs; computers and TV unplugged against the return surge {#appliances-off}
- [ ] Kettle, pans, bottles and bath filled while the water still runs {#fill-water}
- [ ] Fridge and freezer doors shut; note the time they lost power {#fridge-freezer-shut}
- [ ] One warm room chosen; curtains shut at dusk; everyone sleeps there {#one-warm-room}
- [ ] Anyone medically dependent on power identified; PSR status checked; 105 told {#medical-dependents}
- [ ] Generator, barbecue and stove outdoors only; CO alarm working {#no-co-indoors}
- [ ] Cash counted; card-free shopping list; tank above half {#cash-and-fuel}
- [ ] Neighbours checked, especially older people living alone {#check-neighbours}
- [ ] Bucket-flush routine and grey water saved once the mains stops {#bucket-flush}
- [ ] Time off and time on written down for the compensation claim {#log-outage-times}

## Go deeper

- [Power module](module:power)
- [What still works in an outage](page:what-still-works)
- [UK emergency numbers](page:uk-numbers)
- [Solar panels in a power cut](page:solar-islanding)
- [CMO advice during a national power outage](kiwix:govuk_resilience/www.gov.uk/government/publications/public-health-advice-from-uk-cmos-during-a-national-power-outage)
- [NRR 2025, failure of the transmission system](doc:nrr-2025#page=90)
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
