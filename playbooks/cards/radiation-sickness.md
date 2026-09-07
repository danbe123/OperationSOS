---
id: radiation-sickness
title: Radiation sickness
icon: radiation
order: 9
summary: First aid and nursing for someone who was out in fallout or near a radiation source when no hospital can help.
---

## When to use

Nausea, vomiting or diarrhoea within hours of being outside during fallout or near a radiation source.

## Steps

1. Get everyone inside and away from the fallout first.
2. Remove outer clothing, bag it, wash skin and hair with soap.
3. Write down when the exposure started and when vomiting began.
4. The sooner the vomiting, the higher the dose: the time scale, the shielding and the decontamination details are in the [radiation module](module:radiation).
5. {{#if water}}Rest, fluids and oral rehydration solution ([dehydration card](card:dehydration)); paracetamol for fever and pain; small frequent meals when they can eat.{{else}}Rest, fluids and oral rehydration solution made with stored or covered water, which the fallout has not reached ([dehydration card](card:dehydration)); paracetamol for fever and pain; small frequent meals when they can eat.{{/if}}
6. Keep every cut clean and covered ([wound cleaning](card:wound-cleaning)); infection is the main killer in the following weeks while the blood counts fall.
7. Keep them away from anyone with a cough or cold and away from crowds.
8. Stable iodine does nothing for radiation sickness; when and whether to take it is in the [radiation module](module:radiation).

{{#unless power}}
No hospital, no blood counts and no fridge, so keep going with what needs no power: fluids, rest, clean food, mouth care and scrupulous care of every cut. Boil water on gas or on a stove used outdoors and cool it covered. Check what antibiotics you hold, and what each is for, before you need them rather than after ([Chronic conditions](page:chronic-conditions); [medical module](module:medical)). Work by torch and keep the torch and the box charged from a power bank or solar rather than running lamps all night.
{{/unless}}

{{#if scenario:nuclear-war}}
Sheltering comes before treating. Nobody goes outside to fetch help while the fallout is at its worst, because the dose taken going out is worse than the delay ([radiation module](module:radiation)). Decontaminate and nurse inside the shelter. Write down, for each person, the time of the flash and the time their vomiting began, and keep the list: that timing is what the module's dose scale is read against, and it is the only measurement you will have of who is in most danger ([FEMA nuclear detonation guidance, p. 97](doc:fema-nuclear-detonation-2022#page=97)).
{{/if}}

{{#if scenario:nuclear-accident}}
An accident at a reactor or in transport means an official response exists: go in, stay in, tune in, and take stable iodine only when you are told to, because it protects the thyroid alone and does nothing for radiation sickness ([radiation module](module:radiation)). Decontaminate before treating: outer clothing off and bagged, then skin and hair washed with soap and no conditioner ([UKHSA decontamination, p. 1](doc:ukhsa-radiation-decontamination#page=1)). Somebody who has been decontaminated is safe to nurse, so nobody is left untreated for fear of contamination.
{{/if}}

## Warnings

**Warning:** Skin burns, hair loss and bleeding gums two to three weeks later mean a high dose; get medical help by any route.
**Warning:** A person who has been decontaminated is not radioactive and is safe to nurse.

## Stop or escalate

Hospital care with antibiotics and transfusions changes the odds at doses above about 2 Gy, so get them to it by any route — [[call 999]]. {{#if phones}}For advice short of an emergency, [[call 111]] — in Northern Ireland there is no 111, so use your trust's Phone First number or the GP out-of-hours service ([UK numbers](page:uk-numbers)).{{else}}Nothing short of an emergency will be answered from here: use the cards and the [medical module](module:medical).{{/if}} If nobody can come: nurse them as for any grave illness, with fluids, mouth care, clean food, daily washing and scrupulous care of every cut ([Ship Captain's Medical Guide ch. 3](doc:scmg-ch03)); treat the first fever as a serious infection with the antibiotics you hold under the rules in Where There Is No Doctor ([WTIND, p. 381](doc:where-there-is-no-doctor#page=381)); and expect radiation to worsen every other injury, so burns and wounds in the same person get the highest priority ([Emergency War Surgery, p. 449](doc:emergency-war-surgery-2018#page=449)).

## Source

[Acute radiation syndrome (Wikipedia)](kiwix:wikipedia_en_all_maxi/Acute_radiation_syndrome); [FEMA nuclear detonation guidance, p. 97](doc:fema-nuclear-detonation-2022#page=97); [Emergency War Surgery, p. 448](doc:emergency-war-surgery-2018#page=448); [Ship Captain's Medical Guide ch. 3](doc:scmg-ch03); [UKHSA: removing radioactive material from your skin and clothes](doc:ukhsa-radiation-decontamination).
