---
id: evacuation
title: Evacuation
icon: exit
order: 13
summary: Deciding whether to stay or go, the grab bag, shutting the house down, rest centres and travelling when roads and fuel are uncertain.
sources:
  - title: Prepare, get prepared for emergencies
    kiwix: prepare_uk/prepare.campaign.gov.uk/get-prepared-for-emergencies/
    as_at: 2026-09
  - title: Advice for disabled people and carers (Prepare)
    kiwix: prepare_uk/prepare.campaign.gov.uk/advice-for-disabled-persons-and-carers/
    as_at: 2026-09
  - title: Flood alerts and warnings, what they are and what to do (GOV.UK)
    kiwix: govuk_resilience/www.gov.uk/get-flood-warnings
    url: https://www.gov.uk/guidance/flood-alerts-and-warnings-what-they-are-and-what-to-do
    as_at: 2026-09
  - title: Help during a flood (GOV.UK)
    kiwix: govuk_resilience/www.gov.uk/help-during-flood
    as_at: 2026-09
  - title: Planning Guidance for Response to a Nuclear Detonation (FEMA)
    doc: fema-nuclear-detonation-2022
    as_at: 2022-11
  - title: Bug-out bag (Wikipedia)
    kiwix: wikipedia_en_all_maxi/Bug-out_bag
    as_at: 2026-02-15
  - title: National Risk Register 2025
    doc: nrr-2025
    as_at: 2025-01-16
  - title: Chemical emergencies, information for the public (UKHSA)
    kiwix: govuk_resilience/www.gov.uk/government/publications/chemical-emergencies-information-for-the-public
    as_at: 2026-09
  - title: What to do in a radiation emergency (UKHSA)
    kiwix: govuk_resilience/www.gov.uk/government/publications/radiation-emergencies-information-for-the-public/what-to-do-in-a-radiation-emergency
    as_at: 2026-09
---

## Key facts

- Staying put is the default in the UK. Leave only when the police or an Emergency Alert say so, or the building itself is unsafe: fire, rising water, structural damage, or a gas or chemical plume ([Prepare](kiwix:prepare_uk/prepare.campaign.gov.uk/get-prepared-for-emergencies/)).
- For a chemical plume the advice is to go in, stay in and tune in unless you are told to leave; for a fire it is get out, stay out, and get the fire brigade — [[call 999]].
- After a nuclear detonation, shelter first, and evacuate only when told to and along the route given ([FEMA, p. 33](doc:fema-nuclear-detonation-2022#page=33)).

## What to do

1. Pack a grab bag: documents (passports, insurance, prescriptions, a list of medicines), two weeks of medicines, a litre of water each, snacks, a torch, a radio, a power bank, cash in small notes, keys, a first-aid kit, a warm layer, waterproofs, a whistle, pen and paper, baby and pet items, and a card with this box's WiFi name and address ([Prepare](kiwix:prepare_uk/prepare.campaign.gov.uk/get-prepared-for-emergencies/); [bug-out bag](kiwix:wikipedia_en_all_maxi/Bug-out_bag)).
2. Before leaving, turn off gas, electricity and water if it is safe to do so, lock up, leave a note saying where you have gone, and tell someone your plan.
3. At a rest centre, run by the council with the Red Cross, register on arrival and keep the family together.
4. Keep the fuel tank at least half full in case you need to move; motorways jam quickly in a mass evacuation, and bicycles often get through when cars cannot.

{{#unless phones}}
**No alert will reach you and nobody can tell you to go.** Decide from what you can see and hear: water rising, fire, smoke, a wall or roof that has moved, or word brought by a neighbour or a police loudhailer. Send someone to the police or fire station for the official picture before you move a household ([Getting help without phones](page:no-phones)). If you do go, leave a note on the door saying who has left, when and where to, tell a neighbour the same, and take the household plan with you so that the meeting point and the out-of-area contact travel with you ([Household plan](page:household-plan)).
{{/unless}}

{{#if scenario:storms-flooding}}
**Once the water has arrived, go up rather than out.** At a flood warning move people, pets, medicines and documents upstairs or to higher ground; at a severe flood warning stay somewhere safe, be ready to leave, and do as the emergency services tell you ([help during a flood](kiwix:govuk_resilience/www.gov.uk/help-during-flood)). Move the car to higher ground early, before the roads go. Turn off gas, electricity and water at the mains if water is coming in and it is safe to do so — never touch an electrical switch while you are standing in water — then take medicines, documents and dry clothes, and register at the rest centre on arrival so that you can be found.
{{/if}}

{{#if scenario:chemical}}
**Do not evacuate yourself.** For a chemical release the instruction is to go in, stay in and tune in: indoors, doors and windows shut, anything that brings air in from outside such as fans or air conditioning turned off, radio on ([UKHSA chemical emergencies](kiwix:govuk_resilience/www.gov.uk/government/publications/chemical-emergencies-information-for-the-public)). Leave only when the police or an Emergency Alert say so and by the route you are given, moving upwind, never through the plume. If you were caught in it, the clothing comes off and you wash before you go into a rest centre, so that you do not carry it in with you ([Chemical exposure card](card:chemical-exposure)).
{{/if}}

{{#if scenario:nuclear-war}}
**Shelter first: leaving early is the mistake that kills.** Get inside and stay inside for at least 24 hours, expect that to extend to 48 hours or more where fallout is heavy, and evacuate only when you are told to and along the route you are given ([FEMA, p. 33](doc:fema-nuclear-detonation-2022#page=33); [FEMA, p. 74](doc:fema-nuclear-detonation-2022#page=74)). A car gives a protection factor of only about 2, so it is neither a shelter nor a way out through fallout ([Radiation module](module:radiation)). Do not drive home through fallout in order to shelter there: use the nearest solid building instead, and pack the grab bag while you wait rather than while you decide.
{{/if}}

{{#if scenario:nuclear-accident}}
**Sheltering is usually advised over evacuation.** Get into the nearest building rather than the one you would rather be in, and expect to be asked to stay in for one to two days; a vehicle gives no useful shelter and leaving early can increase your dose ([UKHSA, what to do](kiwix:govuk_resilience/www.gov.uk/government/publications/radiation-emergencies-information-for-the-public/what-to-do-in-a-radiation-emergency)). Do not drive to the school: children are kept in and told what to do. If an evacuation is ordered it comes by zone and by route; take medicines, documents and the grab bag, and expect to be checked and asked to change before you go into a centre.
{{/if}}

{{#if scenario:invasion}}
**Staying put in a prepared house is the default.** The register says targets are infrastructure and that no population centres are deliberately targeted ([NRR 2025, p. 184](doc:nrr-2025#page=184)); that no mass evacuation is planned follows from that rather than being the register's own words. Roads jam and become targets in their own right, and in 1939 children were moved by organised train, not by families driving. Go only if you are beside a target — power station, substation, fuel depot, port, airfield, barracks, bridge or mast, all on [the map](map:?overlay=military&overlay=airports&overlay=rail) — or if you are told to, and then do not delay it ([NRR 2025, p. 22](doc:nrr-2025#page=22)). Documents, cash and medicines travel with you.
{{/if}}

## UK specifics

- The flood decision is driven by the warning level, not by the water: at a **flood warning** move people, pets and valuables upstairs or to higher ground; at a **severe flood warning** stay somewhere safe, be ready to evacuate and do as the emergency services tell you ([get flood warnings](kiwix:govuk_resilience/www.gov.uk/get-flood-warnings); [help during a flood](kiwix:govuk_resilience/www.gov.uk/help-during-flood)). Never set off through water that has already arrived: once it is at the door, upstairs is usually safer than the street.
- Never drive or walk through floodwater: 15 cm of moving water can knock an adult off their feet, 30 cm will float a car, and 60 cm can carry one away ([help during a flood](kiwix:govuk_resilience/www.gov.uk/help-during-flood)).
- Anyone with a disability should have a personal evacuation plan in place in advance and be registered on the Priority Services Register ([advice for disabled people and carers](kiwix:prepare_uk/prepare.campaign.gov.uk/advice-for-disabled-persons-and-carers/)).
- Pets travel with you; livestock arrangements are covered separately in the [Livestock module](module:livestock).

## Go deeper

- [Household plan](page:household-plan)
- [Navigation module](module:navigation)
- [Vehicles and fuel module](module:vehicles-fuel)
- [Help during a flood](kiwix:govuk_resilience/www.gov.uk/help-during-flood)
- [Emergency management (Wikipedia)](kiwix:wikipedia_en_all_maxi/Emergency_management)
- [Rail and fuel on the map](map:?overlay=rail&overlay=fuel)
- [Canadian Prepper: bug-out concepts](kiwix:canadian-prepper_en_bugoutconcepts/index.html)
- [Canadian Prepper: bug-out bag](kiwix:canadian-prepper_en_bugoutroll/index.html)
- [Survival, Evasion and Recovery, FM 21-76-1 (pocket checklists)](doc:fm-21-76-1-survival-evasion-recovery)
- [Moving across country](page:fieldcraft-moving)
- [Map, compass and tides](page:fieldcraft-navigation)
- [Field craft in Britain](page:fieldcraft-basics)
- [Getting found](page:fieldcraft-rescue)
- [Getting help without phones](page:no-phones)
