# Situational passages — fact-check report

Scope: all 97 situational passages in `.dev/factcheck/situational-modules-claims.md`, across the 17 topic modules.
Method: primary UK sources. The National Risk Register 2025, Wales Resilience Framework 2025 and NRPB stable-iodine PDFs were downloaded and read directly (page numbers below are the printed page, verified); gov.uk / Prepare, UKHSA, FSA, NHS, DEFRA/APHA, Ofcom, ENA/Ofgem, DWI/EA, HSE, MREW, ProtectUK and legislation.gov.uk were fetched live.
Verdicts: **V** verified · **P** partly (true but imprecise, over-claimed or miscited) · **U** unsupported (sound but no primary source found) · **W** wrong (correction required).

## comms

| branch | verdict | evidence | suggested wording |
|---|---|---|---|
| if phones (else) | V | Lead-in only; consistent with Prepare (105 and 999 both need a working line/signal). | — |
| unless mobile | P | Prepare, phone and broadband outages: "emergency calls automatically roam onto any available network, and the 999 call system and emergency services are designed to keep running during power cuts." emergencySMS pre-registration confirmed. But the passage cites the **power cuts** page, which says none of this. | Recite to `prepare.campaign.gov.uk/be-informed-about-hazards/phone-broadband-outages/`. Soften to "a 999 call *should* roam onto any network with coverage — it is not guaranteed on every handset". |
| unless landline | W | Battery back-up VERIFIED verbatim: "If you are a vulnerable customer... your communication provider must provide a free back-up battery unit" giving "at least one hour... though many modern batteries last considerably longer" (same Prepare page). But most UK fire stations are On-Call/Retained and **not crewed round the clock** (NFCC: on-call firefighters "are not based at a fire station 24 hours a day"). | "A fire station may be unstaffed when you arrive — treat it as a possible help point, not a guaranteed crewed base. A police station or hospital ED is more reliably manned." |
| unless internet | V | Emergency Alerts are broadcast from masts over 4G/5G and need no data (gov.uk/alerts). | — |
| unless phones | P | PMR446 is licence-exempt: 8 analogue (+16 digital) channels, max 500 mW ERP, integral antenna only (Ofcom IR 2009). Ofcom does not manage interference on it. | Add "expect only a few hundred metres in a built-up area, and other people may already be on your channel — it is unlicensed and shared." |

## community

| branch | verdict | evidence | suggested wording |
|---|---|---|---|
| if phones | V | NRR 2025 p.21: register with the Priority Services Register; "Ask anyone you provide care for if they are registered." | — |
| if phones (else) | V | Same. | — |
| if scenario:grid-collapse | P | Register-at-the-door advice is sound. But the Ready Scotland community emergency planning page cited says nothing about councils opening rest centres or warm hubs — it only mentions identifying "community buildings" as assets. | Drop the citation or replace with your council's local emergency plan; keep the advice as practice, not as a quoted source. |
| if scenario:severe-winter | P | NRR 2025 p.143 verifies the winter scenario but only says "An increase in falls, injuries (for example fractures), road accidents and hypothermia would also be expected" — it does **not** rank falls as commonest. Wales Resilience Framework 2025 p.29 is about JESIP/ECCW/the Pan-Wales Response Plan; it contains no mention of warm hubs at all (checked full text). | Drop "commonest"; drop the Wales p.29 citation entirely. |
| if scenario:pandemic | U | Sensible mutual-aid practice; no primary source. Note UKHSA now puts the mask on the **unwell person** in shared areas as well as the carer. | — |
| if scenario:famine | U | No primary source; historically consistent with UK rationing practice. | — |
| if scenario:long-rebuild | V | NRR 2025 p.22 verbatim: "Recovery from a serious incident can last months, years or even decades" and affected communities "should be involved in determining how recovery is best achieved in their community." | — |

## evacuation

| branch | verdict | evidence | suggested wording |
|---|---|---|---|
| unless phones | V | NRR 2025 p.22: "It is important for people not to delay evacuating... Delaying or refusing to evacuate may put individuals' own lives at risk." | — |
| if scenario:storms-flooding | V | gov.uk *Help during a flood*: "move your family, vehicles, pets and important items to safety, for example upstairs or to higher ground"; "turn off your gas, electricity and water supplies, if it's safe to do so". | Add the page's own caveat: "do not touch an electrical switch if you're standing in water." |
| if scenario:chemical | P | UKHSA *What to do in a chemical emergency* verifies go in / stay in / tune in, closing doors and windows, "Turn off any equipment which brings air from the outside into the building (such as fans or air conditioning)", and "move upwind". It does **not** mention the boiler, "the room with the fewest openings", or moving across the wind. | Drop "boiler off", "fewest openings" and "across the wind"; keep "upwind". |
| if scenario:nuclear-war | P | Current US federal guidance (HHS REMM/Ready.gov) says shelter **at least 24 hours** unless told otherwise; the 48-hour figure is *Protect and Survive* (1980), not FEMA 2022. Vehicle PF ≈ 2 is widely published but not confirmable from a live primary page. | "Get inside and stay inside for at least 24 hours, and expect that to extend to 48 hours or more where fallout is heavy; leave only when told." |
| if scenario:nuclear-accident | V | UKHSA *What to do in a radiation emergency*: "In most cases you will be advised to stay inside for one to two days after a release"; "Vehicles and tents do not provide sufficient shelter"; "leaving shelter may increase your exposure"; children "will be asked to stay where they are until it is safe to move." | — |
| if scenario:invasion | P | NRR 2025 p.184 supports the target list: "targets are related to infrastructure. Although no population centres are deliberately targeted..." NRR p.22 supports not delaying. But "the state's plan for this scenario is to fight, not to move the population" is not in the NRR (and the nuclear scenario is explicitly held at higher classification). | Attribute only the target-list point to p.184; present the no-mass-evacuation point as inference, not as the register's position. |

## food

| branch | verdict | evidence | suggested wording |
|---|---|---|---|
| if power | V | gov.uk *Food safety in a power cut* and the UK CMOs' food and nutrition script: "A fridge should stay cold for around 4 hours... Food in a full freezer can stay frozen for up to 48 hours, 24 hours if the freezer is half full." | — |
| if power (else) | V | Same. | — |
| if power (cooking) | V | CMO script: "Never use camping stoves or barbecues indoors as there is a very high risk of carbon monoxide poisoning, which can kill." Fire services specifically warn about disposable BBQs in tents and porches. | — |
| if power (else, cooking) | V | Same. | — |
| unless power | P | Eat-order VERIFIED by the CMO script ("eat chilled and frozen food that is likely to go off quickly first..."). Cold store VERIFIED ("In cold weather... You can keep food outside in a clean and dry sealed container... protect it from animals"). The refreezing line is directionally right but the FSA's actual rule is: cook thawed food and use it within 24 hours; you may refreeze **once cooked**. | Add the temperature threshold ("reliably below 8 °C outside") and restate as: "Thawed raw food is cooked, not refrozen — but once cooked it can be frozen again, and reheated only once." |
| unless shops | V | NHS/Eatwell reference intakes: around 2,000 kcal a day for women and 2,500 for men. | — |
| if scenario:famine | V | UK rationing ran 8 January 1940 to 4 July 1954; registration with one retailer and "fair shares for all" both accurate (IWM). | — |
| if scenario:supply-chain | P | DEFRA/UK Food Security Report: **62%** of all food consumed is produced domestically (75% of "indigenous" food) — "about 60%" understates. The infant-formula pointer carries no safety line. | "The UK produces about 62% of the food it eats." And add: "If formula runs out, contact a health visitor, GP or pharmacist at once — never make your own formula and never substitute cow's milk for a baby under 12 months." |

## growing-food

| branch | verdict | evidence | suggested wording |
|---|---|---|---|
| unless water | U | Standard RHS-consistent drought practice; no primary citation. | — |
| if scenario:heat-drought | P | A hosepipe ban is a **Temporary Use Ban** under s.76 Water Industry Act 1991, not a drought order. Only an **emergency drought order** could authorise standpipes/rota cuts, and none has been made since 1976. | "A hosepipe ban (Temporary Use Ban, s.76 WIA 1991) comes first; a drought order can extend that to all non-essential use, including garden watering by any method." |
| if scenario:famine | V | Allotment numbers rose from ~815,000 pre-war to ~1.4 million by 1943–45 under Dig for Victory. | — |
| if scenario:impact-winter | W | **Potato foliage is frost-tender** — haulm is blackened by frost and tubers are lifted and clamped before hard frost, unlike kale, leeks, swede, turnip, cabbage and broad beans, which do stand frost. Tambora/1816 VERIFIED. | "Grow what stands frost: kale, leeks, swede, turnip, cabbage and broad beans. Potatoes are grown too, but the tops die at the first frost — lift and clamp the crop before hard weather." |
| if scenario:long-rebuild | U | Sound seed-saving and fertility practice; no primary citation. | — |

## livestock

| branch | verdict | evidence | suggested wording |
|---|---|---|---|
| if water | V | Trivially true. | — |
| if water (else) | V | Trivially true. | — |
| unless shops | W | **Illegal as written.** APHA: "It remains illegal to feed catering waste, kitchen scraps, meat or meat products to farmed animals... Catering waste means all waste food originating in restaurants, catering facilities and household kitchens." This applies to backyard hens. Animal Welfare Act 2006 duty of care VERIFIED. | "Hens can range for grass, insects and greens and can be fed feed bought or grown for the purpose — but it is illegal to feed them kitchen scraps or any catering waste, including vegetable peelings from your own kitchen. Plan your winter numbers around forage and stored feed, not scraps." |
| if scenario:supply-chain | V | APHA/DEFRA impose Avian Influenza Prevention Zones and housing orders at very short notice, with movements licensed and general licences suspended in control zones. | — |
| if scenario:famine | P | Home slaughter is lawful but narrower than stated: only the owner, or a licensed slaughterer under the owner's supervision; stunning required (WATOK 2015); the meat is for the owner's immediate household only — "the sale or gifting of meat from a home slaughtered animal is not permitted". Separately, fallen stock **may not be buried or burned on the holding**. | Add the household-only rule and the sale/gifting ban, and add "dead stock must go to an approved knacker, renderer or incinerator — burial on the holding is not lawful." |
| if scenario:long-rebuild | U | Sound husbandry; no primary citation. | — |

## medical

| branch | verdict | evidence | suggested wording |
|---|---|---|---|
| if phones | P | Pharmacy First's **seven** conditions VERIFIED (NHS England: otitis media, impetigo, infected insect bites, shingles, sinusitis, sore throat, uncomplicated UTI). UTC standard VERIFIED: "a minimum of 12 hours a day, 7 days a week, including bank holidays", with X-ray. NI: Phone First is run per HSC trust, so there is no single NI number; Scotland's Pharmacy First covers 30+ conditions, not a narrow parallel list. | "…your local trust's own Phone First line — the number differs by trust"; note Scotland's scheme is much broader. |
| if phones (else) | V | Consistent with the above. | — |
| unless phones | U | Sound runner protocol; no primary source. | — |
| unless power | P | Oxygen/naked-flame VERIFIED (NHS home oxygen: keep at least 3 m from open flame). "Go by its in-use life" gives no usable number. | "Once in use, most insulins keep 28 days to 6 weeks out of the fridge below 25–30 °C depending on brand — check your own pen's leaflet. Never freeze it or leave it in direct heat." |
| if scenario:pandemic | P | ORS/pale urine VERIFIED (NHS dehydration). Current UKHSA guidance puts the mask primarily on the **unwell person** in shared areas. Red flags: NHS says "breathing very fast"; the urine cut-off is 12 hours in young children; and sepsis and meningitis are frequently severe **with no rash at all**. | "The unwell person masks in shared areas; the carer masks for close contact." And: "A non-fading rash is an emergency if present — but do not wait for a rash, many cases never have one." |
| if scenario:nuclear-war | P | UKHSA self-decontamination: "Taking off your outer layer of clothing can remove up to 90% of radioactive material." The 90% belongs to **clothing removal**, not washing. No source states a decontaminated person is unconditionally "safe to nurse". | "Removing outer clothing takes off up to 90% of the contamination; washing skin and hair removes most of the rest. Once decontaminated the risk to carers is very low." |
| if scenario:nuclear-accident | P | UKHSA VERIFIED on sheltering, vehicles and iodine ("Stable iodine only protects the thyroid; it does not counteract other impacts of radiation"). Omits who it is for. | Add "priority goes to newborns, children under 10, and pregnant or breastfeeding women; check the leaflet for who should not take it." |
| if scenario:chemical | W | Two errors. (a) UKHSA sequencing: "Remove the substance from your skin using a dry absorbent material... **Rinse continually with water if the skin is itchy or painful**" — water is conditional, not the routine next step. (b) NHS *Acid and chemical burns*: rinse "for **about 1 hour**" — 20 minutes is the figure for thermal burns and is unsafe for a chemical burn. No-vomiting rule VERIFIED; HSE INDG258 confined-space warning VERIFIED. | "Blot or brush the substance off dry first. Rinse with plenty of water only if the skin is itchy or painful or you are told to — and if you do rinse a chemical burn, keep going for about an hour; irrigate an affected eye continuously until help arrives." |

## mental-health

| branch | verdict | evidence | suggested wording |
|---|---|---|---|
| if phones | W | Samaritans 116 123 (free, 24/7), Shout 85258 (24/7) and Childline 0800 1111 all VERIFIED. **CALM 0800 58 58 58 is open 5pm to midnight every day, not 24 hours** — listing it beside Samaritans in a 24-hour block will send someone to a dead line at 3am. "111 option 2" is not a fixed menu position nationally. | "CALM 0800 58 58 58 (5pm to midnight)"; and "call 111 and choose the mental health option." |
| if phones (else) | V | Consistent. | — |
| if scenario:grid-collapse | U | Sound routine-and-role advice; Prepare's coping-with-trauma page supports the general framing but not the specifics. | — |
| if scenario:pandemic | U | Sound; no primary source. | — |
| if scenario:economic-collapse | W | NHS *Alcohol misuse*: "It can be very dangerous to stop drinking suddenly if you're dependent on alcohol" and "Get medical help before you stop or reduce drinking if you get withdrawal symptoms." The NHS does not endorse self-directed tapering; "needs a taper" reads as permission to self-manage. | "Anyone drinking heavily every day must not stop suddenly and must not try to manage it alone — abrupt withdrawal can cause seizures and delirium tremens. Get a GP or alcohol service involved; if withdrawal has already started with shaking, sweating, confusion or a fit, that is a 999 call." |
| if scenario:long-rebuild | U | Sound; no primary source. | — |

## navigation

| branch | verdict | evidence | suggested wording |
|---|---|---|---|
| unless roads | P | Naismith's rule as stated (1 h per 5 km + 1 min per 10 m ascent) is the standard UK formulation. The flooded-road warning is supported: gov.uk *Flash flooding* — "Shallow flood water (around 15cm or 6 inches)... can knock a person over or conceal hazards" — but the specific manhole/ditch detail is not in the source. | Cite gov.uk flash flooding and use its own figure: "as little as 15 cm of moving water can knock you off your feet, and shallow water hides hazards." |
| if dark | U | Sound night-navigation practice (bearing, pacing, red light, Pole Star); no UK primary source. | — |
| unless phones | P | MREW's own wording is "Six short blasts (or flashes) in quick succession, repeated at one minute intervals... Continue until someone reaches you." It does not include shouts, and it states **no** "reply is three" convention. | "Six blasts or flashes in quick succession, then a minute's silence, repeated until someone reaches you (Mountain Rescue England and Wales). Do not stop signalling because you think you have heard a reply." |

## power

| branch | verdict | evidence | suggested wording |
|---|---|---|---|
| if phones (PSR) | V | PSR is free and explicitly covers dependence on electrical medical equipment (Ofgem/Prepare). | — |
| if phones (else) | V | Same. | — |
| if power (lighting) | V | Prepare, power cuts: "Torches are safer than candles." | — |
| if power (else, lighting) | V | Same. | — |
| if scenario:grid-collapse | P | NRR 2025 p.90 VERIFIED verbatim: total NETS failure, "All consumers without backup generators would lose their mains electricity supply instantaneously and without warning", winter assumption. But "up to 7 days" is on **p.91**, and **rota disconnection is not part of this scenario** — 3-hour rolling cuts belong to the gas/electricity shortfall risk (pp.43, 93–94). | Cite pp.90–91 and drop "rota disconnection after that" from this scenario. |
| if scenario:emp | P | The unplug-before-restoration advice is VERIFIED (Prepare: "Unplug your TV and PC as they can be damaged if there is a surge when power goes back on"). The EMP survivability claims rest only on Wikipedia. | Keep the unplug advice with the Prepare citation; mark the EMP survivability points as reasoning, not sourced fact. |
| if scenario:solar-storm | V | NRR 2025 p.137 verbatim: "approximately the same scale and magnitude as the Carrington Storm of 1859, lasting for 1-2 weeks... Each phenomenon would likely occur several times during a 2-week period", with regional power disruption and loss of GNSS/GPS, satellite comms and HF radio. | Optional precision: fastest CME transit is usually given as 15–18 hours. |
| if scenario:cyber-attack | P | NRR 2025 **p.45** verifies the restoration wording. **p.55 is "Cyber attack: telecommunications systems", not electricity** — wrong citation. The prepay-meter claim is incomplete: meters hold emergency credit and friendly-hours non-disconnection in the meter itself, independent of supplier systems. 105 is GB only. | Drop p.55. "You may not be able to top up while systems are down, but the meter still holds emergency credit and friendly-hours protection — use them rather than assuming you are cut off." Add "in Northern Ireland the power cut number is 03457 643643." |

## radiation

| branch | verdict | evidence | suggested wording |
|---|---|---|---|
| if water | P | UKHSA: "Taking off your outer layer of clothing can remove up to 90% of radioactive material" — the 90% is the **clothing**, not the shower. No conditioner VERIFIED. | "Removing outer clothing takes off up to 90%; showering with soap removes most of what is left." |
| if water (else) | P | Same misattribution; the jug/damp-cloth method is otherwise consistent with UKHSA self-decontamination. | Same. |
| if scenario:nuclear-war | P | The over-40 claim is VERIFIED (NRPB Vol 12 No 3, quoting WHO: "The risk to those aged over 40 years when exposed is negligible"). 48 hours is *Protect and Survive*; current guidance says at least 24. The "do not strip while fallout is falling" instruction is not in the UKHSA self-decontamination page (which starts from indoors). | Present 48 hours as the historical UK civil-defence figure and 24 hours as the current minimum; attribute the dust-down step to FEMA, not UKHSA. |
| if scenario:nuclear-accident | V | UKHSA verbatim on go in/stay in/tune in, one to two days, vehicles insufficient, children kept in place, iodine only on instruction. REPPIR 2019 establishes the DEPZ; note pre-distribution is site-specific, not a universal REPPIR requirement (NRPB "cautions against widespread pre-distribution to individual households"). | "Some sites pre-distribute tablets to households in the DEPZ — check your local off-site plan; it is not universal." |

## sanitation

| branch | verdict | evidence | suggested wording |
|---|---|---|---|
| if water | V | NHS: wash "for the amount of time it takes to sing 'Happy Birthday' twice (around 20 seconds in total)". | — |
| if water (else) | V | Same. | — |
| unless sewage | P | 30 m is the Sphere/WHO default (with the pit base 1.5 m above the water table). Near a private drinking-water source the Environment Agency's Source Protection Zone 1 is **50 m**. Approved Document H covers septic tanks, but the operative regime is the General Binding Rules 2020 — a septic tank may no longer discharge to surface water. | "At least 30 m from any water source, and 50 m from anyone's well or borehole, always downhill." And "Septic tanks with a drainage field, or a package treatment plant where discharge is to a watercourse — see the Environment Agency's General Binding Rules 2020. A cesspool only stores waste and needs tanker emptying." |
| unless water | V | NHS supports gel as the fallback to soap and water; gel does not remove soil or grease. | Add "do not reuse greywater for flushing if anyone in the house has diarrhoea or vomiting, and wash your hands afterwards." |
| if scenario:storms-flooding | W | FSA *Food safety after a flood*: "you can keep food which is in water resistant packaging including undamaged metal cans... wash the outside of the packaging before storage/opening". Only crushed, dented or swollen cans are discarded. The passage tells households to throw away sound tins. Leptospirosis VERIFIED (UKHSA: rat urine, incubation 5–14 days). | "Throw away anything not in a sealed, undamaged container, and any tin that is dented, crushed or swollen. An undamaged sealed tin that went under can be kept — wash the outside thoroughly before you open it." |
| if scenario:pandemic | P | 0.5% chlorine is the WHO/CDC strength for heavily soiled hard surfaces — correct. But chlorine handwashing even at ~0.05% is a last resort only, causes dermatitis and cracked skin, and 0.5% on skin can burn. | "Use the 0.5% solution on hard surfaces only, never on skin. Soap and water, or alcohol gel, for hands." |

## security-law

| branch | verdict | evidence | suggested wording |
|---|---|---|---|
| if scenario:civil-unrest | P | Both quotes are accurate but come from **NRR 2025 pp.21–22, Chapter 3 (Individuals and communities)** — general emergency and volunteering guidance — not from the public disorder risk entry (Ch.4, pp.171–174). The register says "often the safest thing to do"; the passage says "usually". | Correct the citation to pp.21–22 and describe it as the register's general advice during an emergency, not its disorder advice. |
| if scenario:invasion | W | Ofcom licence VERIFIED (OFW611 cond. 8.2: equipment may be "temporarily closed down... in the event of a national or local state of emergency being declared", after written or general notice). But the CCA framing is misleading and the ID line is wrong: s.27 requires **approval by both Houses within 7 days** or the regulations lapse; the 30-day cap in s.26 applies regardless; s.23 forbids conscription, banning strikes, creating offences beyond summary conviction (3 months / level 5), and amending the Human Rights Act. **There is no general duty to carry ID in the UK** — the card scheme was repealed by the Identity Documents Act 2010. | "Emergency regulations must be approved by both Houses within 7 days or they lapse, and lapse in any case after 30 days. They cannot conscript you, ban strikes, create an offence carrying more than 3 months, or alter the Human Rights Act. There is no general duty to carry ID in the UK; movement can only be restricted by such regulations or by narrow police powers." |
| if scenario:terrorism | V | ProtectUK *Run Hide Tell* near-verbatim: "escape if you can", "leave belongings behind", "lock and barricade", "be quiet, silence your phone and turn off vibrate", then call 999 with location and description. | Add the secondary-device point explicitly: "do not gather in large groups at exits or rally points." |

## shelter-heat

| branch | verdict | evidence | suggested wording |
|---|---|---|---|
| if heating | V | Standard one-warm-room advice, consistent with UKHSA cold-weather guidance. | — |
| if heating (else) | V | Same. | — |
| unless power | P | Boilers and heat pumps needing mains for pump, fan and ignition is uncontested. Match-lighting a gas hob is true of thermocouple/FSD hobs but **not** of hobs with fully electronic solenoid valves. Approved Document J para 3.43 requires a CO alarm in the room of a new or replacement fixed gas appliance, "excluding gas appliances used solely for cooking". | "Most gas hobs can still be lit with a match — check yours, as some fully electronic hobs cannot." |
| unless gas | V | NRR 2025 p.43 verbatim: "Restoration of the affected gas infrastructure could take approximately 3 months, at which point rolling power cuts would no longer be required"; "rolling power cuts lasting 3 hours at a time may be required"; "Priority of gas supply would be given to domestic users (as they take longer to reconnect following disconnection for safety reasons)." Both emergency numbers confirmed. | Add the standard cautions the passage omits: "do not smoke or light matches, and do not turn electrical switches on or off." |
| if scenario:severe-winter | W | UKHSA weather-health alerting: "the core alerting season for CHA running from **1 November to 31 March**" — the passage says 30 March. Red definition VERIFIED: "significant risk to life for everyone, including the healthy population." NRR p.143 figures VERIFIED exactly (>30 cm for at least 7 consecutive days, daily mean below −3 °C, overnight below −10 °C). | "Cold-Health Alerts run from 1 November to 31 March." |
| if scenario:impact-winter | U | Seasoning wood, insulating loft-first and sweeping the chimney are all sound and broadly consistent with Approved Documents J and L, but no verbatim support was found. | — |

## tools-repair

| branch | verdict | evidence | suggested wording |
|---|---|---|---|
| unless power | W | INDG231 ("Electrical safety and you") was read in full: it is a general workplace-equipment leaflet and **never mentions isolating, proving dead, or consumer units**. Safe isolation and proving dead sit under the Electricity at Work Regulations 1989 and require a competent person with GS38-compliant test equipment — it is not a householder procedure. | "Never assume a circuit is dead because the power is off — supply can return without warning. Switching off at the consumer unit is as far as an untrained person should go; safe isolation and proving dead need training and proper test equipment (Electricity at Work Regulations 1989), so leave anything beyond that to a registered electrician." |
| unless shops | U | Sound salvage-and-standardise practice; no primary source. | — |
| if scenario:grid-collapse | U | Sound; no primary source. | — |
| if scenario:supply-chain | U | Sound; no primary source. | — |
| if scenario:long-rebuild | V | Asbestos dates confirmed: blue and brown banned by SI 1985/910; white by SI 1999/2373, in force 24 November 1999. HSE: "Do not try to repair or remove any asbestos materials yourself if you have not had any training." | — |

## vehicles-fuel

| branch | verdict | evidence | suggested wording |
|---|---|---|---|
| if power | V | Sound habit; consistent with NRR fuel-distribution dependencies. | — |
| if power (else) | V | Same. | — |
| unless power | V | NRR 2025 p.90: a nationwide loss of power causes secondary impacts across "mobile and internet telecommunications, water, sewage, fuel and gas." | — |
| unless shops | V | Theft Act 1968 s.1. Duress of circumstances requires an imminent threat to life or serious injury, so it would not excuse siphoning in a fuel shortage. | — |
| unless roads | P | Two official figures exist: the Environment Agency/AA line "Just one foot or 30 centimetres of **moving** water can float your car", and current gov.uk *Flash flooding*: "It only takes around 60cm (2 feet) of water to carry away a vehicle of any size." The cited *Help during a flood* page carries no depth figure at all. | "As little as 30 cm of moving water can float a car, and around 60 cm will carry away a vehicle of any size." Recite to gov.uk/guidance/flash-flooding. |
| if scenario:supply-chain | P | The 2021 crisis is accurately described (an HGV driver shortage turned into empty forecourts by "spikes in localised demand" within days). NRR p.69 is "Insolvency affecting fuel supply", which does support heating fuel and road fuel failing together. But "the household limit" is never stated. | State it: "Petroleum (Consolidation) Regulations 2014 — up to 30 litres at home with no notification, in containers no larger than 10 litres plastic or 20 litres metal, marked PETROL, stored outside the dwelling. 30–275 litres needs written notice to the petroleum enforcement authority." |

## water

| branch | verdict | evidence | suggested wording |
|---|---|---|---|
| if water | V | Prepare, water supply interruptions: store water in advance; "2.5 to 3 litres of drinking water per person per day... 10 litres per person per day will make you more comfortable." | Consider adding those two figures. |
| if water (else) | V | Same. | — |
| unless power | U | The cited UK CMOs' water and sanitation broadcast script contains **none** of this — it covers fluid intake, purification and hygiene only. No Water UK or Ofwat source was found for "about 24 hours of treated water" or "many sites have no standby generator". The gravity-fed vs pumped distinction is sound engineering but unattributed. | Drop the 24-hour figure and the generator claim, or source them properly. Keep: "pumped supplies and high-rise flats on booster pumps are more vulnerable to a power cut than gravity-fed areas." |
| if scenario:storms-flooding | P | The boil notice / do-not-drink point is correct and important (a "do not drink" notice is issued for contamination boiling cannot remove). Mythe 2007 figures vary: Parliament recorded 140,000 properties with Severn Trent estimating 7–14 days; retrospectives give 350,000 people for 17–18 days. | "left roughly 350,000 people in Gloucestershire without mains water for over two weeks." |
| if scenario:heat-drought | P | The escalation ladder is mislabelled: a hosepipe ban is a Temporary Use Ban (s.76 WIA 1991); an ordinary drought order extends to non-essential use; only an **emergency drought order** could authorise standpipes and rota cuts, and none has been made since 1976. Cyanobacteria VERIFIED (DWI) — and boiling does not destroy the toxins, it can release more. | "…then a drought order banning non-essential use, and only in the last resort an emergency drought order, which is what would be needed for standpipes or rota cuts — none has been made since 1976." Add: "boiling does not make algae-affected water safe." |

## Counts

| verdict | passages |
|---|---|
| VERIFIED | 40 |
| PARTLY | 32 |
| UNSUPPORTED | 15 |
| WRONG | 10 |
| **total** | **97** |

Of the 32 PARTLY verdicts, 11 are citation errors alone (right fact, wrong page or wrong document); the rest are over-claims or missing qualifications. The 15 UNSUPPORTED passages are all sound practice with no primary UK source located — none is unsafe.

## The five corrections that matter most

1. **livestock / unless shops — feeding hens on kitchen scraps is illegal.** APHA: "It remains illegal to feed catering waste, kitchen scraps, meat or meat products to farmed animals... Catering waste means all waste food originating in restaurants, catering facilities and household kitchens." This was the likely route of the 2001 foot-and-mouth outbreak. The passage currently makes it the household's primary famine plan for poultry. Rewrite around forage, greens and stored feed, and say plainly that scraps are banned.

2. **medical / chemical — rinse a chemical burn for about an hour, and water is conditional.** NHS *Acid and chemical burns* specifies "about 1 hour"; 20 minutes is the thermal-burn figure and stopping there risks continuing tissue damage. Separately, UKHSA's Remove-Remove-Remove sequence is dry decontamination first, with water only "if the skin is itchy or painful" or on instruction — the passage presents washing as the routine next step after blotting.

3. **mental-health / economic-collapse — do not tell people to taper alcohol themselves.** NHS: "It can be very dangerous to stop drinking suddenly if you're dependent on alcohol... Get medical help before you stop or reduce drinking." A household reading "needs a taper rather than a sudden stop" will read it as permission to self-manage a withdrawal that can cause seizures and delirium tremens. And in the same module, CALM is open 5pm to midnight, not 24 hours — it currently sits in a list that reads as round-the-clock.

4. **sanitation / storms-flooding — sound tins are salvageable.** FSA *Food safety after a flood*: "you can keep food which is in water resistant packaging including undamaged metal cans... wash the outside of the packaging before storage/opening." Telling a flooded household to discard every tin that went under destroys the food they most need; only dented, crushed or swollen cans go.

5. **comms / unless landline and tools-repair / unless power — two instructions that send people to the wrong place.** Most UK fire stations are On-Call and unstaffed, so "a walk to a fire station, which stays crewed" can send someone with a life-threatening casualty to a locked building. And INDG231 does not say what it is cited for: proving dead is a competent-person procedure under the Electricity at Work Regulations 1989 requiring GS38 test equipment, not something to invite an untrained householder to do by torchlight.

### Also flag before publication
- **security-law / invasion**: "carry identification" — there is no general duty to carry ID in the UK (Identity Documents Act 2010 repealed the card scheme); and the CCA 2004 summary omits the 7-day approval requirement and the s.23 limits (no conscription, no offence above the summary cap, no amendment of the Human Rights Act).
- **growing-food / impact-winter**: potatoes are not frost-standing — the haulm dies at the first frost and the crop is lifted and clamped.
- **shelter-heat / severe-winter**: the Cold-Health Alert season ends 31 March, not 30 March.
- **food / supply-chain**: the infant-formula pointer needs an explicit line that home-made formula and cow's milk under 12 months are never safe substitutes.
- **radiation and medical**: the "up to 90%" figure belongs to removing outer clothing, not to washing.
- **water / unless power**: the "24 hours of treated water, many sites have no standby generator" claim is not in the cited CMO script or any source found — remove or source it.
