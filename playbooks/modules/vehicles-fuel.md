---
id: vehicles-fuel
title: Vehicles and fuel
icon: car
order: 14
summary: Storing fuel lawfully, keeping vehicles useful without pumps or power, floods and winter, and what electric cars can do for a house.
sources:
  - title: Petroleum (Consolidation) Regulations 2014
    kiwix: legislation_uk/www.legislation.gov.uk/uksi/2014/1637/contents
    as_at: 2026-09-06
  - title: HSE INDG370 Controlling fire and explosion risks
    doc: hse-indg370
    as_at: 2026-09
  - title: 2021 United Kingdom fuel supply crisis (Wikipedia)
    kiwix: wikipedia_en_all_maxi/2021_United_Kingdom_fuel_supply_crisis
    as_at: 2026-02-15
  - title: Help during a flood (GOV.UK)
    kiwix: govuk_resilience/www.gov.uk/help-during-flood
    as_at: 2026-09-05
  - title: Flash flooding (GOV.UK)
    kiwix: govuk_resilience/www.gov.uk/guidance/flash-flooding
    url: https://www.gov.uk/guidance/flash-flooding
    as_at: 2026-09
  - title: Motor Vehicle Maintenance and Repair Q&A
    kiwix: mechanics.stackexchange.com_en_all/questions
    as_at: 2026-08-04
  - title: National Risk Register 2025
    doc: nrr-2025
    as_at: 2025-01-16
  - title: Vehicle-to-grid (Wikipedia)
    kiwix: wikipedia_en_all_maxi/Vehicle-to-grid
    as_at: 2026-02-15
---

## Key facts

- Petrol kept for a generator counts against the same household limit, and a generator is run outdoors only, at least 6 metres from doors and windows, never indoors, in a garage or near an opening, because the exhaust is carbon monoxide ([Power module](module:power)).
- The Petroleum (Consolidation) Regulations 2014 let a household keep up to 30 litres of petrol without telling anyone: in plastic containers of up to 10 litres each, metal containers of up to 20 litres, or a demountable tank of up to 30 litres; diesel is not covered by these limits ([Petroleum Regulations](kiwix:legislation_uk/www.legislation.gov.uk/uksi/2014/1637/contents)).
- Fuel pumps need mains electricity to work, as the September 2021 fuel crisis showed when panic buying, not a shortage of fuel itself, emptied forecourts ([2021 UK fuel supply crisis](kiwix:wikipedia_en_all_maxi/2021_United_Kingdom_fuel_supply_crisis)).
- Petrol goes off after about six months (E10 sooner), diesel keeps for a year or more but grows "diesel bug" if it holds water; {{#if power}}keep every tank above half so you always have a reserve.{{else}}the pumps have no power, so what is in the tank is all there is: save it for the journey that matters.{{/if}}

## What to do

1. Store fuel outside the house, in a ventilated place away from any source of ignition ([HSE INDG370, p. 1](doc:hse-indg370#page=1)).
2. Never drive through floodwater: as little as 30 cm of moving water will float a car, and around 60 cm will carry away a vehicle of any size ([flash flooding](kiwix:govuk_resilience/www.gov.uk/guidance/flash-flooding)).
3. Pack a winter kit for the car: blanket, shovel, grit, torch, food, water, a charger and snow socks.
4. Keep a bicycle or hand cart as a fallback when fuel or a working car are not available ([bicycles Q&A](kiwix:bicycles.stackexchange.com_en_all/questions)).
5. Diagnose faults yourself where you can before assuming a garage visit is possible ([motor vehicle Q&A](kiwix:mechanics.stackexchange.com_en_all/questions)).

{{#unless power}}
**Every pump on the forecourt is dead, and so is every card terminal** ([Power module](module:power)). What is in the tank is all there is until the grid comes back: keep it for the journey that matters, park facing out so that you never manoeuvre in the dark, and lock the fuel cap. An electric car cannot be charged at all now, so treat its battery as a store to be spent on the house rather than on driving, using vehicle-to-load if the car has it ([vehicle-to-grid](kiwix:wikipedia_en_all_maxi/Vehicle-to-grid)).
{{/unless}}

{{#unless shops}}
**Nothing to buy means nothing to replace.** No fuel, no parts, no tyres and no garage, so treat the vehicle as a consumable: decide which journeys are worth the fuel and combine the rest. Service what you own while you still can, with oil, filters, coolant, tyre pressures, a spare bulb and a spare belt, and diagnose faults yourself before assuming a garage ([motor vehicle Q&A](kiwix:mechanics.stackexchange.com_en_all/questions)). Keep the bicycle roadworthy, with a pump, a spare tube and a patch kit ([bicycles Q&A](kiwix:bicycles.stackexchange.com_en_all/questions)). Siphoning from someone else's vehicle is theft, whatever the circumstances.
{{/unless}}

{{#unless roads}}
**Do not drive.** Closed, blocked, flooded or drifted roads strand cars exactly where nobody can reach them, and as little as 30 cm of moving water floats one, with around 60 cm enough to carry away a vehicle of any size ([flash flooding](kiwix:govuk_resilience/www.gov.uk/guidance/flash-flooding)). A bicycle, a hand cart or a wheelbarrow will move what matters. If you are already out when the road closes, park clear of the carriageway, leave a note on the dashboard with your name and where you have gone, take documents, keys, medicines and warm clothing, and walk out by the shortest safe route ([Navigation module](module:navigation)).
{{/unless}}

{{#if scenario:supply-chain}}
**Do not join the queue.** The September 2021 crisis was a shortage of lorry drivers turned into empty forecourts by panic buying within two days ([2021 UK fuel supply crisis](kiwix:wikipedia_en_all_maxi/2021_United_Kingdom_fuel_supply_crisis)). Keep the tank above half as a habit rather than filling in the rush, buy in ordinary amounts, and share journeys instead of each household taking a car. Order heating oil and gas bottles early and jointly with neighbours, because those deliveries fail in the same conditions as diesel ([NRR 2025, p. 69](doc:nrr-2025#page=69)); store petrol outside the house and only within the household limit: up to 30 litres with no notification, in containers no bigger than 10 litres plastic or 20 litres metal, marked PETROL ([Petroleum Regulations 2014](kiwix:legislation_uk/www.legislation.gov.uk/uksi/2014/1637/contents)).
{{/if}}

## UK specifics

- Between 30 and 275 litres of petrol stored at home, you must notify the Petroleum Enforcement Authority in writing ([Petroleum Regulations](kiwix:legislation_uk/www.legislation.gov.uk/uksi/2014/1637/contents)).
- Siphoning fuel from someone else's vehicle or tank is theft, whatever the circumstances.
- An electric car with vehicle-to-load can run a fridge and lights for days from its battery, typically up to 3.6 kW, but it cannot be recharged at all without a working grid connection ([vehicle-to-grid](kiwix:wikipedia_en_all_maxi/Vehicle-to-grid)).

## Go deeper

- [Power module](module:power)
- [Evacuation module](module:evacuation)
- [Motor Vehicle Maintenance and Repair Q&A](kiwix:mechanics.stackexchange.com_en_all/questions)
- [Bicycles Q&A](kiwix:bicycles.stackexchange.com_en_all/questions)
- [Jerrycan (Wikipedia)](kiwix:wikipedia_en_all_maxi/Jerrycan)
- [Fuel stations on the map](map:?overlay=fuel)
