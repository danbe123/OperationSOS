# Situational passages, playbooks/pages — fact-check report

Checked 2026-09-07 against NHS.UK, FSA/gov.uk, the UK CMOs' national power outage scripts (Dec 2025), DWI, UKHSA,
legislation.gov.uk, CPS, HSE (INDG231, GS6), SSEN/ENA/Ofgem, Ofcom/Prepare, NFCC, Met Office, MREW, RNLI,
Environment Agency, Countryside Code, RSGB, NOAA SWPC and the National Risk Register 2025 (full PDF read).
117 passages, 29 pages. `(else)` marks the false branch of an `{{#if}}`.

## amateur-bands

| branch | verdict | evidence | suggested wording |
|---|---|---|---|
| scenario:solar-storm | VERIFIED | NRR 2025 p.137: impacts include "loss or disruption of… some telecommunications (for example satellite communications and high frequency radio)". VHF/UHF do not rely on the ionosphere. | — |
| unless mobile | VERIFIED | Ofcom Amateur Radio Licence (OFW611, Feb 2024) cond. 6(5): the licensee may assist with communications "in times of disaster or local, national, international emergency" or "to support operations conducted by a user service". Listening needs no licence (Wireless Telegraphy Act 2006 s8 licenses transmitting, not reception). RAYNET is tasked through the emergency services and local-authority planners, not by the public (raynet-uk.net/faqs). RSGB 2026 band plan confirms 145.500 and 433.500 MHz FM calling. | — |
| unless internet | VERIFIED | Operational instruction; consistent with the page's own band table. | — |
| scenario:emp | UNSUPPORTED | No primary source obtainable for handheld/metal-tin EMP survivability. | "Nobody can tell you in advance what survived — test on receive first, and treat anything that was plugged into the mains or an outside aerial as a likely loss." |

## butchery

| branch | verdict | evidence | suggested wording |
|---|---|---|---|
| unless water | PARTLY | Tularaemia does pass through broken skin when skinning hares/rabbits, but it is not endemic in Great Britain — confirmed indigenous cases are very rare. The 30 m burial distance is humanitarian (Sphere/WHO) practice, not UK guidance. | "…gloves matter more than ever (tularaemia, rare in Britain but caught through cuts when skinning hares)…" |
| unless power | PARTLY | Directionally right and consistent with FSA chilling principles, but no primary UK source states the "kill only what you eat that day" rule. | — |
| scenario:heat-drought | PARTLY | FSA benchmark is 70 °C for 2 minutes (equivalents 75 °C/30 s, 80 °C/6 s) — https://www.gov.uk/government/publications/cooking-your-food/cooking-your-food. Trichinella dies at ~63–71 °C, so 74 °C is safe but is not the FSA figure. | "Cook right through: 70 °C held for two minutes, or 75 °C for thirty seconds." |

## chronic-conditions

| branch | verdict | evidence | suggested wording |
|---|---|---|---|
| unless shops | VERIFIED | Consistent with steroid/AED/anticoagulant withdrawal guidance; "never halve a dose without advice" follows from all of it. | — |
| unless phones | VERIFIED | Human Medicines Regulations 2012 reg. 225 — pharmacist emergency supply at patient request: 30 days' treatment, 5 days for Sch. 4/5 CDs, insulin and inhalers "smallest available pack". https://www.legislation.gov.uk/uksi/2012/1916/regulation/225 | Add "ask for an *emergency supply* by name — a pharmacist can give up to 30 days". |
| scenario:pandemic | VERIFIED | Sick-day rules: "If you cannot keep tablets down… you must take an intramuscular injection of hydrocortisone 100 mg" (Society for Endocrinology / ADSHG). Metformin: stop after ≥2 episodes of vomiting/diarrhoea. Lithium toxicity on dehydration (nhs.uk/medicines/lithium). | — |
| scenario:supply-chain | **WRONG — unsafe and unlawful** | MHRA's Category 1/2/3 system covers switching *manufacturers of the same drug*, never one AED for another. Under reg. 225 a pharmacist may only supply the *same* medicine previously prescribed; drug-for-drug AED substitution needs a prescriber or a national Serious Shortage Protocol, and none has ever covered AEDs. | Delete the phenobarbital/phenytoin example. "If your epilepsy medicine runs short, do not accept a different one: a pharmacist can give an emergency supply of the same drug, and only a prescriber can change it. Get to a GP, neurology team or 111 before the last packet." |
| scenario:famine | VERIFIED | Gliclazide "take with or just before a meal"; skipping food raises hypo risk (nhs.uk/medicines/gliclazide). Lithium and dehydration as above. Abrupt steroid/AED/anticoagulant withdrawal is dangerous. | — |
| unless power | PARTLY | Home-oxygen contingency guidance is: use the back-up cylinder **at the flow your clinician prescribed** and ring the supplier's 24-hour line — not titrate it yourself. NHS: keep oxygen "at least 3 metres" from any open flame. Kidney Care UK's primary message for a dialysis power cut is contacting the renal unit, not diet alone. The passage also omits the page's own insulin point. | "Switch the oxygen patient to their back-up cylinder at the flow rate on their prescription and send word to the oxygen supplier's 24-hour line; keep the cylinder 3 metres from any flame. On dialysis, get word to the renal unit while keeping strictly to the renal diet and fluid limit. The insulin already in use is fine — see below; do not throw it away because the fridge is off." |

## death-and-grief

| branch | verdict | evidence | suggested wording |
|---|---|---|---|
| if phones | VERIFIED | Coroners and Justice Act 2009 s1: coroner must investigate a death that is violent, unnatural or of unknown cause. https://www.legislation.gov.uk/ukpga/2009/25/section/1 | — |
| if phones (else) | VERIFIED | Reasonable operational advice; consistent with the coroner duty above. | — |
| scenario:pandemic | VERIFIED | The "bodies do not start epidemics" position is settled WHO/PAHO consensus; the exception is a death from an actively contagious disease, which the passage already handles with PPE. | — |
| unless phones | PARTLY | gov.uk: "Register the death within 5 days (8 days in Scotland)… of getting the confirmation" — since Sept 2024 the clock runs from the medical examiner's confirmation, not the death. Scotland has no coroner: the procurator fiscal investigates. https://www.gov.uk/after-a-death | "…the five days in England and Wales, which run from the medical examiner's confirmation, or the eight in Scotland… tell the police in person (in Scotland the death goes to the procurator fiscal)." |
| scenario:long-rebuild | PARTLY — legal caveat needed | Burial on private land is lawful in principle but a sudden/unexplained death must still reach the coroner, and moving a body later normally needs a Ministry of Justice exhumation licence (Burial Act 1857 s25). EA guidance keeps graves well away from water (commonly 10 m from a watercourse, 30 m from a spring/well/borehole — figure not verifiable live). | Add: "This is a last resort only where no authority can be reached. Report the death and the grave to the police or registrar at the first opportunity — moving a body later needs a licence, not just a spade." |

## fieldcraft-basics

| branch | verdict | evidence | suggested wording |
|---|---|---|---|
| if dark | PARTLY | MREW Fact File 6 supports stopping and sheltering and letting the slowest set the pace; no primary source for "half the distance you planned". | — |
| unless roads | VERIFIED | MREW: "Leave details of your route plan — include start and finish points, estimated time of return and contact details." | — |
| scenario:severe-winter | VERIFIED | MREW: be prepared to turn back if conditions turn against you; allow the slowest member to set the pace. | — |

## fieldcraft-fire

| branch | verdict | evidence | suggested wording |
|---|---|---|---|
| unless power | VERIFIED | Craft guidance consistent with the cited Kephart chapters; nothing unsafe. | — |
| if dark | VERIFIED | NHS: "do not use a barbecue or camping stove indoors or inside a tent". https://www.nhs.uk/conditions/carbon-monoxide-poisoning/ | — |
| scenario:heat-drought | VERIFIED | Countryside Code: "Do not light fires and only have BBQs where signs say you can… Always put your BBQ out, make sure the ashes are cold." | — |
| unless gas | VERIFIED | NHS CO guidance as above; lid-and-windshield fuel saving is uncontroversial. | — |
| scenario:severe-winter | VERIFIED | n-butane b.p. −1 to 1 °C; isobutane −11.78 °C. | — |

## fieldcraft-fishing

| branch | verdict | evidence | suggested wording |
|---|---|---|---|
| unless shops | VERIFIED | gov.uk: a rod licence is needed only "for salmon, trout, freshwater fish, smelt or eel" — shore sea angling needs none. https://www.gov.uk/fishing-licences | — |
| scenario:storms-flooding | PARTLY | gov.uk: "Flood water may contain sewage and hide rubbish, wreckage… broken drain and manhole covers." Leptospirosis incubation is 5–14 days, occasionally to 30 — "about a week later" understates the tail, and the cited UKHSA flooding page does not in fact mention leptospirosis. | "…which usually starts like flu one to two weeks later, sometimes as much as a month." Re-point the citation to NHS leptospirosis. |
| unless power | VERIFIED | Histamine in scombroid fish "is not destroyed by normal cooking temperatures". | — |
| unless sewage | PARTLY | FSA grades shellfish waters on faecal indicators precisely because of sewage; oysters are a named norovirus vector. The estuary/outfall wording is not an FSA quote. | — |

## fieldcraft-food

| branch | verdict | evidence | suggested wording |
|---|---|---|---|
| unless shops | VERIFIED | Standard, conservative foraging rule; nothing to correct. | — |
| scenario:famine | PARTLY | Oenanthe crocata is extremely toxic (9 of 13 recorded UK cases 1900–1978 fatal) and grows in wet ditches; the classic confusion is the **root for parsnip**, and "most poisonous plant in Britain" is a popular superlative rather than a sourced ranking. | "…one of the most poisonous plants in Britain… whose root has been eaten in mistake for parsnip." |
| if phones | VERIFIED | Correct triage for suspected plant poisoning. | — |
| if phones (else) | VERIFIED | Taking the sample is standard toxicology advice. | — |

## fieldcraft-hygiene

| branch | verdict | evidence | suggested wording |
|---|---|---|---|
| unless sewage | PARTLY — diverges from UK guidance | The UK CMOs' water and sanitation script tells households: "You will not be able to flush the toilet… collect your poo in plastic bags, which should be sealed and disposed of with normal household waste." The 30 m deep-pit rule is field/humanitarian practice, wrong for a terraced street. | "In a house, bag and seal it and put it out with the household waste, as the CMOs advise; the deep pit 30 m from any well or watercourse is for camps and rural ground." |
| unless water | VERIFIED | CMO script: "Washing your hands with soap and water is more effective at killing all germs than hand sanitiser." NHS: "alcohol hand gels do not kill norovirus." | — |
| scenario:pandemic | VERIFIED | Separate carer/food handler, own utensils, hand hygiene after every contact — standard infection-control practice. | — |
| scenario:storms-flooding | **WRONG on tins** | FSA: "you can keep food which is in water resistant packaging including undamaged metal cans"; discard only "food in packaging with screwcaps, snap lids, pull tops, crimped or metal caps" and "crushed/dented/swollen cans". https://www.gov.uk/government/publications/food-safety-after-a-flood-consumer-advice | "Wash the outside of undamaged metal cans and keep them; throw away anything in porous packaging, anything with a screwcap, snap lid or pull top, and any can that is dented, crushed or swollen." |

## fieldcraft-moving

| branch | verdict | evidence | suggested wording |
|---|---|---|---|
| scenario:storms-flooding | VERIFIED | gov.uk: "Do not walk or drive through flood water… hide rubbish, wreckage, uneven roads and pavements or broken drain and manhole covers." | — |
| if dark | PARTLY | Linear-feature navigation and a shorter night pace count are standard; no primary source for the torch/compass deflection distance. | — |
| scenario:severe-winter | VERIFIED | Consistent with MREW winter advice and the shortened snow pace count. | — |
| unless roads | **WRONG — legal** | gov.uk rights of way: a public footpath is "for walking, running, mobility scooters or powered wheelchairs"; bicycles are lawful only on bridleways ("walking, horse riding, bicycles…"), restricted byways and byways. https://www.gov.uk/right-of-way-open-access-land/use-public-rights-of-way | "Bridleways, byways, towpaths and disused railways take wheels — a barrow, a pram, a bicycle or a sledge. A public footpath is for feet: do not plan a cycle route along one." |

## fieldcraft-navigation

| branch | verdict | evidence | suggested wording |
|---|---|---|---|
| unless power | VERIFIED | Sound; paper map and baseplate compass need no power. | — |
| if dark | PARTLY | Polaris sits about 0.66° from the true pole — near-north, not exact. Compass deflection by a torch is real but no sourced distance was found. | "Polaris gives north to within a degree when the compass is lost." |
| scenario:severe-winter | VERIFIED | Bearing-and-pace with a catching feature is standard whiteout technique; stride does shorten in deep snow. | — |

## fieldcraft-rescue

| branch | verdict | evidence | suggested wording |
|---|---|---|---|
| unless roads | PARTLY | Saying the road is blocked and where a vehicle can reach is sound; the flat/clear/weighted landing-site advice matches the page's own helicopter section but no primary UK source was retrievable. | — |
| scenario:storms-flooding | PARTLY | RNLI: "Throw it to them. Stay safe: do not enter the water yourself" — reach-or-throw VERIFIED. The fire-service-inland / coastguard-on-the-shore split is standard 999 triage but is not stated on the cited gov.uk flood page. | — |
| if dark | PARTLY — safety omission | MREW Fact File 6: "Six good long blasts in a minute. Stop for one minute. Repeat… don't stop because you hear a reply." The "reply is three" figure is traditional but not in MREW's text. The passage also drops the base page's own caveat about not pointing a torch into the cockpit. | "…hold a steady torch on an approaching helicopter until the crew have seen you, never into the cockpit, then switch it off." |

## fieldcraft-rope-tools

| branch | verdict | evidence | suggested wording |
|---|---|---|---|
| if dark | VERIFIED | Sound craft and injury-prevention advice; nothing to correct. | — |
| unless shops | VERIFIED | Consistent with the cited sharpening guide. | — |
| scenario:long-rebuild | VERIFIED | Traditional cordage materials; nothing unsafe. | — |

## fieldcraft-shelter

| branch | verdict | evidence | suggested wording |
|---|---|---|---|
| scenario:storms-flooding | VERIFIED | Consistent with EA/gov.uk flood advice to move to higher ground and off flood plains. | — |
| if dark | VERIFIED | Sound; insulation-first is correct priority. | — |
| scenario:severe-winter | VERIFIED | Insulate below first, keep an air hole in any snow shelter, dry sleeping clothes — standard cold-weather doctrine. | — |
| unless heating | VERIFIED | CMO warmth script: "Get everyone in the house to gather in one room to share warmth"; "wear several thin layers"; babies, young children, older people "at particular risk from cold weather". NHS hypothermia signs include tiredness and confusion. | Add the NHS list (shivering, pale cold skin, slurred speech) alongside "clumsiness and unusual quiet". |

## fieldcraft-water

| branch | verdict | evidence | suggested wording |
|---|---|---|---|
| unless water | PARTLY | DWI confirms private supplies are not treated to mains standards; the four-pathogen list is correct in substance but is not a verbatim DWI consumer-page list. | — |
| scenario:storms-flooding | VERIFIED | DWI: "Cryptosporidium poses a challenge to water treatment, because of its small size and resistance to chlorine." https://dwi.gov.uk/consumers/learn-more-about-your-water/cryptosporidium/ | — |
| scenario:nuclear-war | PARTLY | NWSS: "Settling is one of the easiest methods to remove most fallout particles from water" — but settling removes *particulate* fallout only, not dissolved activity. | "…let it stand at least six hours, pour off the clear water — that takes out the particles, not anything dissolved — and then treat it for microbes." |
| scenario:nuclear-accident | VERIFIED | NWSS: "neither fallout particles nor dissolved radioactive elements or compounds can be removed from water by chemical disinfection or boiling." Milk/radioiodine was the controlling pathway at Windscale. | — |

## fieldcraft-weather

| branch | verdict | evidence | suggested wording |
|---|---|---|---|
| if dark | PARTLY | Falling glass and a backing wind as rain signs are conventional and uncontroversial, but unsourced against the Met Office. | — |
| scenario:severe-winter | PARTLY | Met Office: Force 8 = "Gale", 34–40 knots. The "twigs break off trees / cannot walk into the wind" line is the classic Beaufort **land** description, which the Met Office's public page does not carry. | "Force 8, a gale at 39 to 46 mph, means get off the hill." |
| scenario:storms-flooding | VERIFIED | RNLI: cold water shock happens "anything below 15 °C… you lose control of your breathing"; Float to Live — "Tilt your head back… relax and control your breathing… move your hands and legs to help you stay afloat." | — |
| scenario:heat-drought | VERIFIED | Met Office July 2022 report: "On 19th, 40.3 °C was recorded at Coningsby (Lincolnshire), setting a new UK and England temperature record". NHS heatstroke: "hot skin without sweating… confusion and restlessness… loss of consciousness" — a medical emergency. | Optionally name Coningsby. |

## food-storage

| branch | verdict | evidence | suggested wording |
|---|---|---|---|
| unless power | PARTLY | FSA and the CMO food script both give exactly 4 hours / 48 hours full / 24 hours half full. But FSA: "you can freeze food again once cooked, but you'll only be able to reheat it once after that" — so a flat "do not refreeze" is stricter than the rule and wastes food. | "Cook what has thawed thoroughly; you can refreeze it once it is cooked, but only reheat it once after that. Do not refreeze raw thawed food." |
| unless shops | VERIFIED | Rationing to a counted figure rather than appetite; sound. | — |
| scenario:heat-drought | PARTLY | USDA: "Temperatures below 85 °F [≈29 °C] are best"; "High temperatures (over 100 °F [≈38 °C]) are harmful to canned goods". There is no 32 °C threshold in the guidance. | "…tins keep longest below about 29 °C and are harmed above about 38 °C, and should never be frozen." |

## foraging-law

| branch | verdict | evidence | suggested wording |
|---|---|---|---|
| unless shops | VERIFIED | Theft Act 1968 s4(3): picking wild mushrooms, flowers, fruit or foliage "does not… steal what he picks, unless he does it for reward or for sale or other commercial purpose" (England and Wales). WCA 1981 s13(1)(b): "not being an authorised person, intentionally uproots any wild plant not included in that Schedule" — separate E&W and Scotland versions, i.e. Great Britain. | — |
| scenario:famine | PARTLY | WCA s13(1)(a) and Schedule 8 verified. Snares: banned in Wales (Agriculture (Wales) Act 2023 s46, 17 Oct 2023) and Scotland (Wildlife Management and Muirburn (Scotland) Act 2024 s6, 25 Nov 2024); free-running snares remain lawful in England. But bird protection is not absolute — Schedule 2 quarry species in season and general licences are real exceptions, and Northern Ireland runs on the Wildlife (NI) Order 1985. | "Wild birds, their nests and their eggs are protected throughout the UK unless a close-season quarry species, a general licence or an individual licence applies." |
| scenario:long-rebuild | VERIFIED | Deer Act 1991 s2 close seasons; Game Act 1831; EA byelaw close seasons. | — |

## household-plan

| branch | verdict | evidence | suggested wording |
|---|---|---|---|
| unless roads | VERIFIED | Sound planning advice; nothing to correct. | — |
| if phones | VERIFIED | Standard out-of-area contact practice. | — |
| if phones (else) | VERIFIED | Correct: without phones the address is the operative detail. | — |
| unless power | VERIFIED | FSA/CMO 4 h / 48 h / 24 h as above. Ofgem PSR eligibility explicitly includes "conditions that mean you need to use medical equipment that requires a power supply". | — |
| unless heating | VERIFIED | CMO warmth script, one warm room and layered clothing; "Do not use camping stoves and barbecues indoors as there is a risk of carbon monoxide poisoning, which can kill." | — |
| unless water | PARTLY | Prepare: "A minimum of 2.5–3 litres of drinking water per person per day"; but "10 litres per person per day will make you more comfortable by also providing for basic cooking and hygiene needs". The CMO script says drink at least 2 litres a day. Planning at 3 L under-counts washing and cooking. | "…how many days that is at 3 litres a person a day for drinking, and at 10 litres a head if you are also cooking and washing, which is the government's planning figure." |
| unless shops | VERIFIED | Prepare and the CMO scripts both assume cash; card readers and ATMs depend on the network. | — |

## infant-feeding

| branch | verdict | evidence | suggested wording |
|---|---|---|---|
| if power | VERIFIED | Trivially correct. | — |
| if power (else) | VERIFIED | NHS: never a barbecue or camping stove indoors or in a tent. | — |
| unless water | **WRONG — figure** | NHS: "Boil the water. Then leave the water to cool for no more than 30 minutes, so that it remains at a temperature of at least 70C" — the 70 °C claim is right. But NHS sterilising: "**Boil the feeding equipment in a large pan of water for at least 10 minutes**", not five. https://www.nhs.uk/conditions/baby/breastfeeding-and-bottle-feeding/bottle-feeding/sterilising-baby-bottles/ | "Boiling is also the steriliser: at least ten minutes in a covered pan, and check teats for cracks, because boiling damages them faster than other methods." |
| scenario:pandemic | PARTLY | NHS supports continuing to breastfeed through infection ("the benefits of breastfeeding and the protection it offers outweigh any risks"), verified for COVID specifically. Cup feeding and hand expressing when a mother is too ill are standard WHO/UNICEF practice but were not found on a live NHS/Baby Friendly consumer page. | Cite WHO/UNICEF infant feeding in emergencies for the cup-feeding line rather than implying an NHS source. |
| if phones | VERIFIED | Correct red-flag triage for a baby. | — |
| if phones (else) | VERIFIED | Correct fallback. | — |

## knife-firearms-law

| branch | verdict | evidence | suggested wording |
|---|---|---|---|
| scenario:civil-unrest | PARTLY — "never" too absolute | PCA 1953 s1 verified: an offensive weapon is "any article made or adapted for use for causing injury… or intended by the person having it with him for such use". CJA 1988 s139 verified, including the sub-3-inch non-locking folding-knife exception and the defendant's burden. CJIA 2008 s76(3) verified. But CPS guidance and case law treat fear for personal safety as *capable*, in rare and fact-specific circumstances, of amounting to good reason — it is not excluded as a matter of law. s76(5A) also adds the householder "grossly disproportionate" test the passage omits. | "Carrying a blade 'just in case', or out of a general fear of attack, is not a good reason in law and that defence very rarely succeeds. At home the law allows such force as is reasonable in the circumstances as you honestly believed them to be — and for a householder facing an intruder, only force that is grossly disproportionate is ruled out." |

## mains-electricity

| branch | verdict | evidence | suggested wording |
|---|---|---|---|
| unless power | VERIFIED — two additions | powercut105.com: "105 is a free service… from most landlines and mobile phones." CMO warmth script: site a generator "outdoors at least 6 metres or 20 feet away, with the exhaust facing away from windows or doors." SSEN: "Always leave a light on in your home so you know when the electricity has returned." | Add the 6 m generator distance, and note 105 covers England, Wales and Scotland — Northern Ireland is 03457 643643. |
| scenario:storms-flooding | VERIFIED — add distance | HSE INDG231: "electricity can flash over from overhead lines even though plant and equipment do not touch them." HSE GS6: "assume that the wires are live, even if they are not arcing or sparking"; lines "may be switched back on either automatically after a few seconds or remotely"; "if a live wire is touching the ground the area around it may be live." SSEN: keep "at least 10 metres" from power lines. | Add: "Stay at least 10 metres back, treat the ground near a fallen wire as live, and expect the line to switch itself back on without warning." |
| scenario:grid-collapse | PARTLY | The backfeed hazard is real and the transfer-switch requirement is right, but the technical rule is BS 7671 Section 551 (no paralleling with the public supply), not Approved Document P, which is a compliance framework and says nothing about backfeeding. No Ofgem source was found for the prepayment-meter top-up claim. | Cite BS 7671 §551 for the changeover requirement (Part P still governs notification), and soften the prepayment-meter sentence to "may need topping up". |

## no-phones

| branch | verdict | evidence | suggested wording |
|---|---|---|---|
| unless mobile | PARTLY — eCall overstated | Prepare: "emergency calls automatically roam onto any available network"; Wi-Fi calling and satellite texting (iPhone 14+ in the UK since Dec 2022) verified. But EU Reg. 2015/758 art. 7 applies eCall "with effect from 31 March 2018" only to **new types** of M1/N1 vehicles — many cars *built* after that date, on an older type approval, have no eCall. | "…and a car whose model was type-approved from spring 2018 dials 112 through any mast still standing — check whether yours actually has the SOS button." |
| unless landline | **WRONG on "no SIM"** | Prepare confirms roaming and the battery back-up unit ("your communication provider must provide a free back-up battery unit", at least an hour) — but the BBU is an entitlement for **vulnerable customers**, not every house, and the box contradicts itself on SIMs: fieldcraft-rescue says 999 works "but the phone must have a SIM in it". UK networks do not carry SIM-less emergency calls. | "Use a mobile, which reaches 999 on any network that has signal, with no credit — it does still need a SIM in it — or a neighbour's phone." Also say the free back-up battery is for vulnerable customers. |
| unless internet | PARTLY | Relay UK: "Dial 18000 instead of the normal 18001 through the app or from a textphone." From a textphone this runs over the phone network; the Relay UK **app** needs internet. | "…Relay UK on 18000 works from a textphone over the phone network, though the Relay UK app needs the internet." |
| unless power | **WRONG — optimistic** | Ofcom's RAN power-resilience work found only "around 20% of sites currently have at least 1 hour of backup… approximately 5% have at least 6 hours". So most masts have **less** than an hour, not "about an hour". NRR 2025 p.88 confirms the recovery route: mobile connections stay down "until mobile network operators deploy back-up generators to mobile cell sites". | "Only about a fifth of mobile masts hold an hour of battery and only a twentieth hold six, so the network starts failing within the hour and comes back only where operators can get generators to the sites." |

## pmr446

| branch | verdict | evidence | suggested wording |
|---|---|---|---|
| unless mobile | PARTLY — range optimistic | Ofcom IR 2030 verified: PMR446 "uses integral antennas only… 0.5W ERP maximum", 16 analogue channels. Ofcom publishes no range figures; technical literature puts dense-urban range at a few hundred metres, well under the "one to three kilometres in a town" claimed. Hilltop range of 10 km+ line-of-sight is realistic. | "Range is a few hundred metres among buildings, one to three kilometres in the open, and ten or more from a hilltop — which is why the set goes to the upstairs window or up the hill." |
| unless internet | VERIFIED | Ofcom designates no PMR446 calling channel; "channel 8, tone 16" is correctly described as informal and unmonitored. | — |
| scenario:emp | UNSUPPORTED | No primary source obtainable for EMP survivability of handhelds. The AA-cell logistics point is sound regardless. | Keep the AA-cell advice; drop or hedge the metal-tin survivability claim. |
| scenario:solar-storm | PARTLY — right claim, wrong citation | UHF's independence from the ionosphere is right (NOAA SWPC: flare X-rays black out HF on the sunlit side). The GPS-timing dependency is real — Blackett Review: "Telecoms companies need accurate time and phase to support 4G and 5G networks… most commonly derived from GNSS" — but it comes with a holdover clock, so degradation is gradual, and none of this is in the NRR the sibling page cites. | Cite the Blackett Review, and say the network "drifts" rather than fails outright on GPS loss. |

## solar-islanding

| branch | verdict | evidence | suggested wording |
|---|---|---|---|
| unless power | VERIFIED | SSEN's Distributed Generation Connection Guide (EREC G99): standard grid-tied generation "shall not disconnect from the distribution system… and transition to island mode" unless specifically designed and DNO-notified. Anti-islanding is a safety requirement, not a fault. | — |
| scenario:grid-collapse | VERIFIED | Battery University: LiFePO4 "Cycle life 2000 and higher"; datasheets commonly 3,000–6,000 to 80 %. | — |
| scenario:severe-winter | PARTLY — figure optimistic in the wrong direction | PVGIS (2005–2020) for London: ≈0.69 kWh/m²/day horizontal in December, ≈5.2 in July. A 1 kWp array at 35° south yields ≈**1.18 kWh/day** in December — not "well under 1 kWh". Only poorly oriented arrays fall to 0.5–0.8. | "…so a 1 kWp array gives roughly one kilowatt-hour a day in midwinter, less if it faces east or west, and a 100 W folding panel is realistically a phone charger." |

## ticks-adders

| branch | verdict | evidence | suggested wording |
|---|---|---|---|
| unless phones | PARTLY — safety omission | NHS snake bites: "Keep the part of your body that was bitten as still as you can", "Lie in the recovery position if you can" — stillness and hospital transport verified. But the passage omits the NHS's explicit don'ts: "Do not try to suck or cut the venom out of the bite", "Do not tie anything tightly round the part of the body where the bite is", "Do not take aspirin or ibuprofen". https://www.nhs.uk/conditions/snake-bites/ | Add: "Do not tie anything tightly round the limb, do not cut or suck the bite, and give paracetamol rather than aspirin or ibuprofen." |
| unless roads | VERIFIED | Antivenom is given intravenously in hospital, not in the field; planning the carry is correct. | — |

## uk-numbers

| branch | verdict | evidence | suggested wording |
|---|---|---|---|
| if phones | VERIFIED | Correct. | — |
| if phones (else) | VERIFIED | Prepare: emergency calls roam onto any available network, so "try 999 anyway" is right. | — |
| unless phones (runners) | **WRONG — "fire stations stay crewed"** | NFCC: on-call firefighters "cover emergencies across more than 90% of the United Kingdom" and "aren't based at fire stations but operate on standby… they carry a pager or alert device and must be able to get to the fire station within a specific time." On-call stations stand empty and are alerted by a control room that needs the network. Police front counters have also been cut hard (BBC: 73 nationally, down from 136 in 2013; the Met keeps one 24-hour counter per borough). | "Send the pair of runners to a fire, police or ambulance station — but know that many stations are on-call and stand empty between shouts, and that an empty station cannot be alerted without the network. Head for the largest, town-centre station you can reach, and for a hospital if it is a medical emergency." |
| unless internet | PARTLY | 999 by text needs prior registration, which the passage correctly assumes. Relay UK nuance as under no-phones: 18000 from a textphone is off-internet, the app is not. | Same Relay UK wording as above. |
| unless phones (utilities) | VERIFIED — one addition | Gas: get out, leave doors open, isolate at the meter if safely reachable — standard. Water companies do open bottled-water points. | Add the Northern Ireland power-cut number (03457 643643) beside 105. |

## water-disinfection

| branch | verdict | evidence | suggested wording |
|---|---|---|---|
| if power | VERIFIED | Boiling is the most reliable of the listed methods. | — |
| if power (else) | VERIFIED | CMO water script offers boiling *or* tablets, consistent with this. | — |
| unless water | PARTLY | DWI boil-water notice: boiled water "should be stored in a clean container, in the fridge" and "discarded if not used within 24 hours". "A day or two" is looser than the official figure. | "…use it within 24 hours, and re-treat anything that has stood in the warm." |
| scenario:storms-flooding | VERIFIED | DWI on Cryptosporidium's chlorine resistance, as above; boil-water notices are the DWI's own mechanism. | — |
| scenario:nuclear-war | PARTLY | Same as fieldcraft-water: settling removes particulate fallout, not dissolved activity. | Same addition. |
| scenario:nuclear-accident | VERIFIED | NWSS explicitly: neither disinfection nor boiling removes fallout particles or dissolved radioactivity. | — |

## what-still-works

| branch | verdict | evidence | suggested wording |
|---|---|---|---|
| if power | VERIFIED | Sound. | — |
| if power (else) | VERIFIED | Sound. | — |
| if shops | VERIFIED | Card readers and ATMs depend on the network. | — |
| if shops (else) | VERIFIED | As above. | — |
| scenario:grid-collapse | PARTLY | NRR 2025 p.45 (cyber attack on the NETS): "Full restoration could take up to 7 days" — VERIFIED. But rota disconnection is not part of this scenario: ESEC rotas "published up to 7 days in advance" appear under **failure of gas supply infrastructure** (p.93–94). | "…restoration over several days, up to seven; if the cause is a gas-supply failure instead, expect published rota disconnections on top." |
| scenario:emp | PARTLY | gov.uk: "Emergency alerts work on all 4G and 5G phone networks in the UK" and you get nothing "connected to a 2G or 3G network" — VERIFIED. "Expect cars to be mostly fine" and the metal-tin survivability claim have no obtainable primary source. | Hedge the car and metal-tin claims: "nobody can tell you in advance what survived." |
| scenario:solar-storm | **UNSUPPORTED — citation does not support the claim** | NRR 2025 p.137 lists impacts without ordering them: "regional power disruptions, loss or disruption of Global Navigation Satellite Systems… and some telecommunications (for example satellite communications and high frequency radio), disruption to aviation…". It does not mention payment systems, does not say GPS timing in mobile networks fails first, and nowhere "assumes" cash, paper records and a wind-up radio. | "The register expects regional power disruption, loss of GPS, and disruption to satellite communications and shortwave, all at once rather than in a tidy order — so a phone may show bars and still fail, while FM, PMR446 and the VHF and UHF amateur bands keep working." |

## Counts

| verdict | count |
|---|---|
| VERIFIED | 69 |
| PARTLY | 38 |
| UNSUPPORTED | 3 |
| WRONG | 7 |
| **Total passages checked** | **117** |

## The five most important corrections

1. **`chronic-conditions` — supply-chain, antiepileptic substitution (WRONG, unsafe and unlawful).** The passage tells a household to accept phenobarbital or phenytoin when lamotrigine or levetiracetam runs out. MHRA's switching categories cover different *manufacturers of the same drug*, never a different drug; under reg. 225 a pharmacist may only supply the same medicine previously prescribed. Swapping AED classes without titration risks status epilepticus. Delete the example and route the reader to a prescriber or 111.
2. **`infant-feeding` — unless water, "five minutes in a covered pan" (WRONG, figure).** The NHS requires feeding equipment to be boiled for **at least 10 minutes**. Halving the sterilising time for a formula-fed baby in a contaminated-water scenario is exactly the wrong direction of error. The 70 °C water rule in the same passage is correct.
3. **`uk-numbers` — unless phones, "fire stations stay crewed" (WRONG, unsafe).** On-call firefighters are not based at the station; they are paged from home, by a control room that needs the network. A large share of UK stations are on-call and stand empty. As written this sends a pair of runners on a long walk in an emergency to a locked door. Name the risk and steer readers to the largest town-centre station, or to a hospital for a medical emergency.
4. **`fieldcraft-hygiene` — storms-flooding, "throw away food and tins whose seals were under it" (WRONG, wasteful).** FSA: undamaged metal cans in floodwater can be washed and kept; what must go is porous packaging, screwcaps, snap lids, pull tops and crushed, dented or swollen cans. In a flood this is days of food.
5. **`fieldcraft-moving` — unless roads, footpaths "take wheels" (WRONG, legal).** A public footpath is for walking, running and mobility scooters only; bicycles are lawful on bridleways, restricted byways and byways. The passage as written plans an evacuation route that is a trespass.

## Other safety, legal and sourcing flags

- **`what-still-works` — solar-storm** attributes an ordered failure sequence, payment-system failure and a set of assumed fallbacks to NRR 2025 p.137. None of it is in the register. This is the clearest case in the set of a citation not supporting the sentence it is attached to.
- **`chronic-conditions` — unless power** tells households to ration oxygen to an oximeter target. The correct instruction is the back-up cylinder at the *prescribed* flow plus the supplier's 24-hour line; NHS also gives a concrete 3 m clearance from any flame. Add a cross-reference to the page's own (excellent) insulin section so nobody discards usable insulin when the fridge stops.
- **`fieldcraft-hygiene` — unless sewage** applies a camp latrine rule (deep pit, 30 m) to a household. The UK CMOs tell households to bag, seal and bin. Both belong, labelled for their setting.
- **`ticks-adders` — unless phones** omits the NHS's explicit don'ts for snake bite: no tourniquet, no cutting or sucking, no aspirin or ibuprofen.
- **`no-phones` / `uk-numbers` / `fieldcraft-rescue` contradict each other on SIMs.** Two pages say 999 works with no SIM; `fieldcraft-rescue` says a SIM is required. UK networks do not carry SIM-less 999 calls — settle this one way across all three pages.
- **`household-plan` — unless water** plans at 3 litres a head. That is the drinking minimum; the government's own comfort figure is 10 litres a head for cooking and washing too.
- **`mains-electricity` — grid-collapse** cites Approved Document P for a requirement that actually lives in BS 7671 §551. Separately, 105 is Great Britain only: every passage printing `[[call 105]]` should carry Northern Ireland's 03457 643643.
- **`death-and-grief`** should note that the five days now run from the medical examiner's confirmation, that Scotland uses the procurator fiscal rather than a coroner, and that moving a buried body later needs a Ministry of Justice licence.
- **`no-phones` / `what-still-works` overstate mast battery life.** Ofcom's own site data: ~20 % of masts hold an hour, ~5 % hold six. "Most masts have about an hour" should become "only about a fifth" — it moves the first hour of a blackout from *comfortable* to *urgent*, which changes what a household does first.
- **Unverified this session (search budget exhausted, not necessarily wrong):** the alpine "reply is three", torch-into-cockpit guidance, compass deflection distances, EA grave distances, and the Met Office Beaufort land descriptions. Worth a second pass with search available.
