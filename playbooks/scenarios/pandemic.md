---
id: pandemic
title: Lethal pandemic
icon: virus
order: 3
summary: A respiratory pandemic that overwhelms the NHS. Isolation, home nursing, oral rehydration, sepsis, and keeping the household fed and sane for months.
modules: [medical, sanitation, food, water, mental-health, community, comms]
overlays: [health]
reviewed: null
sources:
  - title: National Risk Register 2025
    doc: nrr-2025
    as_at: 2025-01-16
  - title: Flu (NHS)
    kiwix: nhs_uk/www.nhs.uk/conditions/flu/
    as_at: 2026-09
  - title: Sepsis (NHS)
    kiwix: nhs_uk/www.nhs.uk/conditions/sepsis/
    as_at: 2026-09
  - title: Paracetamol for children (NHS)
    kiwix: nhs_medicines/www.nhs.uk/medicines/paracetamol-for-children/
    as_at: 2025-12-14
  - title: Influenza (WikiMed)
    kiwix: wikipedia_en_medicine_maxi/Influenza
    as_at: 2026-02-15
  - title: N95 respirator (Wikipedia)
    kiwix: wikipedia_en_all_maxi/N95_respirator
    as_at: 2026-02-15
  - title: "Ship Captain's Medical Guide, chapter 3: general nursing"
    doc: scmg-ch03
    as_at: 2019-10
  - title: "Ship Captain's Medical Guide, chapter 6: communicable diseases"
    doc: scmg-ch06
    as_at: 2019-10
  - title: Survival and Austere Medicine, 3rd edition
    doc: survival-austere-medicine-2017
    as_at: 2017-01
  - title: Spanish flu (Wikipedia)
    kiwix: wikipedia_en_all_maxi/Spanish_flu
    as_at: 2026-02-15
---

## Right now

**Cut contact.** The planning assumption is a respiratory pathogen that spreads by close proximity, with 4% of the sick needing hospital and 2.5% dying, for at least nine months ([NRR 2025, p. 156](doc:nrr-2025#page=156)). Every day of distance you buy before the peak is a day the household is not sick at once. Stop non-essential trips now, not when told.

**If someone is already ill:** one room, one carer, door shut, window open; the carer wears a mask (FFP2 or FFP3 if you have them, a surgical or cloth mask if not) and {{#if water}}washes hands for 20 seconds after every contact{{else}}washes hands for 20 seconds after every contact, poured from a jug over a bowl now the mains is off, with alcohol gel only as a stopgap{{/if}} ([Hand washing](kiwix:wikipedia_en_all_maxi/Hand_washing); [European respirator standards](kiwix:wikipedia_en_all_maxi/European_respirator_standards)). Separate cup, plate, towel and bedding ([Ship Captain's Medical Guide ch. 6](doc:scmg-ch06)).

**Know the emergency signs** that still justify a hospital even when the wards are overwhelmed: breathing so hard they cannot finish a sentence, blue or grey lips, confusion, a rash that does not fade under a glass, no urine for a day, or a child who is floppy or will not wake — [[call 999]] ([Sepsis (NHS)](kiwix:nhs_uk/www.nhs.uk/conditions/sepsis/)).

{{module:medical}}

## First 72 hours

- **Stock the sickroom:** paracetamol, oral rehydration salts or the home recipe ([Dehydration card](card:dehydration)), a thermometer, a pulse oximeter if you have one, gloves, bin bags, thin bleach. Adults take 1 g of paracetamol up to four times a day, never more than 4 g in 24 hours ([Paracetamol for adults (NHS)](kiwix:nhs_medicines/www.nhs.uk/medicines/paracetamol-for-adults/)). Children by age, from the NHS table: infant liquid (120 mg in 5 ml) 2.5 ml at 3 to 5 months, 5 ml at 6 to 23 months, 7.5 ml at 2 to 3 years, 10 ml at 4 to 5 years; six-plus liquid (250 mg in 5 ml) 5 ml at 6 to 7 years, 7.5 ml at 8 to 9, 10 ml at 10 to 11, 10 to 15 ml at 12 to 15; up to four times a day, at least four hours apart, never more than four doses in 24 hours, and a baby under 3 months only on advice ([Paracetamol for children (NHS)](kiwix:nhs_medicines/www.nhs.uk/medicines/paracetamol-for-children/)).
- **How long to keep them apart.** Flu is infectious from about a day before symptoms to 5 to 7 days after, and for weeks in children and people with weak immune systems ([Influenza (WikiMed)](kiwix:wikipedia_en_medicine_maxi/Influenza)); COVID-19 showed symptoms a median of four to five days after infection and up to 14 days ([COVID-19 (WikiMed)](kiwix:wikipedia_en_medicine_maxi/COVID-19); [Incubation period (WikiMed)](kiwix:wikipedia_en_medicine_maxi/Incubation_period)). So: the sick person stays in the room until at least a week after symptoms began and until they are clearly better; anyone who shared a room with them before the door shut keeps apart from the rest, watches for symptoms, and is treated as clear only after the incubation period, 14 days for the worst case, has passed without any.
- **Masks and air.** A respirator can be worn again a limited number of times if it is not wet, soiled or misshapen; in a shortage the American guidance allows up to five uses of one mask ([N95 respirator](kiwix:wikipedia_en_all_maxi/N95_respirator)); cloth masks are washed daily. Open doors and windows: natural ventilation is one of the main things that cuts the spread of airborne infection indoors ([Ventilation](kiwix:wikipedia_en_all_maxi/Ventilation_(architecture))).
- **Fluids first.** Fever and fast breathing lose litres a day; aim for pale urine. Small sips often beats big drinks that come back ([Dehydration (NHS)](kiwix:nhs_uk/www.nhs.uk/conditions/dehydration/)).
- **Oxygen saturation** below about 92% on a pulse oximeter in an adult who is breathless is a hospital sign, whatever the wait ([Pulse oximetry](kiwix:wikipedia_en_all_maxi/Pulse_oximetry)).
- **Nursing basics:** sit them up, turn them every two hours if they cannot move, mouth care, watch for pressure sores, write the temperature and breathing rate down twice a day ([Ship Captain's Medical Guide ch. 3](doc:scmg-ch03)).
- **Surfaces:** 0.5% chlorine (one part thin bleach to nine of water) on anything touched by vomit or faeces; ordinary soap and water for the rest ([Sanitation module](module:sanitation)).
- **Household plan:** one person does the outside errands, always the same one, masked, and strips and washes at the door ([Household plan](page:household-plan)). Name the second carer now, before the first one is ill: if the only carer goes down, the plan's out-of-area contact and the street's check-in list are what bring food to the door and a neighbour who has already had the disease to the bedside ([Household plan](page:household-plan); [Community module](module:community)).

{{module:sanitation}}

{{module:water}}

## First month

- **Waves.** The pandemic "may come in single or multiple waves"; the emergency stage lasts at least nine months ([NRR 2025, p. 156](doc:nrr-2025#page=156)). Assume the shops, schools and surgeries close and reopen more than once.
- **Bacterial complications** are what killed most people in 1918: pneumonia after the flu ([Spanish flu](kiwix:wikipedia_en_all_maxi/Spanish_flu)). A fever that comes back after improvement, rusty sputum or one-sided chest pain needs antibiotics; amoxicillin and doxycycline are the WHO first choices for community pneumonia ([WHO EML, p. 12](doc:who-eml-2025#page=12); [WHO EML, p. 18](doc:who-eml-2025#page=18)), prescribed by whoever can still prescribe. Do not self-source antibiotics while any pharmacy or 111 works ([Medical module](module:medical)).
- **Other illness does not stop.** Children still get measles and bronchiolitis, adults still get heart attacks; the quick cards are on [Medical module](module:medical).
- **Food and money.** A two-week store lets you skip the shop at the peak ([Food module](module:food)); keep cash for two weeks of essentials in small notes in case card networks or banks go down ([Economic collapse playbook](playbook:economic-collapse)).
- **Deaths at home.** Confirm death, keep the body cool and separate, and register it when registration is working ([Ship Captain's Medical Guide ch. 12, p. 1](doc:scmg-ch12#page=1)); the steps, the deadlines and grief are on [death and grief](page:death-and-grief).

{{module:food}}

{{module:mental-health}}

## Long term

The register's unmitigated case has half the population fall ill over the course of the pandemic, about 1.34 million needing hospital treatment and up to 840,000 deaths, and it expects recovery of health and social care, and of society, education and the economy, to take years, with each wave's recovery cut short by the next ([NRR 2025, p. 157](doc:nrr-2025#page=157)). For a household that means planning the year, not the month: the two-week store is rebuilt after every wave, schooling happens at home when the school shuts, and the people who did the outside errands change as immunity spreads. Vaccines, if they come, arrive by priority group over months ([Vaccination](kiwix:wikipedia_en_all_maxi/Vaccination)), so the sickroom rules stay in force until the household's own turn has come and gone. Grief accumulates: distress that has not eased after four weeks is a medical problem, not a weakness ([PTSD (NHS)](kiwix:nhs_uk/www.nhs.uk/mental-health/conditions/ptsd-post-traumatic-stress-disorder/)), and the practicalities are on [death and grief](page:death-and-grief) and [Coping with trauma](kiwix:prepare_uk/prepare.campaign.gov.uk/coping-with-trauma/). Communities that organised food, medicine runs and check-ins in 2020 are the model ([COVID-19 pandemic in the United Kingdom](kiwix:wikipedia_en_all_maxi/COVID-19_pandemic_in_the_United_Kingdom)).

{{module:community}}

{{module:comms}}

## UK specifics

- **Numbers:** {{#if phones}}[[call 999]] for the emergency signs, and [[call 111]] for advice and antivirals; Pharmacy First in England covers minor illness, and Northern Ireland uses GP out-of-hours numbers ([UK numbers](page:uk-numbers)).{{else}}No number answers while the phones are down: take the emergency signs to a hospital in person, ask a pharmacy at the counter for the rest, and read [getting help without phones](page:no-phones); the numbers for later are on [UK numbers](page:uk-numbers).{{/if}} The NHS pages in this box are a dated snapshot ([About](page:about-sos)).
- **Powers.** Lockdowns, school closures and travel limits are lawful orders, not advice, made under the Civil Contingencies Act 2004 and the health protection laws; the Act is summarised in the [security and the law module](module:security-law).
- **UK drug names.** American sources in this library say acetaminophen for paracetamol and albuterol for salbutamol ([Medical module](module:medical)).
- **Sick day rules.** Anyone on insulin, steroids or heart medicines should know from their GP what to do when they cannot eat ([Type 1 diabetes (NHS)](kiwix:nhs_uk/www.nhs.uk/conditions/type-1-diabetes/)).

## Checklist

- [ ] Anyone ill into one room, door shut and window open, own bathroom or a lidded bucket {#sickroom now}
- [ ] One carer named and a second in reserve; mask on (FFP2 or FFP3 if you have them), gloves and apron at the door {#one-carer now}
- [ ] Hand-washing station at the door: 20 seconds of soap and water after every contact, and a separate cup, plate, towel and bedding {#hand-washing now}
- [ ] Rehydration salts mixed and to hand; paracetamol, thermometer, oximeter and bleach in the room {#sickroom-kit now}
- [ ] Emergency signs on the wall: breathless, blue lips, confused, no urine, rash that does not fade {#red-flags-on-wall now}
- [ ] Non-essential trips stopped; one person does all outside errands and strips and washes at the door {#single-runner now}
- [ ] Temperature, breathing rate and fluids logged twice a day per patient {#patient-log today}
- [ ] Two weeks of prescription medicines in hand and the sick day rules written down {#medicines-two-weeks today}
- [ ] Two weeks of food and a way to cook it without leaving the house {#two-weeks-food today}
- [ ] Neighbours checked by phone, note or through the window every day {#daily-neighbour-check today}
- [ ] Cash for two weeks of essentials in small notes in case banks and cards stop {#cash-reserve week}

## Go deeper

- [Medical module](module:medical)
- [Dehydration card](card:dehydration)
- [Death and grief](page:death-and-grief)
- [Ship Captain's Medical Guide, general nursing](doc:scmg-ch03)
- [Ship Captain's Medical Guide, communicable diseases](doc:scmg-ch06)
- [Survival and Austere Medicine](doc:survival-austere-medicine-2017#page=10)
- [Paracetamol for children (NHS)](kiwix:nhs_medicines/www.nhs.uk/medicines/paracetamol-for-children/)
- [Flu (NHS)](kiwix:nhs_uk/www.nhs.uk/conditions/flu/)
- [Pneumonia (NHS)](kiwix:nhs_uk/www.nhs.uk/conditions/pneumonia/)
- [Influenza (WikiMed)](kiwix:wikipedia_en_medicine_maxi/Influenza)
- [Quarantine (Wikipedia)](kiwix:wikipedia_en_all_maxi/Quarantine)
- [Pandemic (Ready.gov)](kiwix:www.ready.gov_en/www.ready.gov/pandemic)
- [Hospitals and pharmacies on the map](map:?overlay=health)
- [Where There Is No Doctor (Hesperian)](doc:where-there-is-no-doctor)
- [Quick guides for medicine](kiwix:quickguidesformedicine_en_all/index.html)
- [Field Hygiene and Sanitation, FM 21-10](doc:fm-21-10-field-hygiene)
- [Living in the field: hygiene](page:fieldcraft-hygiene)
