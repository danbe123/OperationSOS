# Situational passages — corrections applied

Round of corrections against the three fact-check reports:

- `.dev/factcheck/situational-cards-report.md` (173 passages: 2 WRONG, 27 PARTLY, 1 UNSUPPORTED)
- `.dev/factcheck/situational-modules-report.md` (97 passages: 10 WRONG, 32 PARTLY, 15 UNSUPPORTED)
- `.dev/factcheck/situational-pages-report.md` (117 passages: 7 WRONG, 38 PARTLY, 3 UNSUPPORTED)

One line per changed passage: document — branch — before → after — source. Base-text lines (steps,
"Stop or escalate", "UK specifics") are listed where the same wrong claim lived in the guide sentence the
situational passage rests on, which the brief required to be corrected too. Every rewritten branch was kept
inside the house range of 20 to 120 words; no document gained a new condition flag, so the engine's ceiling
of six is untouched, and every emergency number is still written as a `[[call …]]` directive.

## Cards

- cards/anaphylaxis — `unless phones` — "Watch them for a full 24 hours" → "at least 12 hours … the NHS observes people for around 2 to 12 hours" — NHS Anaphylaxis.
- cards/anaphylaxis — Stop or escalate (guide sentence) — "watch them for a full 24 hours … 1 and 72 hours later" → "at least 12 hours … around 2 to 12 hours" — NHS Anaphylaxis.
- cards/asthma-attack — `unless phones` — "ten puffs … every 15 minutes" → "every 10 minutes … the interval Asthma + Lung UK gives" — Asthma + Lung UK / NHS asthma.
- cards/asthma-attack — Step 5 and Stop or escalate (guide sentences) — "repeat 10 puffs after 15 minutes" → "after 10 minutes" — Asthma + Lung UK.
- cards/bites-stings — Stop or escalate — bare `[[call 111]]` → 111 with "in Northern Ireland the GP out-of-hours service" — NHS 111 does not operate in NI.
- cards/broken-bones — `unless roads` — four-carrier/feet-first-downhill stated as guidance → same technique attributed as "mountain-rescue practice rather than published guidance" — MREW practice, unsourced.
- cards/burns — Step 7 (guide sentence) — "brush off dry powder, then rinse for 20 minutes or more" → "blot or brush off dry first, then rinse only if the skin itches or burns, and for about an hour" — NHS Acid and chemical burns; UKHSA Remove, remove, remove.
- cards/carbon-monoxide — Stop or escalate — `[[call 111]]` → 111 plus the NI GP out-of-hours route — NHS 111 not in NI.
- cards/chemical-exposure — Stop or escalate (guide sentence) — "if they are awake give water or milk to dilute it" → "give them nothing at all to eat or drink … rinse the mouth and spit it out" — NHS Poisoning.
- cards/chemical-exposure — Stop or escalate — "keep washing until the stinging stops" → "rinse a chemical burn for about an hour rather than the twenty minutes a heat burn takes" — NHS Acid and chemical burns.
- cards/choking — `unless phones` — "eating and drinking nothing but sips for a few hours" → "let them eat and drink normally unless swallowing hurts" — no source for the fasting rule; SCMG ch.1 for the review.
- cards/choking — `if scenario:famine` — stated as guidance → closed with "none of this is published guidance; it is plain sense" — UNSUPPORTED, softened.
- cards/cpr-adult — `unless phones` — "stopping at 20 minutes is reasonable" → "Resuscitation Council UK gives a lay rescuer no time limit; the remote protocol allows stopping after 30 minutes of continuous CPR with no sign of life — but not if they are cold, drowned, struck by lightning, poisoned, or a child" — RCUK 2025 adult BLS; WMS/CWS remote CPR protocol.
- cards/cpr-adult — Stop or escalate (guide sentence) — "reasonable to stop after 20 minutes" → RCUK's no-time-limit rule plus the remote protocol's 30 minutes and its exemptions — RCUK 2025; WMS/CWS.
- cards/cpr-adult — `unless phones` — "cabinets are locked with a code the 999 handler gives out" → "cabinets are meant to be unlocked at all hours and many are not" — RCUK 2025 (AED cabinets unlocked 24 hours).
- cards/dehydration — `if water` / `if water (else)` — "an adult with diarrhoea needs three litres or more a day" → "keep replacing what is lost, which Where There Is No Doctor puts at three litres a day or more" — attribution made explicit (WTIND p. 201, not a UK source).
- cards/dehydration — `if phones` — bare `[[call 111]]` → "in Northern Ireland there is no 111, so use your trust's Phone First number or the GP out-of-hours service" — NHS 111 not in NI.
- cards/dental-abscess — Stop or escalate — `[[call 111]]` → plus NI GP out-of-hours — NHS 111 not in NI.
- cards/drowning — `unless phones` — "reach, throw or wade with a line held from the bank" → "reach or throw from the bank: the RNLI's rule is that you do not go in the water yourself, not even the shallows" — RNLI cold water safety.
- cards/electric-shock — `unless phones` — no distance, "send a runner to the fire station" → "at least 10 metres from a fallen cable … the largest fire or police station you can reach, knowing many fire stations are on-call and stand empty" — ENA/SSEN 10 m; NFCC on-call firefighters.
- cards/electric-shock — Stop or escalate — `[[call 111]]` → plus NI GP out-of-hours — NHS 111 not in NI.
- cards/eye-injury — `unless phones` — "cover both eyes to stop the injured one moving" → "taping a cup or folded pad over the injured eye without ever pressing on it and asking them not to look about rather than padding both eyes" — NHS/RCOphth eye injury.
- cards/eye-injury — Stop or escalate — `[[call 111]]` → plus NI GP out-of-hours — NHS 111 not in NI.
- cards/fever-child — `unless water` — "do not sponge a child with water you would not let them drink" (implies sponging is fine) → "Do not sponge a feverish child down at all: the NHS says it does not help" — NHS Fever in children.
- cards/fever-child — Stop or escalate — `[[call 111]]` → plus NI GP out-of-hours — NHS 111 not in NI.
- cards/frostbite — `unless power` — "test it on your own elbow: warm, never hot" → "about body temperature, and if it feels more than pleasantly warm to the elbow it is too hot" — NHS frostbite; WMS 37–39 °C.
- cards/frostbite — Stop or escalate — `[[call 111]]` → plus NI GP out-of-hours — NHS 111 not in NI.
- cards/head-injury — Stop or escalate — `[[call 111]]` → plus NI GP out-of-hours — NHS 111 not in NI.
- cards/heart-attack — `unless phones` — driving the casualty presented flatly → "this is a judgement forced on you by there being no ambulance, not normal advice; the casualty never drives" — NHS heart attack.
- cards/hypothermia — `unless phones` — "changing the wrapped bottles or stones" with no caveat → "the NHS says never to use a hot water bottle: wrapped heat goes to the trunk only, never bare on the skin and never on the arms or legs" — NHS Hypothermia; WMS austere practice.
- cards/nosebleed — `unless phones` — "still going after 30 minutes … packed and left for 48 hours" → "after two full 15-minute pinches … take the pack out at 24 hours … never beyond 48 hours" — NHS nosebleed; ENT UK packing practice.
- cards/nosebleed — Stop or escalate (guide sentences) — "after 30 minutes of proper pressure"; "leave it 48 hours" → "two full 15-minute pinches"; "out gently at 24 hours … never beyond 48, because a pack left longer needs antibiotic cover and risks toxic shock" — NHS; ENT UK.
- cards/nosebleed — Stop or escalate — `[[call 111]]` → plus NI GP out-of-hours — NHS 111 not in NI.
- cards/poisoning — `unless water` — "then sips of water or milk if they are fully awake" after a swallowed corrosive → "give nothing to swallow — not water, not milk … diluting a corrosive can bring it back up over the gullet a second time" — NHS Poisoning ("do not give the person anything to eat or drink").
- cards/poisoning — Stop or escalate (guide sentence) — "give water or milk to dilute corrosives" → "give nothing at all to eat or drink after a swallowed corrosive, only a mouth rinse spat out" — NHS Poisoning.
- cards/poisoning — `unless phones` — "most poisons show what they are going to do within hours" → "Some poisons show nothing for a day and still kill — paracetamol and antifreeze above all" — NHS paracetamol overdose; toxbase-consistent.
- cards/poisoning — Stop or escalate — `[[call 111]]` → plus NI GP out-of-hours — NHS 111 not in NI.
- cards/pregnancy-emergencies — Stop or escalate — `[[call 111]]` → plus NI GP out-of-hours — NHS 111 not in NI.
- cards/radiation-sickness — `if phones` — bare `[[call 111]]` → 111 with Phone First / GP out-of-hours for NI — NHS 111 not in NI.
- cards/seizures — `unless phones` — "a second dose after 15 minutes if the fit has not stopped" → "exactly as their own care plan sets out, and a second dose only if that plan allows one, usually 10 minutes later; if it does not, do not give one" — NICE NG217; Epilepsy Action.
- cards/seizures — Stop or escalate (guide sentence) — "a second dose if the fit has not stopped after 15 minutes" → care-plan-only wording, usual interval 10 minutes — NICE NG217.
- cards/sepsis — `if scenario:famine` — blunted signs stated flatly → attributed to "WHO's guidance on severe malnutrition" — WHO SAM guidance.
- cards/sepsis — Stop or escalate — `[[call 111]]` → plus NI GP out-of-hours — NHS 111 not in NI.
- cards/severe-bleeding — `unless phones` — "leave them still for at least half an hour" → "let the clot settle: move them only when you must, and as gently as you can" — no source for the 30-minute figure.
- cards/spinal-injury — `unless phones` — "the bladder emptied" in passing → "The bladder must be emptied: that needs a catheter and somebody shown how, and if nobody has been, it is the strongest reason to get them to a crewed hospital" — SAM p. 434.
- cards/sprains-strains — Stop or escalate — `[[call 111]]` → plus NI GP out-of-hours — NHS 111 not in NI.
- cards/stroke — `unless power` — "keep the blood-pressure tablets and any anticoagulant going … stopping them suddenly is dangerous" → "Keep any anticoagulant going … never stop a beta blocker suddenly; other blood-pressure tablets can wait a day if she cannot swallow safely" — NICE NG128; BNF withdrawal advice.
- cards/stroke — Stop or escalate (guide sentence) — same over-generalisation → same correction — NICE NG128.
- cards/wound-cleaning — Stop or escalate — `[[call 111]]` → plus NI GP out-of-hours — NHS 111 not in NI.
- cards/wound-closure — `unless phones` — "look again on day three to five" → "look again on day four or five" — Emergency War Surgery (delayed primary closure day 4–5).
- cards/wound-closure — Stop or escalate (guide sentence) — "delayed primary closure 3 to 5 days later" → "on day four or five" — EWS p. 124.
- cards/wound-closure — Stop or escalate — `[[call 111]]` → plus NI GP out-of-hours — NHS 111 not in NI.

## Modules

- modules/comms — `unless mobile` — "A 999 call roams onto any network", cited to the power-cuts page → "should roam … not guaranteed on every handset", recited to Prepare's phone and broadband outages page — Prepare, phone/broadband outages.
- modules/comms — `unless landline` — "a walk to a fire station, which stays crewed" → "most UK fire stations are on-call and stand empty between shouts … a police station or a hospital emergency department is more reliably manned" — NFCC on-call firefighters.
- modules/comms — `unless phones` — no range or sharing caveat on PMR446 → "only a few hundred metres between buildings … the band is unlicensed and shared, and nobody polices interference" — Ofcom IR 2030/2009.
- modules/community — `if scenario:severe-winter` — "Falls are the commonest injury", "warm hub" cited to Wales Resilience Framework p. 29 → "more falls, fractures, road accidents and hypothermia"; the p. 29 citation dropped and the warm hub marked as local practice — NRR 2025 p. 143 (checked); Wales framework p. 29 does not mention hubs.
- modules/community — `if scenario:grid-collapse` — rest centres/warm hubs cited to Ready Scotland → "the published advice goes only as far as naming community buildings as assets, so check your council's own plan" — Ready Scotland community emergency planning.
- modules/community — UK specifics (guide sentence) — Storm Darragh hubs cited to Wales Resilience Framework p. 29 → page-level citation removed, claim softened — framework text checked.
- modules/evacuation — `if scenario:storms-flooding` — turning off the mains with no caveat → "if it is safe to do so — never touch an electrical switch while you are standing in water" — gov.uk Help during a flood.
- modules/evacuation — `if scenario:chemical` — "fans, extractors and the boiler off, into the room with the fewest openings … upwind or across the wind" → "anything that brings air in from outside such as fans or air conditioning turned off … moving upwind" — UKHSA What to do in a chemical emergency.
- modules/evacuation — `if scenario:nuclear-war` — "stay inside for at least 48 hours" cited to FEMA → "at least 24 hours, expect that to extend to 48 hours or more where fallout is heavy" — HHS REMM/Ready.gov; 48 h is Protect and Survive 1980.
- modules/evacuation — `if scenario:invasion` — "The state's plan for this scenario is to fight, not to move the population" attributed to NRR p. 184 → the target-list point attributed to p. 184, the no-mass-evacuation point presented as inference — NRR 2025 p. 184.
- modules/food — `unless power` — "raw food that has thawed is never refrozen"; no temperature threshold → "cooked and used within 24 hours … once cooked it can be frozen again and reheated only once"; cold store qualified "while it stays reliably below 8 °C" — FSA chill, freeze and defrost.
- modules/food — `if scenario:supply-chain` — "about 60% of the food it eats"; formula pointer with no safety line → "about 62%"; "ask a health visitor, GP or pharmacist at once, and never make up your own formula or give cow's milk to a baby under twelve months" — DEFRA UK Food Security Report; NHS infant feeding.
- modules/growing-food — `if scenario:heat-drought` — "A hosepipe ban … and a drought order can stop garden watering" → the ladder named correctly: temporary use ban under s. 76 WIA 1991, then a drought order banning non-essential use — Water Industry Act 1991 s. 76.
- modules/growing-food — `if scenario:impact-winter` — "grow what stands frost: potatoes, kale, leeks…" → "Potatoes are grown too, but the tops die at the first frost, so lift and clamp the crop before hard weather" — RHS/potato haulm frost-tenderness.
- modules/growing-food — `unless water` — unsourced drought practice → closed with "ordinary grower practice in a dry summer rather than published guidance" — UNSUPPORTED, softened.
- modules/growing-food — `if scenario:long-rebuild` — unsourced seed/fertility practice → "None of this rests on official guidance; it is long-standing practice" — UNSUPPORTED, softened.
- modules/livestock — `unless shops` — "Hens will live on scraps, greens, grass and what they find" → "it is illegal to feed them kitchen scraps or any catering waste, including peelings from your own kitchen"; the winter plan now runs on forage and stored feed — APHA: never feed catering waste or meat to farm animals (added to sources).
- modules/livestock — `if scenario:famine` — "one living on scraps, weeds and forage is not"; home slaughter given only as "lawful with stunning" → scraps named as illegal feed; slaughter narrowed to owner or licensed slaughterer, meat for the owner's household only, never sold or given away; fallen stock to an approved knacker or renderer, never buried on the holding — APHA; WATOK 2015; fallen stock rules.
- modules/livestock — `if scenario:long-rebuild` — unsourced husbandry → "settled husbandry rather than published guidance" — UNSUPPORTED, softened.
- modules/medical — `if phones` — NI Phone First implied as one number; Scotland's scheme implied narrow → "your own trust's Phone First line — the number differs by trust"; "Scotland's Pharmacy First is far broader than England's, covering more than thirty conditions" — NHS England Pharmacy First; HSC NI; NHS Scotland.
- modules/medical — `unless phones` — runner protocol stated as procedure → "No UK source sets out a runner protocol; this is practice, written down" — UNSUPPORTED, softened.
- modules/medical — `unless power` — "go by its in-use life" → "once in use most insulins keep 28 days to six weeks below 25 to 30 °C depending on brand … never freeze it" — NHS insulin; product SPCs.
- modules/medical — `if scenario:pandemic` — carer masks only; rash treated as the marker; "no urine for a day" → the unwell person masks in shared areas and the carer for close contact; "breathing very fast"; "twelve hours in a young child"; "many cases never have one, so do not wait for it" — UKHSA; NHS sepsis.
- modules/medical — `if scenario:nuclear-war` — 90% attributed to clothing removal *and* washing, "safe to nurse" unconditional → "clothing … alone takes off up to 90% … washing removes most of the rest … the risk to whoever nurses them is very low" — UKHSA self-decontamination.
- modules/medical — `if scenario:nuclear-accident` — same 90%/"not radioactive" phrasing; iodine priority groups missing → corrected, and "goes first to newborns, children under ten and pregnant or breastfeeding women" added — UKHSA; NRPB p. 9.
- modules/medical — `if scenario:chemical` — "wash with plenty of water" as the routine next step; "rinse … for 20 minutes or more" → water only "if the skin is itchy or painful or you are told to"; "a chemical burn that is rinsed is rinsed for about an hour" — UKHSA Remove, remove, remove; NHS Acid and chemical burns (added to sources).
- modules/mental-health — `if phones` — CALM listed in a 24-hour block; "111 … option 2" → "CALM 0800 58 58 58, which is open 5pm to midnight"; "111 and choose the mental health option", with the NI route named — CALM; NHS 111.
- modules/mental-health — `if scenario:economic-collapse` — "anyone drinking heavily every day needs a taper rather than a sudden stop" → "must not stop suddenly and must not manage it alone … get a GP or alcohol service involved … if it has already started with shaking, sweating, confusion or a fit — [[call 999]]" — NHS Alcohol misuse (added to sources).
- modules/mental-health — `if scenario:grid-collapse`, `if scenario:pandemic`, `if scenario:long-rebuild` — practice presented as guidance → each closed with an explicit "practice, not published guidance" line — UNSUPPORTED, softened.
- modules/navigation — `unless roads` — flooded-road warning with no figure → "as little as 15 cm of moving water will knock you off your feet, and shallow water hides the hazards under it" — gov.uk flood guidance.
- modules/navigation — `unless phones` — "six blasts, flashes or shouts … the reply is three" → "six blasts or flashes in quick succession, then a minute's silence, repeated until somebody reaches you; do not stop signalling because you think you have heard a reply" — Mountain Rescue England and Wales.
- modules/navigation — `if dark` — unsourced night technique → "standard night practice rather than published UK guidance" — UNSUPPORTED, softened.
- modules/power — `if scenario:grid-collapse` — "restoration taking up to seven days and rota disconnection after that" cited to p. 90 → seven days cited to pp. 90–91 and rota disconnection moved out of this scenario — NRR 2025 pp. 90–91, 43, 93–94.
- modules/power — `if scenario:emp` — survivability stated as fact → "Nobody can tell you in advance what survived. The reasoning — not a sourced fact — is …" — UNSUPPORTED, softened; Prepare unplug advice kept.
- modules/power — `if scenario:cyber-attack` — cited NRR p. 55 (telecoms, not electricity); "treat the credit you hold as fixed"; 105 given UK-wide → p. 55 dropped; "the meter itself holds emergency credit and friendly-hours protection"; "105, Great Britain only, with Northern Ireland on 03457 643643" — NRR 2025 p. 45; Ofgem prepayment protections.
- modules/radiation — `if water` / `if water (else)` — the 90% attached to showering → "removing your outer clothing and bagging it, which alone takes off up to 90% … then showering … removes most of what is left"; "safe to nurse" → "the risk to whoever nurses them is very low" — UKHSA self-decontamination.
- modules/radiation — `if scenario:nuclear-war` — "at least 48 hours" as the current rule → "at least 24 hours, the current minimum … 48 hours or more where fallout is heavy, which was the old civil-defence figure" — HHS REMM; Protect and Survive 1980.
- modules/radiation — `if scenario:nuclear-accident` — "the tablets and instructions are already distributed" in the DEPZ → "some operators pre-distribute … site-specific rather than universal, so check your local off-site plan" — REPPIR 2019; NRPB.
- modules/sanitation — Step 2 (guide sentence) — "use a weaker 0.05% solution on hands and skin" → "keep chlorine off skin altogether … soap and water, or alcohol gel, is what hands get" — WHO/CDC chlorine guidance.
- modules/sanitation — `unless sewage` — "30 metres from any well, stream or spring"; "Septic tanks and cesspools are the permanent answer" → "30 metres from any water and 50 metres from anyone's well or borehole"; septic tank with drainage field or treatment plant under the general binding rules, cesspool stores only — Sphere/WHO; EA SPZ1; General Binding Rules 2020.
- modules/sanitation — `unless water` — greywater flushing with no caveat → "not if anyone in the house has diarrhoea or vomiting, and wash your hands afterwards" — NHS/UKHSA hygiene.
- modules/sanitation — `if scenario:storms-flooding` — "throw away food and drink it reached, including tins whose seals went under" → porous packaging, screwcaps and dented, crushed or swollen tins discarded; "a sealed, undamaged tin that went under is kept, with the outside washed" — FSA Food safety after a flood (added to sources).
- modules/sanitation — `if scenario:pandemic` — "the weaker skin solution on hands when there is no soap and water" → "0.5% … on hard surfaces … never on skin; hands get soap and water, or alcohol gel" — WHO/CDC.
- modules/security-law — `if scenario:civil-unrest` — the register's general emergency advice presented as its disorder advice, "usually" → attributed to NRR 2025 pp. 21–22 as general advice, "often the safest thing to do" — NRR 2025 pp. 21–22.
- modules/security-law — `if scenario:invasion` — CCA summary without the 7-day approval or the s. 23 limits; "carry identification" → "both Houses must approve them within 7 days or they lapse, and they lapse anyway after 30 days; they cannot conscript you, ban strikes, create an offence carrying more than 3 months, or alter the Human Rights Act. There is no general duty to carry ID in the UK" — Civil Contingencies Act 2004 ss. 23, 26, 27; Identity Documents Act 2010.
- modules/security-law — `if scenario:terrorism` — secondary-device risk implied → "do not bunch at exits or rally points" added — ProtectUK Run Hide Tell.
- modules/shelter-heat — `unless power` — "a gas hob still lights with a match" → "most gas hobs still light with a match, though a fully electronic one will not — check yours" — hob solenoid/FSD design.
- modules/shelter-heat — `unless gas` — gas-smell steps missing two cautions → "do not smoke or light a match and do not turn any electrical switch on or off" — National Gas / Gas Safe.
- modules/shelter-heat — `if scenario:severe-winter` — "Cold-Health Alerts run from 1 November to 30 March" → "to 31 March" — UKHSA weather-health alerting (added to sources).
- modules/shelter-heat — `if scenario:impact-winter` — seasoning/insulating order stated as rule → "settled practice rather than a published rule" — UNSUPPORTED, softened.
- modules/tools-repair — `unless power` — "isolate at the consumer unit and prove dead before touching anything", cited to INDG231 → "Switching off at the consumer unit is as far as an untrained person should go — safe isolation and proving dead need training and proper test equipment under the Electricity at Work Regulations 1989" — EAWR 1989; HSE GS38 (INDG231 does not cover it).
- modules/tools-repair — `unless shops`, `if scenario:grid-collapse`, `if scenario:supply-chain` — salvage/maintenance practice stated as guidance → each marked as practice rather than published guidance — UNSUPPORTED, softened.
- modules/vehicles-fuel — Step 2 and `unless roads` — "30 cm of it will float a car", cited to Help during a flood (which carries no depth figure) → "as little as 30 cm of moving water will float a car, and around 60 cm will carry away a vehicle of any size", recited to gov.uk Flash flooding — EA/AA; gov.uk Flash flooding (added to sources).
- modules/vehicles-fuel — `if scenario:supply-chain` — "the household limit" never stated → "up to 30 litres with no notification, in containers no bigger than 10 litres plastic or 20 litres metal, marked PETROL" — Petroleum (Consolidation) Regulations 2014.
- modules/water — `unless power` — "a treatment works holds up to about 24 hours of treated water, and many sites have no standby generator" (not in the cited CMO script or any source found) → claim removed; the gravity-fed vs pumped distinction kept — CMO outage advice.
- modules/water — `if scenario:storms-flooding` — "350,000 people … for up to 17 days" → "roughly 350,000 people … for over two weeks" — Mythe 2007 retrospectives.
- modules/water — `if scenario:heat-drought` — "drought orders … that allow rota cuts and standpipes" → temporary use ban, then drought order for non-essential use, then "only as a last resort an emergency drought order … none has been made since 1976"; "boiling does not make algae-affected water safe" added — WIA 1991 ss. 74–76, 79A; DWI cyanobacteria.

## Pages

- pages/amateur-bands — `scenario:emp` — metal-tin survivability stated as fact → "Nobody can tell you in advance what survived: … test everything on receive first" — UNSUPPORTED, softened.
- pages/butchery — `unless water` — tularaemia implied endemic → "rare in Britain but caught through cuts when skinning hares and rabbits" — UKHSA/tularaemia epidemiology.
- pages/butchery — `unless power` — "kill only what the household will eat that day" as a rule → "as a rule of thumb" — no UK source for the rule.
- pages/butchery — `scenario:heat-drought` — "Cook to 74 °C right through" → "70 °C held for two minutes, or 75 °C for thirty seconds" — FSA Cooking your food.
- pages/chronic-conditions — `scenario:supply-chain` — "a pharmacy may hold phenobarbital or phenytoin when it cannot get lamotrigine or levetiracetam … take the equivalent the pharmacist offers" → "Never accept a different epilepsy medicine: a pharmacist may only supply the same medicine you were prescribed, and only a prescriber can change one" — Human Medicines Regulations 2012 reg. 225; MHRA AED switching categories.
- pages/chronic-conditions — `unless power` — "ration [oxygen] to the pulse oximeter target"; dialysis diet only → "the back-up cylinder at the flow rate on their prescription … get word to the supplier's 24-hour line"; "at least 3 metres from any flame"; "get word to the renal unit"; insulin cross-reference added — NHS home oxygen; Kidney Care UK.
- pages/chronic-conditions — `unless phones` — "ask for an emergency supply" → "ask for an emergency supply by name, which a pharmacist can give for up to 30 days" — HMR 2012 reg. 225.
- pages/death-and-grief — `unless phones` — "the five days in England and Wales" → "which now run from the medical examiner's confirmation rather than from the death"; "in Scotland the death goes to the procurator fiscal rather than a coroner" — gov.uk After a death.
- pages/death-and-grief — `scenario:long-rebuild` — burial on private land with no legal caveat → "a last resort where no authority can be reached: report the death and the grave at the first opportunity … Moving a body afterwards needs a licence, not just a spade" — Burial Act 1857 s. 25; coroner duty.
- pages/death-and-grief — `if phones` — `[[call 111]]` → plus NI GP out-of-hours — NHS 111 not in NI.
- pages/fieldcraft-basics — `if dark` — "expect to cover half the distance you planned" → "far less ground than you planned — halving it is a rule of thumb rather than a published figure" — MREW Fact File 6 has no figure.
- pages/fieldcraft-fishing — `scenario:storms-flooding` — leptospirosis "about a week later", cited to the UKHSA flooding page → "one to two weeks later and sometimes as much as a month", recited to the leptospirosis article first — UKHSA leptospirosis.
- pages/fieldcraft-fishing — `unless sewage` — estuary/outfall rule implied to be an FSA quote → "sense drawn from how shellfish waters are graded, not a quoted instruction" — FSA shellfish classification.
- pages/fieldcraft-food — `scenario:famine` — "the most poisonous plant in Britain … taken for wild celery or parsnip" → "one of the most poisonous plants in Britain … its root has been eaten in mistake for parsnip" — Oenanthe crocata case series.
- pages/fieldcraft-food — `if phones` — `[[call 111]]` → plus NI GP out-of-hours — NHS 111 not in NI.
- pages/fieldcraft-hygiene — `unless sewage` — camp deep-pit rule applied to a house → "In a house the CMOs' advice is to seal the bags and put them out with the household waste; the deep pit … is for camps and open ground" — UK CMOs' water and sanitation script.
- pages/fieldcraft-hygiene — `scenario:storms-flooding` — "throw away food and tins whose seals were under it" → porous packaging and dented, crushed or swollen tins discarded; sealed undamaged tins kept and washed — FSA Food safety after a flood.
- pages/fieldcraft-moving — `unless roads` — "The footpath, bridleway, byway, towpath and disused railway network … takes wheels" → "Bridleways, byways, towpaths and disused railways take wheels … A public footpath is for feet, mobility scooters and powered wheelchairs only, so do not plan a cycle route along one" — gov.uk rights of way.
- pages/fieldcraft-moving — `if dark` — torch/compass deflection with an implied distance → "it deflects the needle, though no source gives a reliable distance" — UNSUPPORTED, softened.
- pages/fieldcraft-navigation — `if dark` — "Polaris gives north"; deflection distance → "north to within about a degree"; deflection distance marked unsourced — Polaris ~0.66° from the pole.
- pages/fieldcraft-rescue — `if dark` — "keep going after you hear the three that answer" → "six flashes in quick succession, a minute's silence, then six again, and do not stop because you think you have heard a reply"; "never into the cockpit" added — MREW Fact File 6.
- pages/fieldcraft-rescue — `scenario:storms-flooding` — reach-or-throw without the shallows; fire/coastguard split implied sourced → "not even the shallows"; split marked as ordinary 999 triage — RNLI.
- pages/fieldcraft-rescue — `unless roads` — landing-site advice implied sourced → "practice rather than published guidance, but it is what a crew looks for" — UNSUPPORTED, softened.
- pages/fieldcraft-shelter — `unless heating` — hypothermia signs given as "clumsiness and unusual quiet" only → "shivering, pale cold skin, slurred speech, clumsiness and unusual quiet" — NHS Hypothermia.
- pages/fieldcraft-water — `unless water` — private supplies "untreated" and the pathogen list stated as a DWI list → "not treated to mains standards and can carry …" — DWI private water supplies.
- pages/fieldcraft-water — `scenario:nuclear-war` — settling implied to remove fallout → "let it stand at least six hours and pour off the clear water — that takes out the particles, not anything dissolved" — NWSS.
- pages/fieldcraft-water — `scenario:storms-flooding` — leptospirosis "about a week later" → "one to two weeks later, sometimes as much as a month" — UKHSA.
- pages/fieldcraft-weather — `if dark` — falling-glass signs stated as fact → "the conventional signs … unsourced but sound" — UNSUPPORTED, softened.
- pages/fieldcraft-weather — `scenario:severe-winter` — "Force 8, when twigs break off and you cannot walk into the wind" → "Force 8, a gale at 39 to 46 mph" — Met Office Beaufort scale.
- pages/food-storage — `unless power` — "do not refreeze it" → "raw thawed food is never refrozen, but once cooked it can be frozen again and reheated only once" — FSA.
- pages/food-storage — `scenario:heat-drought` — "never kept above 32 °C" → "tins keep longest below about 29 °C, are harmed above about 38 °C and should never be frozen" — USDA canned-food storage.
- pages/foraging-law — `scenario:famine` — "Eggs and nesting birds are protected everywhere in the UK, whatever the species"; snares "unless you have checked" → quarry species, general and individual licences named, NI's 1985 Order named, and the snare position given for Wales, Scotland and England — WCA 1981; Agriculture (Wales) Act 2023 s. 46; Wildlife Management and Muirburn (Scotland) Act 2024 s. 6.
- pages/household-plan — `unless water` — planning at 3 litres a head → "3 litres a person a day for drinking, and … the government's comfort figure of 10 litres a head if you are cooking and washing too" — Prepare, water supply interruptions.
- pages/infant-feeding — `unless water` — "Boiling is also the steriliser, five minutes in a covered pan" → "at least ten minutes in a covered pan … check teats for cracks" — NHS sterilising baby bottles.
- pages/infant-feeding — `scenario:pandemic` — cup feeding and hand expressing implied NHS advice → "the standard WHO and UNICEF practice for feeding in emergencies rather than NHS consumer advice" — WHO/UNICEF IFE.
- pages/infant-feeding — `if phones` — `[[call 111]]` → plus NI GP out-of-hours — NHS 111 not in NI.
- pages/knife-firearms-law — `scenario:civil-unrest` — "self-defence has never been a good reason"; householder test omitted → "carrying a blade out of a general fear of attack is not a good reason in law: that defence very rarely succeeds"; "for a householder facing an intruder only grossly disproportionate force is ruled out" — CPS charging guidance; CJIA 2008 s. 76(5A).
- pages/mains-electricity — `unless power` — 105 given UK-wide; no generator distance → "105 in Great Britain, or 03457 643643 in Northern Ireland"; "outdoors, at least 6 metres from doors and windows" — powercut105; CMO outage advice.
- pages/mains-electricity — `scenario:storms-flooding` — no distance, no auto-reclose warning → "at least 10 metres back, treat … the ground near a fallen wire as live … expect the line to switch itself back on without warning"; NI number added — HSE GS6; SSEN.
- pages/mains-electricity — `scenario:grid-collapse` — transfer switch cited to Approved Document P; prepayment top-up stated flatly → "BS 7671 section 551 forbids paralleling with the public supply, and the work is notifiable under Part P"; "may need topping up"; rota disconnection removed from this scenario — BS 7671 §551.
- pages/no-phones — `unless mobile` — "a car built since April 2018 dials 112" → "a car whose model was type-approved from spring 2018 … check whether yours actually has the SOS button" — EU Reg. 2015/758 art. 7.
- pages/no-phones — `unless landline` — "reaches 999 … even with no SIM"; battery back-up implied universal → "it does still need a SIM in it"; "which providers must give to vulnerable customers rather than to every house" — Prepare, phone/broadband outages.
- pages/no-phones — `unless internet` — Relay UK 18000 implied wholly off-internet → "works from a textphone over the phone network, though the Relay UK app needs the internet" — Relay UK.
- pages/no-phones — `unless power` — "most mobile masts have about an hour of battery" → "only about a fifth of mobile masts hold an hour of battery and only a twentieth hold six" — Ofcom RAN power resilience; NRR 2025 p. 88.
- pages/pmr446 — `unless mobile` — "one to three kilometres in a town" → "a few hundred metres among buildings, one to three kilometres in the open" — Ofcom IR 2030 (0.5 W ERP, integral antenna).
- pages/pmr446 — `scenario:emp` — metal-tin survivability stated as fact → "Nobody can say in advance what survived, so test on receive first"; the AA-cell advice kept — UNSUPPORTED, softened.
- pages/pmr446 — `scenario:solar-storm` — "may fail on GPS timing before it fails on power" → "drifts rather than stops when GPS timing is lost, because the masts hold their own clocks for a while" — Blackett Review on GNSS dependency.
- pages/solar-islanding — `scenario:severe-winter` — "0.5 kWh/m²/day in December against 4.7 in July … well under 1 kWh a day" → "about 0.7 … against 5.2 … roughly one kilowatt-hour a day in midwinter, less if it faces east or west" — PVGIS 2005–2020, London.
- pages/ticks-adders — `unless phones` — NHS snake-bite don'ts omitted → "Do not tie anything tightly round the limb, do not cut or suck the bite, and give paracetamol rather than aspirin or ibuprofen" — NHS Snake bites.
- pages/ticks-adders — Lyme paragraph — `[[call 111]]` → plus NI GP out-of-hours — NHS 111 not in NI.
- pages/uk-numbers — `unless phones` (runners) — "fire stations stay crewed and have their own radio to control" → "the largest town-centre fire, police or ambulance station you can reach; many fire stations are on-call and stand empty between shouts, and an empty station cannot be alerted without the network" — NFCC on-call firefighters.
- pages/uk-numbers — `unless internet` — Relay UK implied wholly off-internet → textphone/app distinction stated — Relay UK.
- pages/uk-numbers — `unless phones` (utilities) — no NI power-cut number → "105 in Great Britain, 03457 643643 in Northern Ireland, once the lines are back" — NIE Networks.
- pages/uk-numbers — lead paragraph (guide sentence) — "without credit and without a SIM" → "without credit — though the phone does still need a SIM in it", settling the contradiction with fieldcraft-rescue — UK network practice.
- pages/water-disinfection — `unless water` — "use it within a day or two" → "within 24 hours, which is the figure a boil-water notice gives" — DWI boil-water notice.
- pages/water-disinfection — `scenario:nuclear-war` — settling implied to remove fallout → "let it stand at least six hours … that removes the particles, not anything dissolved" — NWSS.
- pages/what-still-works — `scenario:grid-collapse` — rota disconnection attached to the cyber/NETS scenario → "if the cause is a gas-supply failure instead, expect published rota disconnections on top" — NRR 2025 pp. 45, 93–94.
- pages/what-still-works — `scenario:emp` — metal-tin survivability and "expect cars to be mostly fine" → "Nobody can tell you in advance what survived, so test everything on receive first"; the car claim cut — UNSUPPORTED, cut.
- pages/what-still-works — `scenario:solar-storm` — an ordered failure sequence, payment-system failure and assumed fallbacks attributed to NRR p. 137 → "regional power disruption, loss of GPS, and disruption to satellite communications and shortwave, all at once rather than in a tidy order"; the fallbacks no longer attributed to the register — NRR 2025 p. 137.

## Sources added

- modules/livestock — APHA, never feed catering waste, kitchen scraps or meat to farm animals.
- modules/medical — NHS, Acid and chemical burns.
- modules/mental-health — NHS, Alcohol misuse.
- modules/sanitation — FSA, Food safety after a flood.
- modules/shelter-heat — UKHSA, weather-health alerting system.
- modules/vehicles-fuel — GOV.UK, Flash flooding.
- pages carry no `sources` front matter by convention, so their new primary sources are inline citations:
  HMR 2012 reg. 225 (chronic-conditions), NHS sterilising baby bottles (infant-feeding), FSA food safety
  after a flood (fieldcraft-hygiene), GOV.UK rights of way (fieldcraft-moving), FSA cooking your food (butchery).

## Same wrong claim, propagated outside the three reports' passage lists

The brief required the guide sentence behind a corrected passage to be fixed too. These sit in documents or
sections the reports did not list, but they carried the identical claim and are now consistent:

- cards/cpr-child — Stop or escalate — "with no response at all after 20 minutes it is reasonable to stop" → "Resuscitation Council UK sets a lay rescuer no time limit, and the 30-minute rule used in remote settings expressly excludes children, so keep going for an hour or more" — RCUK 2025 paediatric BLS; WMS/CWS.
- cards/carbon-monoxide — `unless phones` — "the nearest fire station, which stays crewed and has its own radio" → "the largest town-centre station you can reach, knowing many fire stations are on-call and stand empty" — NFCC.
- pages/no-phones — "Know the nearest crewed places" (base) — "Fire stations are the most reliable: they stay crewed in a crisis" → on-call stations named, with police stations and emergency departments preferred — NFCC.
- pages/no-phones — lead bullet (base) — "most mobile masts have about an hour of battery" → "only about a fifth … hold an hour and about a twentieth hold six" — Ofcom RAN power resilience.
- pages/what-still-works — "What still works" table row (the guide `no-phones` cites) — same mast-battery claim → same correction — Ofcom.
- kits/comms — `intro` — "most mobile masts hold about an hour of battery" → "only about a fifth of mobile masts hold an hour of battery" — Ofcom.
- scenarios/storms-flooding — First 72 hours — "tins whose seals were under water go with the rest of the food it touched" → porous packaging and dented, crushed or swollen tins go; a sealed undamaged tin is kept and washed — FSA Food safety after a flood.
- scenarios/severe-winter — Right now and UK specifics — "Cold-Health Alerts run from 1 November to 30 March" (twice) → "to 31 March" — UKHSA weather-health alerting.

## Left unresolved

- **Sources with no library copy.** Resuscitation Council UK 2025, the WMS/CWS remote CPR protocol, NFCC's
  on-call firefighter page, Ofcom's RAN power-resilience data, CALM's opening hours, PVGIS, the Blackett
  Review and CPS charging guidance are not in the manifest. The corrected passages name the authority in
  prose and keep the nearest library citation; they cannot carry a `kiwix:`/`doc:` link until those items
  are added to the library.
- **New `kiwix:` paths are unverified against the ZIMs.** Six paths were introduced
  (`www.gov.uk/guidance/flash-flooding`, `www.gov.uk/guidance/never-feed-catering-waste-or-meat-to-farm-animals`,
  `www.gov.uk/government/publications/food-safety-after-a-flood-consumer-advice`,
  `www.gov.uk/government/publications/cooking-your-food/cooking-your-food`,
  `www.gov.uk/right-of-way-open-access-land`, `www.nhs.uk/conditions/acid-and-chemical-burns/`,
  `www.nhs.uk/conditions/alcohol-misuse/`, `www.nhs.uk/conditions/fever-in-children/`,
  `www.nhs.uk/conditions/baby/…/sterilising-baby-bottles/`, `legislation.gov.uk/uksi/2012/1916/regulation/225`).
  `sos validate-playbooks` without `--deep` only checks the ZIM id, so these need a
  `sos validate-playbooks --deep` run on the box (the `nhs_uk` ZIM is not present on this PC) before release.
- **`[[call 111]]` outside cards, modules and pages.** The Northern Ireland qualification was added to every
  111 instruction in `playbooks/cards`, `playbooks/modules` and `playbooks/pages`. The scenario playbooks
  (`chemical`, `pandemic`, `terrorism`, `nuclear-accident`, `volcanic`, `supply-chain`) were outside the scope
  of these three reports; `pandemic` and `medical` already carry the NI route, the others still point at 111
  alone and should be swept next.
- **Wales Resilience Framework p. 29.** The Storm Darragh / village hub claim in `modules/community` UK
  specifics could not be re-verified, so the page-level citation was dropped and the claim softened rather
  than removed; someone with the PDF should confirm or cut it.
- **`sepsis — if scenario:famine`.** Attributed in prose to WHO's severe-malnutrition guidance, which is not
  in the library; the card keeps its existing citations.
- **Unverified in the pages report and still unverified here** (search budget, not necessarily wrong): the
  alpine "reply is three" convention (removed rather than corrected), torch-into-cockpit guidance, compass
  deflection distances, and Environment Agency grave-distance figures. Each is now marked in the text as
  practice rather than sourced guidance.
