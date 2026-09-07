# Health map tooltips — fact-check report

Checked 2026-09-07 against NHS England/NHS.UK, NHS 24, NHS 111 Wales, HSC NI/nidirect, gov.uk, CQC, legislation.gov.uk, Resuscitation Council UK, UKHSA, HTM 06-01/04-01, NHS EPRR core standards.
`expect` paragraphs are split into sentences `[kind.expect[sN]]`.

## hospital — Hospital

| tag | verdict | evidence (URL + supporting sentence) | suggested wording |
|---|---|---|---|
| hospital.expect[s1] | UNSUPPORTED | No authoritative source ranks the order in which health services stop. NHS.UK does say "A&E departments are open 24 hours a day, every day" (https://www.nhs.uk/nhs-services/urgent-and-emergency-care-services/when-to-go-to-ae/), but EDs are diverted, and whole hospitals evacuated, in real incidents. | "A&E runs 24 hours a day and is meant to keep running in an emergency, but it can be diverted or moved: do not assume the nearest one is open." |
| hospital.expect[s2] | VERIFIED | https://www.bjaed.org/article/S2058-5349(17)30033-1/fulltext — "By declaring a major incident, trusts are able to cancel non-urgent elective operations." | — |
| hospital.expect[s3] | PARTLY | https://www.nhs.uk/nhs-services/urgent-and-emergency-care-services/when-to-go-to-ae/ — A&E is for "serious injuries and life-threatening emergencies". "Make your own way" is not NHS advice and is unsafe for chest pain/stroke. | "Come here only for something life-threatening — but for chest pain, stroke or heavy bleeding call 999 first and do not drive yourself." |
| hospital.expect[s4] | PARTLY | Bringing medicines and a list is standard NHS pre-admission advice; "nobody can look your record up" is overstated — records are held on several systems and outages are rarely total. | "…because staff may not be able to see your record." |
| hospital.expect[s5] | UNSUPPORTED | No source endorses self-treating "anything smaller" without triage; NHS routes minor problems to 111/pharmacy/UTC. | "For anything smaller, try 111, a pharmacy or an urgent treatment centre first; if nothing answers, read the quick cards." |
| hospital.have[0] | PARTLY / misleading | HTM 06-01 sizes the generator day tank at ~10 hours full load; bulk tanks are commonly derogated to 48–72 hours (https://www.wbpsltd.co.uk/wp-content/uploads/2024/05/Common-HTM-6-Derrogations.pdf; SHTM 06-01 https://www.nss.nhs.scot/media/1791/shtm-06-01-part-a-v10-jul-2015.pdf). IT and at least one lift per group are normally *on* the essential supply, not "cut back". | "Standby generators typically hold 48–72 hours of fuel and then need resupply; they carry A&E, theatres, lifts, IT and essential lighting, not the whole site." |
| hospital.have[1] | VERIFIED | NHS EPRR core standards require plans for supply-chain disruption (https://www.england.nhs.uk/long-read/nhs-core-standards-for-emergency-preparedness-resilience-and-response-guidance/); blood components are short-dated (platelets 7 days). | — |
| hospital.have[2] | PARTLY | HTM 04-01 covers "supply, storage and distribution" of water in healthcare premises (https://www.england.nhs.uk/publication/safe-water-in-healthcare-premises-htm-04-01/); acute sites are mains-fed with multi-compartment cold-water storage, but stored volume is hours, not days. | "Water comes off the mains like everyone else's; on-site tanks hold hours, not days." |
| hospital.have[3] | PARTLY | Triage and mental-health liaison are general; midwifery only where the site has a maternity unit. "Switchboard with its own radios" is not a national requirement — EPRR requires resilient comms, not radios. | Drop "midwifery" unless the site has maternity; say "resilient communications" not "its own radios and landlines". |
| hospital.have[4] | UNSUPPORTED — unsafe | Rest, warmth and refreshment in an emergency are a local-authority rest-centre function, not a hospital one: https://assets.publishing.service.gov.uk/media/5a7c43e4ed915d7d70d1dafd/Evacuation_and_Shelter_Guidance_2014.pdf — rest centres "provide shelter, warmth, refreshments…". | Delete. Replace with: "If you need warmth or shelter, the council's rest centre — not the hospital — is the place." |
| hospital.have[5] | UNSUPPORTED — unsafe | Nothing authoritative says this, and it contradicts `hospital.avoid[0]`. Reads as an invitation to shelter at A&E. | Delete, or "The hospital is not a shelter; go for treatment only." |
| hospital.useful[0] | VERIFIED | https://www.nhs.uk/nhs-services/urgent-and-emergency-care-services/when-to-go-to-ae/ — A&E is for serious injuries and life-threatening emergencies; severe bleeding, chest pain, stroke signs, severe burns are listed 999/A&E conditions. | Add "call 999 for chest pain and stroke rather than travelling". |
| hospital.useful[1] | PARTLY — correct first | Home-oxygen patients are issued a back-up cylinder and a 24-hour supplier number: https://www.nhshighland.scot.nhs.uk/media/4dvlvcnv/contingency-planning-for-power-outages-home-oxygen.pdf — the back-up cylinder "should be used if there is a power cut". | "In a long blackout: use your back-up oxygen cylinder and ring your oxygen supplier's 24-hour line; ring your dialysis unit. Go to hospital only if breathing worsens or you cannot reach them." |
| hospital.useful[2] | VERIFIED | Smoke inhalation, crush injury and immersion are A&E/999 presentations (NHS.UK A&E page, above). | Add "call 999". |
| hospital.useful[3] | PARTLY | Falls, frostbite and hypothermia are A&E presentations, but severe hypothermia is a 999 call, not a walk-in. | "…and for hypothermia call 999 rather than walking someone cold and confused to hospital." |
| hospital.avoid[0] | VERIFIED | https://www.nhs.uk/nhs-services/urgent-and-emergency-care-services/when-to-go-to-ae/ — A&E is not for minor illness or routine care; https://www.bjaed.org/article/S2058-5349(17)30033-1/fulltext — routine activity is cancelled first. | — |
| hospital.avoid[1] | PARTLY | Major-incident triage prioritises the seriously injured, so minor cases wait (BJA Education, above); "many hours" is not a figure anyone publishes. | "…and anyone with a minor problem may wait a very long time." |
| hospital.avoid[2] | PARTLY | Hospitals restrict visiting and cohort patients in outbreaks (UKHSA/NHS infection prevention guidance); "the centre of any epidemic" overstates it. | "Hospitals see the sickest cases in an outbreak; keep well household members away from the doors." |
| hospital.avoid[3] | VERIFIED | https://www.gov.uk/government/publications/radiation-emergencies-information-for-the-public/what-to-do-in-a-radiation-emergency — the advice is to "go in, stay in, tune in". | Add the chemical-specific step: "if you have been splashed or sprayed, remove clothing and rinse before going indoors." |
| hospital.approach[0] | VERIFIED | Standard NHS advice to bring current medicines and a list of doses to hospital. | — |
| hospital.approach[1] | PARTLY — one item wrong | NHS emergency treatment does not require ID and A&E care is free at the point of use; hospitals are cashless/card in many trusts. | Drop "ID" and "cash"; keep water, warm layer, charger. |
| hospital.approach[2] | UNSUPPORTED | Generalisation about staff/visitor behaviour; no source. Also cuts across the need for a parent/guardian to consent for a child. | "Bring only the people who need to be there — but a child must be accompanied by a parent or guardian." |
| hospital.approach[3] | UNSUPPORTED | Sensible but nobody authoritative states it. | Frame as a tip, not a rule. |
| hospital.approach[4] | PARTLY | Telling staff about deterioration is right; "do not queue-jump" is a behavioural generalisation. | "Tell reception at once if someone is collapsing, bleeding heavily or struggling to breathe." |

## pharmacy — Pharmacy

| tag | verdict | evidence (URL + supporting sentence) | suggested wording |
|---|---|---|---|
| pharmacy.expect[s1] | UNSUPPORTED — likely wrong | Community pharmacy was an essential service kept open through the COVID-19 response; contractors must hold business continuity plans and report closures (NHS EPRR core standards, https://www.england.nhs.uk/long-read/nhs-core-standards-for-emergency-preparedness-resilience-and-response-guidance/). No source says pharmacies "shut early". | "A pharmacy needs power, deliveries and staff. Most stay open in an emergency, but the nearest one may be shut — check before a long walk." |
| pharmacy.expect[s2] | VERIFIED | NHS.UK pharmacy services: pharmacists give advice on medicines and minor illness without an appointment. | — |
| pharmacy.expect[s3] | PARTLY | Reg 225 HMR 2012 requires the pharmacist to be satisfied the medicine "was previously prescribed" (https://www.legislation.gov.uk/uksi/2012/1916/regulation/225), so the box/slip helps. But prescriptions are free in Scotland, Wales and NI; the England charge is £9.90 per item (https://commonslibrary.parliament.uk/constituency-casework-nhs-prescription-charges-in-england/). | "Bring the labelled box or repeat slip. In England bring cash — a prescription costs £9.90 an item and an emergency supply may be a private sale; prescriptions are free in Scotland, Wales and Northern Ireland." |
| pharmacy.expect[s4] | PARTLY | Quantity is a prescriber decision; UK medicines-supply guidance discourages patients requesting extra beyond clinical need. | "Ask your prescriber, well before you run out, whether a longer supply is clinically appropriate." |
| pharmacy.have[0] | VERIFIED | NHS.UK: pharmacists advise on minor health concerns without an appointment; pharmacies dispense POMs and sell dressings, analgesics, ORS and inhalers. | — |
| pharmacy.have[1] | PARTLY | Typical of larger pharmacies; not a required stock list. | "Many pharmacies also stock baby formula, nappies…" |
| pharmacy.have[2] | PARTLY | Uncontroversial but unsourced. Materially, without power a pharmacy usually cannot access its patient medication record and may be unable to dispense safely at all. | "Without power the till, card machine and the pharmacy's own patient records go down, so it may not be able to dispense at all." |
| pharmacy.have[3] | VERIFIED (incomplete) | https://www.england.nhs.uk/long-read/launch-of-nhs-pharmacy-first-advanced-service/ — launched 31 January 2024 covering sinusitis, sore throat, earache, infected insect bite, impetigo, shingles and uncomplicated UTI in women; it also includes urgent repeat medicine supply. | Add: "Scotland has NHS Pharmacy First Scotland, Wales and Northern Ireland have their own common-ailments schemes." |
| pharmacy.have[4] | WRONG — unsafe | Diabetes UK: the insulin you are using "can be kept at room temperature (under 25ºC)" (https://www.diabetes.org.uk/guide-to-diabetes/teens/me-and-my-diabetes/getting-my-glucose-right/insulin/storage); insulin in use is good for about 28 days out of the fridge. The claim could make a reader throw away usable insulin. | "Insulin in use is fine at room temperature (below 25°C) for about 28 days — do not throw it away after a power cut. Vaccines and some other fridge lines are the stock that is lost." |
| pharmacy.useful[0] | VERIFIED | https://www.legislation.gov.uk/uksi/2012/1916/regulation/225 — emergency supply at the patient's request where there is immediate need and obtaining a prescription would cause undue delay. | Add the limits: up to 30 days for most POMs; 5 days for Schedule 4/5 controlled drugs; smallest pack for insulin, inhalers, creams; a full cycle for oral contraceptives; phenobarbital for epilepsy is the only Schedule 1–3 exception. |
| pharmacy.useful[1] | VERIFIED | Pharmacy First covers infected insect bite, impetigo, shingles, sore throat, sinusitis, earache and UTI (NHS England, above); pharmacists advise on rashes, burns and coughs. | — |
| pharmacy.useful[2] | UNSUPPORTED | No source on stock behaviour in a blackout. | "Go while the pharmacy still has power — it may not be able to dispense once systems are down." |
| pharmacy.useful[3] | PARTLY | Same as expect[s4] — a prescriber, not the pharmacy, decides quantity. | See expect[s4]. |
| pharmacy.avoid[0] | UNSUPPORTED | Plausible generalisation; nobody authoritative states it. | "Deliveries may have stopped and shelves may be bare — ring ahead if you can." |
| pharmacy.avoid[1] | PARTLY WRONG | You may lawfully collect another person's dispensed prescription (and `pharmacy.approach[4]` tells readers to do exactly that) — the two bullets contradict each other. "Never buy prescription drugs off anyone" is sound (MHRA #FakeMeds). | "You can collect a prescription for someone else, but never take or buy someone else's medicine for yourself, and never buy prescription drugs off a person or an unregistered website." |
| pharmacy.avoid[2] | UNSUPPORTED | No authoritative source on pharmacies as looting targets. | "Do not travel to a pharmacy through public disorder." |
| pharmacy.avoid[3] | PARTLY | Consistent with UKHSA respiratory-infection advice on keeping people at higher risk away from crowded indoor settings. | "Leave a frail or very young household member at home rather than in a queue indoors." |
| pharmacy.approach[0] | PARTLY | See expect[s3] — cash only relevant in England. | See expect[s3]. |
| pharmacy.approach[1] | UNSUPPORTED | "Ask for the pharmacist by name" has no basis and may read as pressuring staff. | "Ask to speak to the pharmacist rather than the counter assistant." |
| pharmacy.approach[2] | PARTLY | Sensible and consistent with reg 225's requirement that the pharmacist establish the dose and need. | — |
| pharmacy.approach[3] | PARTLY WRONG | Quantity is set by reg 225 and clinical judgement (30 days, 5 days for Sch 4/5 CDs, smallest pack for insulin/inhalers/creams, full cycle for oral contraceptives), not by what the patient asks for; an under-supply can be unsafe. | "Take whatever quantity the pharmacist judges safe — the law sets limits and they may already be giving you less than a month." |
| pharmacy.approach[4] | VERIFIED | NHS.UK: someone else can collect your prescription on your behalf. | — |

## gp — GP surgery

| tag | verdict | evidence (URL + supporting sentence) | suggested wording |
|---|---|---|---|
| gp.expect[s1] | WRONG | CQC GP mythbuster 69 (https://www.cqc.org.uk/guidance-providers/gps/gp-mythbusters/gp-mythbuster-69-business-continuity-arrangements-emergencies-major-incidents): practices "should ensure they have identified core, essential services and can maintain these" through disruption; planning should "continue to provide a service to the population you serve". Practices stayed open through the pandemic. | "A GP surgery may close its building or move to another site in an emergency, so ring or check the door notice before walking there." |
| gp.expect[s2] | PARTLY | 111 in England (https://www.nhs.uk/nhs-services/urgent-and-emergency-care-services/when-to-use-111/); NHS 24 on 111 in Scotland "day and night" (https://www.nhs24.scot/111/); 111 across all seven Welsh health boards since 2022 (https://www.gov.wales/111-service-now-available-across-wales). NI has no 111: it uses **Phone First** (Mon–Fri 8am–6pm, trust-specific numbers) plus GP out-of-hours (https://www.northerntrust.hscni.net/services/emergency-departments/phone-first-frequently-asked-questions/). | "…Northern Ireland has no 111: ring your GP practice in hours, your trust's Phone First number before going to an emergency department, and the GP out-of-hours number at night and at weekends." |
| gp.expect[s3] | VERIFIED | https://www.gov.uk/guidance/999-and-112-the-uks-national-emergency-numbers — 999 and 112 both reach the UK emergency services. | — |
| gp.expect[s4] | PARTLY — potentially unsafe | 999 calls are carried by any available mobile network (emergency roaming) and work without credit; landlines often work in a power cut. Telling readers "none of those numbers connect" may stop someone trying 999. | "If your own network is down, still try 999 — a mobile will use any network it can find, and it works without credit or a SIM." |
| gp.have[0] | VERIFIED | Resuscitation Council UK primary-care standards (https://www.resus.org.uk/library/quality-standards-cpr/primary-care-equipment-and-drug-lists): an AED must be "available for immediate use"; dispensing practices exist in rural areas. | — |
| gp.have[1] | WRONG | General practice records are held on electronic clinical systems; paper Lloyd George records have been withdrawn/digitised. There is no reliable paper fallback. | "Records are electronic. If the computers are down the practice may not be able to see your record at all — bring your own list." |
| gp.have[2] | VERIFIED | Practices must tell patients how to access out-of-hours care; the line diverts and the building is locked outside surgery hours. | — |
| gp.have[3] | VERIFIED | A GP practice is not an inpatient or emergency facility (CQC GP guidance, above). | — |
| gp.useful[0] | VERIFIED | Routine and same-day in-hours general practice covers wound review, repeat prescriptions and fit notes. | — |
| gp.useful[1] | PARTLY | CQC mythbuster 69 expects practices to plan communication with patients; a door notice is common practice but not mandated. | "Look for a door notice — many practices post where they have moved to and which numbers still answer." |
| gp.useful[2] | VERIFIED — good safety point | Abrupt steroid withdrawal is dangerous and epilepsy/insulin interruptions are urgent; the pharmacy emergency-supply route (reg 225) may be faster out of hours. | Add: "if the surgery is shut, a pharmacy can often make an emergency supply." |
| gp.avoid[0] | WRONG | Duplicate of expect[s1]; same correction. | See gp.expect[s1]. |
| gp.avoid[1] | PARTLY | Correct steer, but practices hold AEDs and emergency drugs, so a collapse at the surgery door is not a reason to leave. | "For anything life-threatening call 999 rather than travelling to the surgery." |
| gp.avoid[2] | UNSUPPORTED | Generalisation about premises; no source. | "Outside surgery hours the building is usually locked and unstaffed." |
| gp.approach[0] | PARTLY | Same as expect[s2]. | See gp.expect[s2]. |
| gp.approach[1] | PARTLY | Sensible; the NHS number is not required to be seen. | "…your medicines list and any letters (your NHS number helps but is not needed)." |
| gp.approach[2] | UNSUPPORTED | Practices have no duty to share business continuity plans with patients. | "Ask where the practice will work from if it has to close, and write it down." |
| gp.approach[3] | UNSUPPORTED — security risk | No source, and leaving your name and home address on a locked door in a crisis is poor advice. | "If nobody answers, use the number on the door — do not leave your address on the premises." |

## clinic — Walk-in or urgent treatment centre

| tag | verdict | evidence (URL + supporting sentence) | suggested wording |
|---|---|---|---|
| clinic.expect[s1] | VERIFIED | https://www.nhs.uk/nhs-services/urgent-and-emergency-care-services/when-to-visit-an-urgent-treatment-centre/ — "sprains and strains, suspected broken bones, injuries, cuts and bruises…"; "you can often get tests like an ECG, blood tests or an X-ray". | — |
| clinic.expect[s2] | VERIFIED | https://www.england.nhs.uk/long-read/urgent-treatment-centres-principles-and-standards/ — UTCs manage conditions "urgent but not life or limb threatening", with protocols for transferring "critically ill and injured adults and children who arrive at a UTC unexpectedly". | — |
| clinic.expect[s3] | WRONG (for UTCs) | Same source — "UTCs must be open for a minimum of 12 hours a day, 7 days a week, including bank holidays", and the standard has no routine-closure provision. True only of some older walk-in centres and minor injuries units. | "Urgent treatment centres must open at least 12 hours a day, every day; walk-in centres and minor injuries units vary and some close early. Check before a long walk." |
| clinic.expect[s4] | UNSUPPORTED | No source supports a blanket "treat what you can at home first" ahead of triage. | "If you are not sure, use 111 (or NI: Phone First) before you set out." |
| clinic.have[0] | PARTLY | UTC standards: "Access to bedside diagnostics and plain X-ray facilities must be available throughout the UTC opening hours" — but many walk-in centres have no X-ray at all. | "Urgent treatment centres have X-ray during opening hours; many walk-in centres do not." |
| clinic.have[1] | PARTLY | UTC standards: "An appropriately trained multidisciplinary clinical workforce must be deployed whenever the UTC is open", led by a GP, ED consultant or senior clinical lead. "Strong painkillers" overstates — controlled-drug analgesia is limited. | "Nurses, paramedics and GPs who can close a wound, strap a sprain and give pain relief." |
| clinic.have[2] | UNSUPPORTED | No national standard requires standby power at a UTC, walk-in centre or MIU; the "generator at some units" claim has no source. | "Basic waiting facilities. Do not count on the lights staying on — most of these units have no standby generator." |
| clinic.have[3] | WRONG | Contradicted by the 12-hour/7-day UTC standard (above). | See clinic.expect[s3]. |
| clinic.useful[0] | VERIFIED | UTC standards list wound closure and minor head and eye injuries; NHS.UK lists suspected broken bones and injuries. | — |
| clinic.useful[1] | VERIFIED | UTC standards: designed to treat urgent but not life- or limb-threatening problems and divert from ED. | — |
| clinic.useful[2] | PARTLY — unsafe element | Sprains and cuts, yes. Hypothermia is not a UTC condition — moderate/severe hypothermia needs 999/A&E. | "…for the sprains and cuts that follow the clean-up. If someone is cold, shivering and confused, call 999." |
| clinic.avoid[0] | VERIFIED | UTC standards require onward transfer of critically ill patients; NHS.UK routes chest pain, stroke, severe bleeding and breathing difficulty to 999/A&E. | Say explicitly "call 999" rather than "are sent on". |
| clinic.avoid[1] | PARTLY | Reasonable for walk-in centres/MIUs; overstated for UTCs, which must open 12h/day, 7 days. | "Check it is open before a long walk — walk-in centres and minor injuries units keep varying hours." |
| clinic.avoid[2] | PARTLY WRONG | UTCs must be open a minimum of 12 hours a day and some are 24-hour; "most units are closed" overnight is not accurate across the category. | "Many units close in the evening — but some urgent treatment centres are open late or around the clock. Check first." |
| clinic.approach[0] | UNSUPPORTED | Sensible planning advice, no source. | Keep as a tip. |
| clinic.approach[1] | PARTLY — unsafe element | Standard pre-anaesthetic/sedation advice is not to eat or drink if a fracture may need manipulation or an injury may need sedation. | "Take the medicines list, a warm layer and water. Do not eat if the injury may need setting or stitching under sedation." |
| clinic.approach[2] | PARTLY | Reasonable, except a child under 16 must be accompanied by someone with parental responsibility to consent to treatment. | "Bring the injured person, not the household — but a child must come with a parent or guardian." |
| clinic.approach[3] | VERIFIED — strengthen | NICE NG232 head injury: anyone on anticoagulants with a head injury needs a CT head within 8 hours, which a UTC cannot provide. | "Say if anyone is on anticoagulants — with a head injury that means A&E, not a walk-in centre." |

## Summary

| verdict | count |
|---|---|
| VERIFIED | 21 |
| PARTLY | 37 |
| UNSUPPORTED | 18 |
| WRONG | 7 |
| **Total claims checked** | **83** |

### The five most important corrections

1. **`pharmacy.have[4]` — insulin (WRONG, unsafe).** Insulin in use is fine at room temperature below 25°C for about 28 days (Diabetes UK). Telling readers it "spoils once the power has been off a while" could make a diabetic discard usable insulin in a blackout. Rewrite so only vaccines and genuinely cold-chain lines are described as lost.
2. **`gp.expect[s4]` — "none of those numbers connect" (PARTLY, unsafe).** 999 calls roam onto any available mobile network and work with no credit or SIM. Readers must be told to try 999 anyway rather than assuming it is dead.
3. **`clinic.expect[s3]`, `clinic.have[3]`, `clinic.avoid[2]` — opening hours (WRONG).** NHS England requires urgent treatment centres to open "a minimum of 12 hours a day, 7 days a week, including bank holidays". The card's "short hours, shorter in an emergency, closed overnight" framing may send someone to A&E unnecessarily. Separate UTCs from walk-in centres/MIUs.
4. **`gp.expect[s1]` / `gp.avoid[0]` — "first to close, last to reopen" (WRONG).** CQC requires practices to identify and maintain core essential services through disruption. Replace with "may close its building or move site — ring or check the door notice".
5. **`hospital.have[0]`, `have[4]`, `have[5]` — hospital as generator-backed shelter (PARTLY/UNSUPPORTED, unsafe).** Fuel is typically 48–72 hours, not open-ended, and hot drinks/warm waiting rooms are not a hospital function: shelter and refreshment are a local-authority rest-centre role under the government's Evacuation and Shelter Guidance. As written these bullets invite people to walk to A&E for warmth, which `hospital.avoid[0]` correctly forbids.

### Other safety/legal flags

- `pharmacy.avoid[1]` contradicts `pharmacy.approach[4]`: collecting a prescription for someone else is lawful and encouraged.
- `pharmacy.approach[3]` ("ask for a week rather than a month") invites an under-supply; quantity limits are fixed by reg 225 HMR 2012 and clinical judgement.
- `pharmacy.have[3]` should name the Scottish, Welsh and NI equivalents, not only England's Pharmacy First.
- `gp.approach[3]` advises leaving your name and home address on a locked door — a security risk in a crisis.
- `clinic.approach[1]` ("something to eat while you wait") conflicts with nil-by-mouth before sedation for fractures and wound closure.
- `hospital.approach[1]` implies ID is needed; NHS emergency care is free at the point of use and does not require ID.
