---
id: supply-chain
title: Supply chain collapse
icon: truck
order: 11
summary: Fuel, food and medicine stop arriving. Panic buying, empty forecourts, pharmacy shortages, and the store, garden and neighbours that carry you through.
modules: [food, vehicles-fuel, medical, growing-food, community, water, tools-repair]
overlays: [fuel, health, rail]
reviewed: null
sources:
  - title: National Risk Register 2025
    doc: nrr-2025
    as_at: 2025-01-16
  - title: 2021 United Kingdom fuel supply crisis (Wikipedia)
    kiwix: wikipedia_en_all_maxi/2021_United_Kingdom_fuel_supply_crisis
    as_at: 2026-02-15
  - title: Fuel protests in the United Kingdom (Wikipedia)
    kiwix: wikipedia_en_all_maxi/Fuel_protests_in_the_United_Kingdom
    as_at: 2026-02-15
  - title: Prepare, get prepared for emergencies
    kiwix: prepare_uk/prepare.campaign.gov.uk/get-prepared-for-emergencies/
    as_at: 2026-09
  - title: How to chill, freeze and defrost food safely (FSA)
    kiwix: govuk_resilience/www.gov.uk/government/publications/how-to-chill-freeze-and-defrost-food-safely
    as_at: 2026-09
  - title: Agriculture in the United Kingdom (Wikipedia)
    kiwix: wikipedia_en_all_maxi/Agriculture_in_the_United_Kingdom
    as_at: 2026-02-15
  - title: WHO Model List of Essential Medicines 2025
    doc: who-eml-2025
    as_at: 2025-09
  - title: USDA Complete Guide to Home Canning
    kiwix: usda-2015_en/home
    as_at: 2025-04-11
---

## Right now

**Do not join the queue.** The September 2021 fuel crisis was a shortage of lorry drivers turned into empty forecourts by panic buying within two days ([2021 United Kingdom fuel supply crisis](kiwix:wikipedia_en_all_maxi/2021_United_Kingdom_fuel_supply_crisis)); the September 2000 refinery blockades had supermarkets warning of empty shelves within days ([Fuel protests in the United Kingdom](kiwix:wikipedia_en_all_maxi/Fuel_protests_in_the_United_Kingdom)). If your tank is above half and your cupboard holds two weeks, you have already done the useful thing ([Prepare](kiwix:prepare_uk/prepare.campaign.gov.uk/get-prepared-for-emergencies/)).

**Take stock tonight:** food by days, medicines by days, fuel by miles, cash for two weeks of essentials in small notes, nappies, formula, pet food, gas bottles, wood. {{#if shops}}Write it on the fridge and buy only the gaps, in ordinary quantities, from ordinary shops{{else}}Write it on the fridge; with the shops shut there is nothing to buy, so the list becomes the ration{{/if}} ([Food module](module:food)). A baby on formula is the household's tightest supply line: the fallback when the tin runs out is on [Infant feeding](page:infant-feeding).

**Medicines first.** {{#if phones}}Order repeat prescriptions early, ask the pharmacist about alternatives now rather than when the shelf is empty, and keep two weeks in hand ([Medical module](module:medical)).{{else}}With the surgery's line and its app both down, take the repeat slip or the labelled box to the pharmacy counter in person, ask about alternatives while you are there, and keep two weeks in hand ([Medical module](module:medical)).{{/if}}

{{module:food}}

## First 72 hours

- **Fuel.** The register's fuel scenarios are regional: a refinery or terminal lost, replenishment taking "several days", the National Emergency Plan for Fuel and Operation ESCALIN's military tanker drivers keeping priority users supplied ([NRR 2025, p. 49](doc:nrr-2025#page=49); [NRR 2025, p. 69](doc:nrr-2025#page=69)). Store petrol only within the household limit and outside the house (see [vehicles and fuel](module:vehicles-fuel)); cycle, walk, share cars.
- **Food.** The UK produces about 60% of the food it eats and runs its shops on daily deliveries ([Agriculture in the United Kingdom](kiwix:wikipedia_en_all_maxi/Agriculture_in_the_United_Kingdom); [Lean manufacturing](kiwix:wikipedia_en_all_maxi/Lean_manufacturing)); fresh produce goes first, then bread and milk, then tins. Cook the fridge and freezer contents first if power is also uncertain ([FSA chill and freeze](kiwix:govuk_resilience/www.gov.uk/government/publications/how-to-chill-freeze-and-defrost-food-safely)).
- **Water** is usually the last thing to stop, but bottled water vanishes with the first rumour; {{#if water}}fill containers from the tap now{{else}}the tap has stopped too, so ration the store and treat whatever you gather{{/if}} ([Water module](module:water)).
- **Gas bottles, heating oil, wood:** heating oil deliveries fail in the same scenarios as diesel ([NRR 2025, p. 69](doc:nrr-2025#page=69)); order early, share deliveries with neighbours.
- **Queues make shortages.** A lorry-driver shortfall becomes an empty forecourt only when everyone fills up at once; buying in ordinary amounts is what keeps the system delivering ([Panic buying](kiwix:wikipedia_en_all_maxi/Panic_buying)).
- **Money.** Cash, card outages, bank failure and the deposit guarantee are the [economic collapse playbook](playbook:economic-collapse); this one is about the lorries.

{{module:vehicles-fuel}}

{{module:water}}

## First month

- **Cook from staples.** Rice, pasta, oats, lentils, flour, oil, tinned tomatoes, tinned fish and UHT milk make months of meals; the recipe collections in this box need no fresh ingredients ([Seasoned Advice, cooking Q&A](kiwix:cooking.stackexchange.com_en_all/questions); [Food Preparation Library](kiwix:zimgit-food-preparation_en/home)). Bulk grain and flour, how to keep them and how much a person eats: [Food storage](page:food-storage).
- **Preserve what appears.** A glut of anything is dried, pickled, jammed or canned; the pressure-canning rule for low-acid food is in the [food module](module:food) above ([USDA canning](kiwix:usda-2015_en/home)).
- **Medicines.** The WHO essential list is what a pharmacy should hold when the wholesalers fail; it is the list to ask about ([WHO EML, p. 12](doc:who-eml-2025#page=12)). Insulin, inhalers, thyroid and heart drugs are the ones to worry about first ([Insulin (NHS)](kiwix:nhs_medicines/www.nhs.uk/medicines/insulin/); [Salbutamol inhaler (NHS)](kiwix:nhs_medicines/www.nhs.uk/medicines/salbutamol-inhaler/)). Keeping insulin usable without a fridge, and what to do when a long-term condition's supply runs short, is on [Chronic conditions](page:chronic-conditions).
- **Grow.** Sow what the month allows ([Growing food module](module:growing-food)): nothing tender outdoors before mid-May, hardy crops and under-cover sowing in every other month; a bed sown now is a bag not bought later.
- **Fix rather than replace.** Spares stop arriving before food does; the repair guides and the tool kit are the supply chain you control ([Tools and repair module](module:tools-repair); [iFixit](kiwix:ifixit_en_all/home/home)).
- **Community.** A village bulk order, a shared freezer run on one generator, a lift rota: the [community module](module:community) has the template.

{{module:medical}}

{{module:growing-food}}

{{module:tools-repair}}

## Long term

Global supply chains failed for two years after 2020 and the container ship stuck in the Suez Canal in March 2021 held up a tenth of world trade for a week ([2021–2023 global supply chain crisis](kiwix:wikipedia_en_all_maxi/2021–2023_global_supply_chain_crisis); [2021 Suez Canal obstruction](kiwix:wikipedia_en_all_maxi/2021_Suez_Canal_obstruction)). Just-in-time stocking means shops hold days, not weeks ([Lean manufacturing](kiwix:wikipedia_en_all_maxi/Lean_manufacturing)).

**What fails in what order.** Air freight and imported fresh produce go first, then anything trucked daily (bread, milk, fuel, pharmacy wholesale), then tinned and dried goods as depots empty, then spares and parts, which nobody stocks at all; power and water are the last to go because they are supplied under emergency plans with priority fuel ([NRR 2025, p. 49](doc:nrr-2025#page=49); [NRR 2025, p. 69](doc:nrr-2025#page=69)). The register's answer for fuel is priority-user schemes and military drivers, not deliveries to households, so a long failure means the household supplies itself.

**A year without deliveries** is run on three lines: a rotated store that is always two weeks deep and refilled whenever anything is on the shelf ([Food module](module:food); [Food storage](page:food-storage)); food from close by, which means the garden, an allotment, a local farm that sells at the gate, and hens or rabbits on scraps ([Growing food module](module:growing-food); [Livestock module](module:livestock)); and repair, because the washing machine, the bicycle and the boiler will not be replaced ([Tools and repair module](module:tools-repair)). A village that pools a bulk order, a delivery slot and a lift rota gets more through the gap than any household alone ([Community module](module:community)). If the state rations, the wartime system is the model, and the money side of a long shortage is the [economic collapse playbook](playbook:economic-collapse); if the harvest itself fails, the [famine playbook](playbook:famine) is the next chapter ([Rationing in the United Kingdom](kiwix:wikipedia_en_all_maxi/Rationing_in_the_United_Kingdom)).

{{module:community}}

## UK specifics

- **Fuel plans.** The National Emergency Plan for Fuel, priority-user schemes and Operation ESCALIN ([NRR 2025, p. 49](doc:nrr-2025#page=49)); the Energy Act 1976 powers over production and supply in a real shortage ([NRR 2025, p. 63](doc:nrr-2025#page=63)); the UK's emergency oil stocks released with other International Energy Agency members ([NRR 2025, p. 63](doc:nrr-2025#page=63)).
- **Gas** comes by pipeline from Norway and as LNG; the UK does not use Russian gas but pays European prices, and the heating season is October to May ([NRR 2025, p. 62](doc:nrr-2025#page=62)).
- **Fuel at home:** the petrol limits and the notification rule are in [vehicles and fuel](module:vehicles-fuel); diesel and heating oil are outside them.
- **Food safety** when shops and fridges fail: the FSA rules on chilling and the 8 °C limit ([FSA chill and freeze](kiwix:govuk_resilience/www.gov.uk/government/publications/how-to-chill-freeze-and-defrost-food-safely)); foraging is lawful for your own use ([Foraging law](page:foraging-law)).
- **Routes to medicines:** Pharmacy First in England, the GP's repeat system, and NHS advice — [[call 111]]. Hoarding prescription drugs is not one of them ([UK numbers](page:uk-numbers)).
- **Where the fuel is:** every forecourt is on the map ([fuel overlay](map:?overlay=fuel)); stations near motorway junctions and depots are resupplied first.

## Checklist

- [ ] Stock count on the fridge door: food, medicines, fuel, cash, nappies, pet food, gas {#stock-count}
- [ ] Repeat prescriptions ordered early; alternatives discussed with the pharmacist {#prescriptions-early}
- [ ] Tank above half; any stored petrol within the lawful limit and outside the house {#fuel-half-tank}
- [ ] Two weeks of staples built up over several ordinary shops, not one trolley {#two-weeks-staples}
- [ ] Water containers filled and stored in the dark {#water-filled}
- [ ] Bicycle serviced; car-share and lift rota agreed with neighbours {#bike-and-lifts}
- [ ] Freezer contents cooked or preserved first; USDA rules for low-acid canning {#preserve-first}
- [ ] Seeds, seed potatoes and a bed ready; sowing calendar checked {#sow-something}
- [ ] Village bulk order or shared delivery organised {#bulk-order}
- [ ] Spares for the things that break: fuses, tape, wire, filters, tyre patches {#spares}
- [ ] Formula fallback read; insulin-without-a-fridge plan agreed with the pharmacist {#infant-and-insulin}

## Go deeper

- [Food module](module:food)
- [Vehicles and fuel module](module:vehicles-fuel)
- [Growing food module](module:growing-food)
- [Food storage: bulk grain, milling and what 2,000 kcal looks like](page:food-storage)
- [Infant feeding when formula runs out](page:infant-feeding)
- [Chronic conditions without the pharmacy](page:chronic-conditions)
- [2021 United Kingdom fuel supply crisis (Wikipedia)](kiwix:wikipedia_en_all_maxi/2021_United_Kingdom_fuel_supply_crisis)
- [Food security (Wikipedia)](kiwix:wikipedia_en_all_maxi/Food_security)
- [Stockpile (Wikipedia)](kiwix:wikipedia_en_all_maxi/Stockpile)
- [Food Preparation Library](kiwix:zimgit-food-preparation_en/home)
- [USDA canning guide](kiwix:usda-2015_en/home)
- [Bicycles Q&A](kiwix:bicycles.stackexchange.com_en_all/questions)
- [Fuel stations and stations on the map](map:?overlay=fuel&overlay=rail)
- [Economic collapse playbook](playbook:economic-collapse)
- [Famine playbook](playbook:famine)
- [Canadian Prepper: prepping food](kiwix:canadian-prepper_en_preppingfood/index.html)
- [GrimGrains: cooking from stores](kiwix:grimgrains_en_all/grimgrains.com/)
