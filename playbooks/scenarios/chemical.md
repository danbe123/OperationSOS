---
id: chemical
title: Chemical or industrial disaster
icon: flask
order: 16
summary: A toxic plume from a refinery, chemical works, tanker or attack. Upwind and indoors, seal the room, remove-remove-remove, and the checks afterwards.
modules: [evacuation, medical, water, shelter-heat, comms, sanitation]
overlays: [chemical-sites, health, water]
reviewed: null
sources:
  - title: National Risk Register 2025
    doc: nrr-2025
    as_at: 2025-01-16
  - title: Chemical emergencies, information for the public (UKHSA)
    kiwix: govuk_resilience/www.gov.uk/government/publications/chemical-emergencies-information-for-the-public
    as_at: 2026-09
  - title: "Ship Captain's Medical Guide, chapter 2: toxic hazards of chemicals"
    doc: scmg-ch02
    as_at: 2019-10
  - title: HSE INDG258 Confined spaces
    doc: hse-indg258
    as_at: 2026-09
  - title: Buncefield fire (Wikipedia)
    kiwix: wikipedia_en_all_maxi/Buncefield_fire
    as_at: 2026-02-15
  - title: Flixborough disaster (Wikipedia)
    kiwix: wikipedia_en_all_maxi/Flixborough_disaster
    as_at: 2026-02-15
  - title: Hazchem (Wikipedia)
    kiwix: wikipedia_en_all_maxi/Hazchem
    as_at: 2026-02-15
  - title: Poisoning (NHS)
    kiwix: nhs_uk/www.nhs.uk/conditions/poisoning/
    as_at: 2026-09
---

## Right now

**Go in, stay in, tune in.** That is the government's instruction for a chemical release: indoors, doors and windows shut, fans, extractors and the boiler off, into a room with the fewest openings, and the radio on ([UKHSA chemical emergencies](kiwix:govuk_resilience/www.gov.uk/government/publications/chemical-emergencies-information-for-the-public)). If you are outside, move upwind or across the wind, uphill, away from the smell; do not drive into it.

**If it is on you: remove, remove, remove.** Get away from the source, take the clothing off (cut it rather than pulling it over the head), blot the skin dry, then {{#if water}}wash with plenty of water{{else}}wash with stored water, poured slowly and generously, because a shortage is no reason to skimp here{{/if}}; bag the clothes ([Chemical exposure card](card:chemical-exposure); [UKHSA chemical emergencies](kiwix:govuk_resilience/www.gov.uk/government/publications/chemical-emergencies-information-for-the-public)).

**Do not go into a cellar, tank, pit or building to rescue someone who has collapsed:** the gas that dropped them drops you; confined-space deaths are usually the rescuers ([HSE INDG258](doc:hse-indg258)).

**Which gas?** Chlorine and most industrial gases are heavier than air and pool in low ground, cellars and ground floors; go up ([Chlorine](kiwix:wikipedia_en_all_maxi/Chlorine)). Ammonia is lighter and rises ([Ammonia](kiwix:wikipedia_en_all_maxi/Ammonia)). A tanker's orange Hazchem plate tells the fire service what it carries; the letter E on it means evacuate ([Hazchem](kiwix:wikipedia_en_all_maxi/Hazchem)).

{{module:evacuation}}

## First 72 hours

- **How long.** The register's toxic-release scenario is a large gas release from a COMAH site near a town, with deaths, casualties and long-term health effects in the vulnerable ([NRR 2025, p. 108](doc:nrr-2025#page=108)); its fire scenario is Buncefield-style, a visible plume and buildings damaged near the site ([NRR 2025, p. 106](doc:nrr-2025#page=106)). A gas cloud passes in hours; a fire's smoke can last days.
- **Sealing the room.** Tape or wet towels along door and window gaps; one room is easier to seal than a house; open it up as soon as the all-clear comes because a sealed room runs out of air in hours ([Shelter-in-place](kiwix:wikipedia_en_all_maxi/Shelter-in-place)).
- **Symptoms and treatment.** Stinging eyes, cough, chest tightness, headache; fresh air, eye flushing for 15 minutes, no vomiting induced; breathing difficulty, burns or confusion need an ambulance, and whoever you reach must be told the substance — [[call 999]] ([Poisoning (NHS)](kiwix:nhs_uk/www.nhs.uk/conditions/poisoning/); [Ship Captain's Medical Guide ch. 2](doc:scmg-ch02)). Chemical burns are rinsed for 20 minutes or more ([Burns card](card:burns)). Lung injury from chlorine or smoke can appear hours later; anyone exposed is watched overnight ([Chemical exposure card](card:chemical-exposure)).
- **Water.** Cover water butts; do not drink from open sources downwind; {{#if water}}tap water is safe unless the company says otherwise{{else}}with the mains off, use stored and covered water, which the plume has not reached{{/if}} ([Water module](module:water)).
- **Evacuation** only when the police or an Emergency Alert say so, by the route given; the cordon may be a kilometre or more ([NRR 2025, p. 22](doc:nrr-2025#page=22); [How alerts work](kiwix:govuk_resilience/www.gov.uk/alerts/how-alerts-work)).
- **Pets** in; livestock under cover and off contaminated grass ([Evacuation module](module:evacuation)).

{{module:medical}}

{{module:shelter-heat}}

{{module:water}}

## First month

- **Going back.** Ventilate fully when told, wash hard surfaces, launder everything that was exposed, and discard open food and garden produce the plume passed over until the council says otherwise ([UKHSA chemical emergencies](kiwix:govuk_resilience/www.gov.uk/government/publications/chemical-emergencies-information-for-the-public)).
- **Health follow-up.** Register with the council's incident helpline so you are in the health study; keep a note of symptoms; asthma flares are common for weeks ([Asthma (NHS)](kiwix:nhs_uk/www.nhs.uk/conditions/asthma/)).
- **Deliberate release.** Salisbury in 2018 showed what a nerve agent does and that one contaminated object can kill weeks later ([Poisoning of Sergei and Yulia Skripal](kiwix:wikipedia_en_all_maxi/Poisoning_of_Sergei_and_Yulia_Skripal); [NRR 2025, p. 40](doc:nrr-2025#page=40)); do not pick up discarded bottles, perfume or containers near any incident. Nerve agents cause pinpoint pupils, drooling, twitching and collapse; the treatment is atropine, which paramedics carry ([Nerve agent](kiwix:wikipedia_en_all_maxi/Nerve_agent); [Atropine](kiwix:wikipedia_en_all_maxi/Atropine)).
- **Sanitation.** Wash water from decontamination is contaminated; keep it out of the drinking supply and the vegetable patch ([Sanitation module](module:sanitation)).

{{module:comms}}

{{module:sanitation}}

## Long term

Britain's worst industrial accidents, Flixborough in 1974 with 28 dead and Buncefield in 2005, the largest peacetime fire in Europe, produced the COMAH rules that make every major site plan for the public around it ([Flixborough disaster](kiwix:wikipedia_en_all_maxi/Flixborough_disaster); [Buncefield fire](kiwix:wikipedia_en_all_maxi/Buncefield_fire); [Control of Major Accident Hazards Regulations 2015](kiwix:wikipedia_en_all_maxi/Control_of_Major_Accident_Hazards_Regulations_2015)). Bhopal in 1984 is what happens when there is no plan ([Bhopal disaster](kiwix:wikipedia_en_all_maxi/Bhopal_disaster)). Long-term contamination of land and water is the council's and the Environment Agency's to test; keep every letter and result.

## UK specifics

- **The sites.** Refineries at Grangemouth, Stanlow, Fawley and the Humber, the chemical works of Teesside, Runcorn and Ellesmere Port, fuel terminals and gas storage, all on the map ([chemical sites overlay](map:?overlay=chemical-sites&overlay=water); [Grangemouth Refinery](kiwix:wikipedia_en_all_maxi/Grangemouth_Refinery); [Stanlow Oil Refinery](kiwix:wikipedia_en_all_maxi/Stanlow_Oil_Refinery)). Upper-tier COMAH sites must inform the people around them of what to do; ask the site or the council for the leaflet ([NRR 2025, p. 108](doc:nrr-2025#page=108)).
- **Roads and rail.** A tanker or a rail wagon is a moving chemical site; the register plans for accidents with high-consequence dangerous goods ([Dangerous goods](kiwix:wikipedia_en_all_maxi/Dangerous_goods)); the Hazchem plate is the label ([Hazchem](kiwix:wikipedia_en_all_maxi/Hazchem)).
- {{#if phones}}**Numbers:** [[call 999]] for the incident and [[call 111]] for advice; the Environment Agency incident hotline is 0800 80 70 60 for pollution of water or land ([UK numbers](page:uk-numbers)).{{else}}**Numbers:** none of them connect while the phones are down: take a casualty to hospital or a fire station yourself and report the release to the police in person ([getting help without phones](page:no-phones); [UK numbers](page:uk-numbers)).{{/if}}
- **Warnings:** Emergency Alerts, site sirens where they exist, and the police door to door ([Prepare, alerts](kiwix:prepare_uk/prepare.campaign.gov.uk/get-prepared-for-emergencies/alerts/)).
- **Household chemicals** cause most poisonings in Britain; bleach and acid cleaners mixed make chlorine gas indoors ([Poisoning (NHS)](kiwix:nhs_uk/www.nhs.uk/conditions/poisoning/); [Chlorine](kiwix:wikipedia_en_all_maxi/Chlorine)).

## Checklist

- [ ] Nearest chemical, fuel and refinery sites found on the map; wind direction noted {#sites-and-wind}
- [ ] Shelter room chosen: upstairs, few windows, tape and towels stored in it {#shelter-room}
- [ ] Doors, windows, fans, extractors and the boiler off; radio on {#go-in-stay-in}
- [ ] Anyone exposed: clothes off and bagged, skin blotted then washed, eyes flushed {#remove-remove-remove}
- [ ] Nobody enters a cellar, tank or building to rescue a collapsed person {#no-confined-space-rescue}
- [ ] Water butts covered; open-source water not drunk {#cover-water}
- [ ] Pets in; livestock under cover {#animals-in}
- [ ] Evacuate only when told, by the route given {#evacuate-when-told}
- [ ] Symptoms and times written down for everyone exposed {#symptom-log}
- [ ] After the all-clear: ventilate, wash surfaces, launder, discard exposed food {#clean-up-after}

## Go deeper

- [Chemical exposure card](card:chemical-exposure)
- [Evacuation module](module:evacuation)
- [UKHSA chemical emergencies](kiwix:govuk_resilience/www.gov.uk/government/publications/chemical-emergencies-information-for-the-public)
- [Ship Captain's Medical Guide, chemical hazards](doc:scmg-ch02)
- [HSE INDG258 Confined spaces](doc:hse-indg258)
- [Buncefield fire (Wikipedia)](kiwix:wikipedia_en_all_maxi/Buncefield_fire)
- [Decontamination (Wikipedia)](kiwix:wikipedia_en_all_maxi/Decontamination)
- [Chemistry Q&A](kiwix:chemistry.stackexchange.com_en_all/questions)
- [Hazardous materials incidents (Ready.gov)](kiwix:www.ready.gov_en/www.ready.gov/hazmat)
- [Chemical sites on the map](map:?overlay=chemical-sites&overlay=health)
- [Terrorism playbook](playbook:terrorism)
