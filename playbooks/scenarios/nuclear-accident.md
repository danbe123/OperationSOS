---
id: nuclear-accident
title: Nuclear accident or dirty bomb
icon: atom
order: 2
summary: A radiation release from a UK or nearby site, a lost source, or a dirty bomb. Go in, stay in, tune in; iodine only when told.
modules: [radiation, evacuation, water, food, medical, comms, livestock]
overlays: [nuclear-sites, health, water]
reviewed: null
sources:
  - title: National Risk Register 2025
    doc: nrr-2025
    as_at: 2025-01-16
  - title: Radiation emergencies, information for the public (UKHSA)
    kiwix: govuk_resilience/www.gov.uk/government/publications/radiation-emergencies-information-for-the-public
    as_at: 2026-09
  - title: Nuclear emergencies, information for the public (UKHSA)
    kiwix: govuk_resilience/www.gov.uk/government/publications/nuclear-emergencies-information-for-the-public
    as_at: 2026-09
  - title: Stable iodine prophylaxis (NRPB 2001)
    doc: nrpb-stable-iodine
    as_at: 2001-01
  - title: Removing radioactive material from your skin and clothes (UKHSA)
    doc: ukhsa-radiation-decontamination
    as_at: 2023-11-28
  - title: REPPIR 2019
    kiwix: legislation_uk/www.legislation.gov.uk/uksi/2019/703/contents
    as_at: 2026-09
  - title: Chernobyl disaster (Wikipedia)
    kiwix: wikipedia_en_all_maxi/Chernobyl_disaster
    as_at: 2026-02-15
  - title: Windscale fire (Wikipedia)
    kiwix: wikipedia_en_all_maxi/Windscale_fire
    as_at: 2026-02-15
---

## Right now

**Go in, stay in, tune in.** Get indoors, shut doors and windows, turn off fans, extractor fans and the boiler flue's air supply if you can, and listen to the radio or wait for the Emergency Alert ([UKHSA radiation emergencies](kiwix:govuk_resilience/www.gov.uk/government/publications/radiation-emergencies-information-for-the-public)). This is the government's standing instruction for any release ([NRR 2025, p. 22](doc:nrr-2025#page=22)).

**If you were outside in the plume or near an explosion:** outer clothing off at the door into a bag, then {{#if water}}shower or wash with soap and warm water, hair too, no conditioner and no scrubbing{{else}}wash with soap and stored water, hair too, no conditioner and no scrubbing, because water that was in pipes and covered tanks before the release is still clean{{/if}}; this removes most contamination ([UKHSA decontamination sheet, p. 1](doc:ukhsa-radiation-decontamination#page=1)). A person who has washed is not radioactive and is safe to be with.

**A dirty bomb is a bomb first.** Treat the casualties for blast and bleeding ([Severe bleeding card](card:severe-bleeding)); the radiation is a localised, secondary problem. Move upwind and uphill, do not touch debris or dust, and get people inside ([NRR 2025, p. 40](doc:nrr-2025#page=40)).

**Do not take iodine tablets on your own initiative.** They only matter if the release contains radioactive iodine and only for the thyroid; the authorities will say if and when ([NRPB, p. 8](doc:nrpb-stable-iodine#page=8)).

{{module:radiation}}

## First 72 hours

An accident at a UK civil site is planned for as a release that crosses the site boundary: no immediate fatal effects off site are expected, some off-site casualties are possible, and the contamination of food and land depends on the weather ([NRR 2025, p. 96](doc:nrr-2025#page=96)). The same is true for a release at a nearby foreign site, where the UK effect is a long-term cancer risk rather than acute illness ([NRR 2025, p. 98](doc:nrr-2025#page=98)).

- **Follow the instruction for your zone.** Around every licensed site the council holds an off-site plan with a Detailed Emergency Planning Zone in which tablets and advice are pre-distributed ([REPPIR 2019](kiwix:legislation_uk/www.legislation.gov.uk/uksi/2019/703/contents)). Sheltering is usually advised over evacuation because a moving car offers no protection and the plume passes ([FEMA, p. 74](doc:fema-nuclear-detonation-2022#page=74)).
- **Iodine, if and when told.** NRPB doses: adults 100 mg iodine (169 mg potassium iodate), children 3 to 12 half, 1 month to 3 years a quarter, newborns an eighth; priority to newborns, under-tens, and pregnant or breastfeeding women ([NRPB, p. 9](doc:nrpb-stable-iodine#page=9)). Over-40s gain almost nothing ([NRPB, p. 16](doc:nrpb-stable-iodine#page=16)).
- **Water** from the mains, covered tanks and sealed bottles is safe; do not drink from water butts, ponds or streams downwind until cleared ([Water module](module:water)).
- **Animals in.** Shut poultry and pets in, bring livestock under cover and feed them stored feed and covered water; grazing animals are how iodine reaches milk ([Windscale fire](kiwix:wikipedia_en_all_maxi/Windscale_fire)).
- **Keep the radio on.** Instructions change as the plume moves ([FEMA, p. 128](doc:fema-nuclear-detonation-2022#page=128)).

{{module:evacuation}}

{{module:water}}

{{module:food}}

## First month

- Expect a **milk and produce ban** in the affected area: after the 1957 Windscale fire milk from 500 km² was poured away for a month ([Windscale fire](kiwix:wikipedia_en_all_maxi/Windscale_fire)). Discard leafy vegetables and fruit that were outside; wash and peel roots; sealed and stored food is fine.
- **Do not eat game, wild mushrooms or foraged food** from the area; fungi and moss concentrate caesium ([Chernobyl disaster](kiwix:wikipedia_en_all_maxi/Chernobyl_disaster)).
- **Monitoring and screening.** UKHSA runs monitoring units for people who may have been contaminated; go if asked, take the bag of clothes with you ([UKHSA nuclear emergencies](kiwix:govuk_resilience/www.gov.uk/government/publications/nuclear-emergencies-information-for-the-public)).
- **Lost or stolen sources** are the other route to exposure: a heavy metal cylinder or a scrap-metal find with a radiation trefoil is not to be opened or kept; keep people metres away and report it — [[call 999]] ([NRR 2025, p. 100](doc:nrr-2025#page=100)).

{{module:medical}}

{{module:comms}}

## Long term

Restrictions on upland sheep in Wales and Cumbria after Chernobyl in 1986 lasted until 2012 ([Chernobyl disaster](kiwix:wikipedia_en_all_maxi/Chernobyl_disaster)); caesium-137 halves every 30 years and is what closes land ([Caesium-137](kiwix:wikipedia_en_all_maxi/Caesium-137)). Iodine-131 is gone within months ([Iodine-131](kiwix:wikipedia_en_all_maxi/Iodine-131)). Ask for the thyroid screening offered to children in the affected area; thyroid cancer after radioiodine is treatable when found ([Thyroid cancer (NHS)](kiwix:nhs_uk/www.nhs.uk/conditions/thyroid-cancer/)). Keep the record of where you were and when; it matters for any later claim or study.

{{module:livestock}}

## UK specifics

- **The sites.** Operating stations at Heysham, Hartlepool, Torness and Sizewell B, the new build at Hinkley Point C and Sizewell C, the defuelling and decommissioning Magnox and AGR sites, Sellafield with the country's largest store of high-level waste, the fuel plants at Springfields and Capenhurst, the weapons establishments and the naval bases are all on the map ([nuclear sites overlay](map:?overlay=nuclear-sites); [Nuclear power in the United Kingdom](kiwix:wikipedia_en_all_maxi/Nuclear_power_in_the_United_Kingdom)).
- **Nearby foreign sites.** French stations on the Channel coast (Flamanville, Gravelines, Paluel, Penly) are closer to Kent, Sussex and the Channel Islands than most British ones; Fukushima in 2011 produced detectable iodine in the UK at harmless levels ([NRR 2025, p. 98](doc:nrr-2025#page=98)).
- **Who does what.** The site operator and the council run the off-site plan; UKHSA gives health advice; the Food Standards Agency imposes food restrictions ([REPPIR 2019](kiwix:legislation_uk/www.legislation.gov.uk/uksi/2019/703/contents)). Warnings come by Emergency Alert, local radio and, near sites, sirens and loudhailers ([Prepare, alerts](kiwix:prepare_uk/prepare.campaign.gov.uk/get-prepared-for-emergencies/alerts/)).
- **The UK's only deliberate radiological attack** was the 2006 polonium poisoning of Alexander Litvinenko; it contaminated dozens of London sites but harmed only those in direct contact ([NRR 2025, p. 40](doc:nrr-2025#page=40); [Poisoning of Alexander Litvinenko](kiwix:wikipedia_en_all_maxi/Poisoning_of_Alexander_Litvinenko)).
- **Numbers**: {{#if phones}}[[call 999]] for the explosion and [[call 111]] for health advice; the rest are on [UK numbers](page:uk-numbers).{{else}}nothing answers while the phones are down, so take an emergency to the nearest fire or ambulance station in person ([getting help without phones](page:no-phones)); the numbers for when the lines return are on [UK numbers](page:uk-numbers).{{/if}}

## Checklist

- [ ] Find the nearest nuclear site on the map and note which way the wind is blowing from it {#site-and-wind}
- [ ] Doors and windows shut, fans and extractors off, everyone and pets inside {#go-in-stay-in}
- [ ] Radio on; Emergency Alerts switched on in every phone {#tune-in}
- [ ] Anyone who was outside: outer clothes bagged at the door, shower, no conditioner {#decontaminate}
- [ ] Bag of contaminated clothes labelled and kept outside the living space {#bag-clothes}
- [ ] Iodine tablets only when the authorities say, doses by age written down {#iodine-when-told}
- [ ] Livestock and poultry under cover on stored feed and covered water {#animals-under-cover}
- [ ] No milk, leafy greens, game or foraged food from the area until cleared {#food-restrictions}
- [ ] Water butts covered; drink mains, tank or bottled water only {#covered-water}
- [ ] Record where everyone was, for how long, and what they did afterwards {#exposure-record}

## Go deeper

- [Radiation module](module:radiation)
- [Radiation sickness card](card:radiation-sickness)
- [UKHSA decontamination sheet](doc:ukhsa-radiation-decontamination#page=1)
- [NRPB stable iodine report, the dose table](doc:nrpb-stable-iodine#page=9)
- [Chernobyl disaster (Wikipedia)](kiwix:wikipedia_en_all_maxi/Chernobyl_disaster)
- [Fukushima nuclear accident (Wikipedia)](kiwix:wikipedia_en_all_maxi/Fukushima_nuclear_accident)
- [Dirty bomb (Wikipedia)](kiwix:wikipedia_en_all_maxi/Dirty_bomb)
- [Radiation emergencies (Ready.gov)](kiwix:www.ready.gov_en/www.ready.gov/radiation)
- [Nuclear sites overlay](map:?overlay=nuclear-sites&overlay=health)
- [Nuclear war playbook](playbook:nuclear-war)
