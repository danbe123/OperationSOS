---
id: food
title: Food
icon: food
order: 2
summary: What to store, how to cook without power, keeping food safe in a power cut and the law on foraging and fishing.
sources:
  - title: Prepare, get prepared for emergencies
    kiwix: prepare_uk/prepare.campaign.gov.uk/get-prepared-for-emergencies/
    as_at: 2026-09
  - title: How to chill, freeze and defrost food safely (FSA)
    kiwix: govuk_resilience/www.gov.uk/government/publications/how-to-chill-freeze-and-defrost-food-safely
    as_at: 2026-09
  - title: The Eatwell Guide (NHS)
    kiwix: nhs_uk/www.nhs.uk/live-well/eat-well/food-guidelines-and-food-labels/the-eatwell-guide/
    as_at: 2026-09
  - title: USDA Complete Guide to Home Canning
    kiwix: usda-2015_en/home
    as_at: 2025-04-11
  - title: Guidance for safe foraging (FSA)
    kiwix: govuk_resilience/www.gov.uk/government/publications/guidance-for-safe-foraging/guidance-for-safe-foraging
    as_at: 2023-01-27
  - title: National Risk Register 2025
    doc: nrr-2025
    as_at: 2025-01-16
  - title: UK CMOs' advice during a national power outage, food and nutrition
    kiwix: govuk_resilience/www.gov.uk/government/publications/public-health-advice-from-uk-cmos-during-a-national-power-outage/food-and-nutrition-scripts-for-broadcast-media
    as_at: 2025-12-16
  - title: Rationing in the United Kingdom (Wikipedia)
    kiwix: wikipedia_en_all_maxi/Rationing_in_the_United_Kingdom
    as_at: 2026-02-15
  - title: Agriculture in the United Kingdom (Wikipedia)
    kiwix: wikipedia_en_all_maxi/Agriculture_in_the_United_Kingdom
    as_at: 2026-02-15
---

## Key facts

- Prepare asks every household to keep at least three days of non-perishable food ([Prepare](kiwix:prepare_uk/prepare.campaign.gov.uk/get-prepared-for-emergencies/)); this box recommends building up to two weeks, because three days is a floor, not a target.
- Energy needs are roughly **2,000 kcal a day for women and 2,500 for men** ([Eatwell Guide](kiwix:nhs_uk/www.nhs.uk/live-well/eat-well/food-guidelines-and-food-labels/the-eatwell-guide/)); plan quantities around that, more for anyone doing physical work outdoors.
- The National Risk Register lists disruption and contamination of the food supply as reasonable worst-case risks ([NRR 2025, p. 122](doc:nrr-2025#page=122)).

## What to do

1. Build a store of tinned beans, fish, tomatoes and fruit; dried pasta, rice, oats and lentils; UHT and powdered milk; oil, salt, sugar, honey and stock cubes; tea and coffee; biscuits; peanut butter; baby formula (and read [Infant feeding](page:infant-feeding) for what to do when it runs out); pet food; and a manual tin opener. Rotate it first-in, first-out. Bulk storage of grain, flour, rice and pulses, keeping weevils and rats out, and how many grams of each make a day's calories are on the [Food storage](page:food-storage) page.
2. {{#if power}}In a power cut, keep fridge and freezer doors shut: a fridge holds its temperature for about 4 hours, a full freezer for 48 hours, a half-full one for 24 hours.{{else}}Keep the fridge and freezer doors shut from now on, and note the time the power went: a fridge holds its temperature for about 4 hours, a full freezer for 48 hours, a half-full one for 24 hours.{{/if}} Discard any chilled food that has been above 8 °C for more than 4 hours ([FSA chill, freeze and defrost](kiwix:govuk_resilience/www.gov.uk/government/publications/how-to-chill-freeze-and-defrost-food-safely)).
3. {{#if power}}Work out now how you would cook without mains power: a gas hob lit with a match, or a camping stove used only in a ventilated space; never a barbecue or a generator indoors, even in a doorway or open window ([Carbon monoxide card](card:carbon-monoxide)).{{else}}Cook on a gas hob lit with a match if the gas is still on, or on a camping stove used only in a ventilated space; never a barbecue or a generator indoors, even in a doorway or open window ([Carbon monoxide card](card:carbon-monoxide)).{{/if}}
4. Home-canning low-acid vegetables and meat needs a pressure canner; water-bath canning them risks botulism, which grows unseen in low-acid, low-oxygen jars ([USDA Complete Guide to Home Canning](kiwix:usda-2015_en/home); [Botulism](kiwix:wikipedia_en_all_maxi/Botulism)).
5. Never eat a wild fungus you cannot name with certainty, and never identify one from a photo on this box.

{{#unless power}}
**Eat in this order while the cold lasts:** the fridge first, then the freezer as it softens, then the cupboard. Cook one big pot for everyone rather than reheating twice. Food that has thawed but is still cold can be cooked and eaten at once, but raw food that has thawed is never refrozen ([FSA chill, freeze and defrost](kiwix:govuk_resilience/www.gov.uk/government/publications/how-to-chill-freeze-and-defrost-food-safely)). In winter an unheated porch or shed is a cold store; in summer nothing is, so open a tin rather than gamble on a thawed one ([CMO food and nutrition advice](kiwix:govuk_resilience/www.gov.uk/government/publications/public-health-advice-from-uk-cmos-during-a-national-power-outage/food-and-nutrition-scripts-for-broadcast-media)).
{{/unless}}

{{#unless shops}}
**With the shops shut, the cupboard is the ration.** Count what you hold in days rather than in tins: at roughly 2,000 kcal a day for women and 2,500 for men ([Eatwell Guide](kiwix:nhs_uk/www.nhs.uk/live-well/eat-well/food-guidelines-and-food-labels/the-eatwell-guide/)) a household can work out in an hour how long it can eat. Write that figure on the cupboard door, ration from today rather than when the shelves are bare, and feed children, pregnant women, the sick and anyone working outdoors first ([Food storage](page:food-storage)).
{{/unless}}

{{#if scenario:famine}}
**Ration from the first day, not the last.** A store spent in the first month is gone long before the first harvest, so set a weekly allowance for each person and write it down; British rationing ran from 1940 to 1954 on exactly that principle, with registration at one shop and fair shares for all ([Rationing in the United Kingdom](kiwix:wikipedia_en_all_maxi/Rationing_in_the_United_Kingdom)). Set next year's seed aside before anyone eats it ([Growing food module](module:growing-food)), and preserve every glut by drying, salting, pickling or jam rather than eating it at once.
{{/if}}

{{#if scenario:supply-chain}}
**Do not join the queue.** The UK produces about 60% of the food it eats and runs its shops on daily deliveries ([Agriculture in the United Kingdom](kiwix:wikipedia_en_all_maxi/Agriculture_in_the_United_Kingdom)), so shelves empty from panic buying long before the country is short: fresh produce goes first, then bread and milk, then tins. Buy the gaps in your list in ordinary quantities from ordinary shops, and buy them early rather than in the rush. A baby on formula is the tightest supply line in the house; the fallback when the tin runs out is on [Infant feeding](page:infant-feeding).
{{/if}}

## UK specifics

- Picking wild fruit, foliage, fungi and flowers for your own use is lawful, uprooting and selling are not, and verges, dog-walking routes and sprayed margins are contaminated: the detail is in [Foraging law](page:foraging-law) ([FSA safe foraging](kiwix:govuk_resilience/www.gov.uk/government/publications/guidance-for-safe-foraging/guidance-for-safe-foraging)).
- The plants and fungi that kill most often in the UK are hemlock water dropwort ([Oenanthe crocata](kiwix:wikipedia_en_all_maxi/Oenanthe_crocata)), mistaken for wild parsnip or celery, and the death cap ([Amanita phalloides](kiwix:wikipedia_en_all_maxi/Amanita_phalloides)), a fungus that resembles edible field mushrooms; the full list is in [Wild food in Britain and Ireland](page:fieldcraft-food).
- UK food rationing ran from 1940 to 1954 and is the country's own precedent for sustained shortage ([Rationing in the United Kingdom](kiwix:wikipedia_en_all_maxi/Rationing_in_the_United_Kingdom)).

## Go deeper

- [Foraging law](page:foraging-law)
- [Growing food module](module:growing-food)
- [Livestock module](module:livestock)
- [Food Preparation Library](kiwix:zimgit-food-preparation_en/home)
- [Food preservation (Wikipedia)](kiwix:wikipedia_en_all_maxi/Food_preservation)
- [Canning (Wikipedia)](kiwix:wikipedia_en_all_maxi/Canning)
- [Dehydration and rehydration card](card:dehydration)
- [Canadian Prepper: prepping food](kiwix:canadian-prepper_en_preppingfood/index.html)
- [GrimGrains: cooking from stores](kiwix:grimgrains_en_all/grimgrains.com/)
- [Wild food in Britain and Ireland](page:fieldcraft-food)
- [Food storage: bulk staples and the calorie table](page:food-storage)
- [Infant feeding](page:infant-feeding)
- [Butchery and preserving meat](page:butchery)
- [Fishing and the shore](page:fieldcraft-fishing)
