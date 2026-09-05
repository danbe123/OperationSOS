---
id: cyber-attack
title: Cyber attack on infrastructure
icon: laptop
order: 7
summary: Ransomware or sabotage takes out the NHS, banks, telecoms, water or the grid for days to weeks. Cash, paper records, water you can trust, and 999 by any route.
modules: [comms, water, power, medical, food, community]
overlays: [health, fuel, water]
reviewed: null
sources:
  - title: National Risk Register 2025
    doc: nrr-2025
    as_at: 2025-01-16
  - title: WannaCry ransomware attack (Wikipedia)
    kiwix: wikipedia_en_all_maxi/WannaCry_ransomware_attack
    as_at: 2026-02-15
  - title: 2024 CrowdStrike-related IT outages (Wikipedia)
    kiwix: wikipedia_en_all_maxi/2024_CrowdStrike-related_IT_outages
    as_at: 2026-02-15
  - title: 2015 Ukraine power grid hack (Wikipedia)
    kiwix: wikipedia_en_all_maxi/2015_Ukraine_power_grid_hack
    as_at: 2026-02-15
  - title: Telecommunications (Security) Act 2021 (Wikipedia)
    kiwix: wikipedia_en_all_maxi/Telecommunications_(Security)_Act_2021
    as_at: 2026-02-15
  - title: How emergency alerts work (GOV.UK)
    kiwix: govuk_resilience/www.gov.uk/alerts/how-alerts-work
    as_at: 2026-09
  - title: Prepare, get prepared for emergencies
    kiwix: prepare_uk/prepare.campaign.gov.uk/get-prepared-for-emergencies/
    as_at: 2026-09
---

## Right now

**Work out what has gone.** A cyber attack looks like an ordinary failure of one thing: the bank app, the GP system, the phone network, the water company's "do not drink" notice, the lights. The difference is that it will not be fixed by the evening, and the attacker may still be inside ([NRR 2025, p. 55](doc:nrr-2025#page=55)).

- **Telecoms down:** 999 and 112 may be unreachable for everyone on the affected network; try another phone on another network, a neighbour's landline, or go to the nearest fire station, police station or hospital in person ([NRR 2025, p. 55](doc:nrr-2025#page=55)). Texts often pass when calls do not ([What still works](page:what-still-works)).
- **Banks down:** use the cash you have, pay for essentials only, do not join a queue at a branch on a rumour ([NRR 2025, p. 59](doc:nrr-2025#page=59)).
- **Water notice:** if the company says do not drink, boiling may not make it safe; the planning case is water "unfit for human consumption even after boiling" ([NRR 2025, p. 120](doc:nrr-2025#page=120)). Use bottled or stored water until the notice is lifted ([Water module](module:water)).
- **Grid down:** run the [grid collapse playbook](playbook:grid-collapse), and tell the network operator — [[call 105]].

{{module:comms}}

## First 72 hours

- **How long.** Telecoms: "up to 72 hours, but could extend into weeks or months", with a contingency service possibly within a fortnight ([NRR 2025, p. 55](doc:nrr-2025#page=55)). A retail bank: at least 2 days offline and 2 more days partial, hardest on people with a single account ([NRR 2025, p. 59](doc:nrr-2025#page=59)). A financial market infrastructure: a week down, weeks partial, months to recover ([NRR 2025, p. 58](doc:nrr-2025#page=58)). The grid: pockets in hours, up to 7 days for full restoration, longer if the attack damaged systems ([NRR 2025, p. 45](doc:nrr-2025#page=45)). Gas: a regional loss taking about 3 months, with 3-hour rolling power cuts in the meantime ([NRR 2025, p. 43](doc:nrr-2025#page=43)). Fuel: a region without deliveries for several days ([NRR 2025, p. 49](doc:nrr-2025#page=49)).
- **The NHS.** The planning case is ransomware across at least 90% of the health estate, every system offline, appointments and tests cancelled, A&E diverting ([NRR 2025, p. 52](doc:nrr-2025#page=52)). Keep your own paper record: medicines and doses, allergies, conditions, the GP's name; a pharmacist who cannot see the record can still dispense against a repeat slip or a labelled box ([Medical module](module:medical)). WannaCry in May 2017 cancelled about 19,000 appointments in a week ([WannaCry ransomware attack](kiwix:wikipedia_en_all_maxi/WannaCry_ransomware_attack)); the Synnovis attack of June 2024 postponed 10,152 outpatient appointments and 1,710 operations in south-east London ([NRR 2025, p. 52](doc:nrr-2025#page=52)).
- **Cash and paper.** Contactless and online payments, Faster Payments and Bacs all stop with their systems ([Faster Payment System](kiwix:wikipedia_en_all_maxi/Faster_Payment_System_(United_Kingdom)); [Bacs](kiwix:wikipedia_en_all_maxi/Bacs)); a fortnight's cash in small notes and a cheque book cover the gap ([Cheque](kiwix:wikipedia_en_all_maxi/Cheque)).
- **Do not trust the screen.** {{#if internet}}Fake texts and emails follow every outage; the register asks you to use the SHARE checklist before passing anything on ([NRR 2025, p. 22](doc:nrr-2025#page=22)).{{else}}With the network down the rumours come by word of mouth instead, and they are no more reliable: check anything that matters against BBC local radio on FM before repeating it ([NRR 2025, p. 22](doc:nrr-2025#page=22)).{{/if}} Emergency Alerts come from the network, need no app, and are not sent by text ([How alerts work](kiwix:govuk_resilience/www.gov.uk/alerts/how-alerts-work)).

{{module:water}}

{{module:power}}

{{module:medical}}

## First month

- **Rolling power cuts** of 3 hours at a time, spread across Great Britain, if the attack took gas or generation ([NRR 2025, p. 43](doc:nrr-2025#page=43)); plan the day around the published schedule ([Power module](module:power)).
- **Food and fuel** move by lorry through depots that run on the same software; the CrowdStrike failure of 19 July 2024 grounded flights and stopped tills worldwide in a morning without any attacker ([2024 CrowdStrike-related IT outages](kiwix:wikipedia_en_all_maxi/2024_CrowdStrike-related_IT_outages)). Two weeks of food and a half tank are the buffer ([Food module](module:food)).
- **Data loss.** Some NHS and bank data "would be unrecoverable from backups" ([NRR 2025, p. 52](doc:nrr-2025#page=52)); keep paper copies of prescriptions, test results, insurance and bank statements from now on.
- **Neighbours who bank with one bank, depend on a card, or need a hospital appointment** are the ones to check on ([Community module](module:community)).

{{module:food}}

## Long term

Attacks on power systems are real: the December 2015 attack on Ukraine's grid cut power to about 230,000 people for up to six hours ([2015 Ukraine power grid hack](kiwix:wikipedia_en_all_maxi/2015_Ukraine_power_grid_hack)); the May 2021 Colonial Pipeline ransomware emptied filling stations on the US east coast for a week ([Colonial Pipeline ransomware attack](kiwix:wikipedia_en_all_maxi/Colonial_Pipeline_ransomware_attack)). Recovery is measured in months where data is destroyed ([NRR 2025, p. 58](doc:nrr-2025#page=58)). Households that keep cash, paper records, stored water and a battery radio are the ones that notice least ([Prepare](kiwix:prepare_uk/prepare.campaign.gov.uk/get-prepared-for-emergencies/)).

{{module:community}}

## UK specifics

- **999 when the network is down.** Any mobile will use any network for 999; a landline on Digital Voice needs power; if nothing works, go in person to a fire station, police station or hospital ([What still works](page:what-still-works); [UK numbers](page:uk-numbers)).
- **Telecoms security** is regulated under the Telecommunications (Security) Act 2021 ([Telecommunications (Security) Act 2021](kiwix:wikipedia_en_all_maxi/Telecommunications_(Security)_Act_2021)); Ofcom obliges providers to keep access to the emergency services ([NRR 2025, p. 88](doc:nrr-2025#page=88)).
- **Water:** companies must provide bottled water and bowsers when supply fails, prioritising the Priority Services Register ([Priority Services Register](kiwix:govuk_resilience/www.thepsr.co.uk/)); the Drinking Water Inspectorate's consumer pages explain notices ([DWI consumers](kiwix:govuk_resilience/www.dwi.gov.uk/consumers/)).
- **Banks:** the financial authorities' response framework covers the Bank of England, the Treasury and the FCA ([NRR 2025, p. 58](doc:nrr-2025#page=58)); deposits are protected by the Financial Services Compensation Scheme up to its published limit ([Financial Services Compensation Scheme](kiwix:wikipedia_en_all_maxi/Financial_Services_Compensation_Scheme)).
- **Fuel:** the National Emergency Plan for Fuel and Operation ESCALIN (military tanker drivers) cover regional shortages ([NRR 2025, p. 49](doc:nrr-2025#page=49)); petrol at home is limited to 30 litres ([Petroleum regulations 2014](kiwix:legislation_uk/www.legislation.gov.uk/uksi/2014/1637/contents)).

## Checklist

- [ ] Work out which service is down and whether 999 works on any phone in the house {#which-service-down}
- [ ] Paper record per person: medicines, doses, allergies, conditions, GP {#paper-medical-record}
- [ ] Two weeks of cash in small notes; cheque book found {#cash-fortnight}
- [ ] Repeat prescriptions collected early; two weeks of medicines in hand {#prescriptions-early}
- [ ] Stored water used if a do-not-drink notice is issued; boiling not assumed safe {#stored-water-notice}
- [ ] Battery radio on; Emergency Alerts on; SHARE checklist before forwarding anything {#radio-and-share}
- [ ] Paper copies of bank statements, insurance and key documents printed while you can {#paper-documents}
- [ ] Rolling-cut schedule for your area found and pinned up {#rota-schedule}
- [ ] Neighbours with one bank account or a hospital appointment checked on {#check-neighbours}

## Go deeper

- [Communications module](module:comms)
- [What still works in an outage](page:what-still-works)
- [UK emergency numbers](page:uk-numbers)
- [NRR 2025, cyber attack on telecommunications](doc:nrr-2025#page=55)
- [NRR 2025, cyber attack on the health service](doc:nrr-2025#page=52)
- [Ransomware (Wikipedia)](kiwix:wikipedia_en_all_maxi/Ransomware)
- [Cyberattack (Wikipedia)](kiwix:wikipedia_en_all_maxi/Cyberattack)
- [Cybersecurity (Ready.gov)](kiwix:www.ready.gov_en/www.ready.gov/cybersecurity)
- [Grid collapse playbook](playbook:grid-collapse)
- [Economic collapse playbook](playbook:economic-collapse)
- [Getting help without phones](page:no-phones)
