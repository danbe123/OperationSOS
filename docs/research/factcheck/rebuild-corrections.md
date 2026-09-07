# Rebuild section: corrections applied

Round of corrections against the four fact-check reports of 2026-09-07:
`rebuild-a-report.md` (restarting science, making things, iron and tools, power),
`rebuild-b-report.md` (medicine, farming), `rebuild-c-report.md` (library map and the
rebuild module), `rebuild-d-report.md` (first year, keeping the box, essentials printed,
law and trade).

One line per changed claim: **before → after (source)**. 135 claims changed across 18
files. Every `kiwix:` link in every changed file was re-requested against the live
kiwix-serve on 127.0.0.1:8090 before committing: 382 distinct links, all 200, except the
pre-existing `nhs_uk` link on `card:severe-bleeding`, whose ZIM is not synced on this PC.

---

## pages/rebuild-farming.md

1. Calorie base: "one adult doing hard work needs roughly 2,000 kcal a day, about 730,000 a year" → "an adult doing farm work needs roughly 3,000 kcal a day, about 1.1 million a year", with 2,000/2,500 named as average-activity figures (NHS understanding calories, via `page:food-storage`; Wikipedia *Food energy*, *Physical activity level*).
2. Potato energy yield: "about 95 GJ/ha, 9.2 million kcal an acre", cited to *Potato* → recomputed from FAO production and area in the *Potato* article: 22.8 t/ha × 3.2 MJ/kg ≈ **73 GJ/ha**, 7.1 million kcal an acre.
3. Wheat energy yield: "31 GJ/ha, 3 million kcal an acre" → 3.6 t/ha × 13.7 MJ/kg ≈ **50 GJ/ha**, 4.8 million kcal an acre (Wikipedia *Wheat*, *Food energy*).
4. People per acre: "twelve people for potatoes, four for wheat", potatoes ~3× wheat → "about six working adults for potatoes and four and a half for wheat, at 3,000 kcal a day: potatoes lead by half again, not threefold" (arithmetic on 2 and 3).
5. Land budget: "half an acre of cropped ground per person, and as much again" → "roughly an acre of cropped ground per person, and as much again in ley, grass and hay — call it two acres a head" (follows from 1 and 4).
6. Yield planning: "a quarter to a third of modern yields" → "a quarter to a third in the first years, rising towards a half once the leys and the muck are working" (report B).
7. Norfolk rotation: "barley undersown with clover and ryegrass" stated as sourced → "barley, usually undersown with clover…", the undersowing marked as practice rather than as the article's claim (Wikipedia *Norfolk four-course system*).
8. "Never take two grain crops off the same ground in a row" → "avoid two grain crops in a row; the second yields less and carries the disease forward" (rule of thumb, not a rule of nature).
9. Urine feed: "diluted about one part in ten" → "one part in eight to ten, and neat urine burns leaves and roots" (Wikipedia *Urine*).
10. **Night soil (safety):** "thermophilic composting, with the heap genuinely held at 40 to 60 °C, or one to two years of storage" → "**55 °C for at least two weeks, or 60 °C for one week**, probed in the middle of the heap, or **one to two full years of storage with nothing fresh added**"; 40 °C named as mesophilic and inadequate for helminth eggs (Wikipedia *Composting toilet*).
11. **Night soil (safety):** "use aged material on grass, orchards and fibre crops before you ever put it near salad" → "**never on salad or any crop eaten raw, whatever the heap reached**" (WHO multiple-barrier principle).
12. **Urine (safety):** "urine alone, kept separate, is close to sterile" → "carries far less disease than faeces, but it is not sterile, not even in the bladder, and can carry typhoid, leptospirosis and schistosomiasis; store it a month in a closed drum, water it in, keep it off leaves" (Wikipedia *Urine*).
13. Brassica seed saving: no numbers → adds about a mile of isolation and at least a dozen seed plants (Real Seed Catalogue seed-saving notes, named in prose — not in the library).
14. Brassica seed saving: implied all brassicas cross → turnip, swede and oriental greens are *B. rapa* / *B. napus* and will **not** cross with *B. oleracea* (Wikipedia *Brassica rapa*, *Brassica napus*).
15. Beet seed saving: "they need real distance" → "around two miles from any other flowering beet" (Real Seeds, named in prose).
16. Maize: distance only → adds time isolation, staggered sowing, where distance is impossible.
17. Seed store: "hold two years of every important crop" → adds that parsnip, onion and leek seed is worthless after a year or two and must be re-grown annually.
18. Frost date: "nothing tender goes out before mid-May" → "until your own last frost has passed — late May in the south, well into June in the north and on high ground".
19. Hungry gap: "April and May" → "April to early June, from the overwintered brassicas bolting to the first broad beans" (Wikipedia *Hungry gap*).
20. Allotment: "a 10-rod allotment was reckoned to cover a family's vegetables for a year, a useful sanity check on any plan" → "…to keep a family of four in *vegetables*; 250 m² is a sixteenth of an acre, so the staple calories still need the acres above" (Wikipedia *Allotment (gardening)*).
21. Great Famine: "a single potato disease that is still in British soil", cited to *Great Famine (Ireland)* → the endemic clause moved to and cited from *Phytophthora infestans*.
22. Grain storage: "dried to 12 to 13% moisture" → adds the 14.5% food-safety hard line and drying immediately at 18% or more (AHDB grain storage moisture targets).
23. Hens: "a hen fed on grain a person could have eaten is a net loss" → "grain fed to a hen returns less energy than it cost — feed hens on forage, insects, spoiled roots and milling waste", with eggs' protein and fat acknowledged.

## pages/rebuild-medicine.md

24. Semmelweis: "fell from 18% to under 2%" → "from 18% in April 1847 to between 1% and 2% within three months" (Wikipedia *Ignaz Semmelweis*; June was 2.2%).
25. Liverpool: "the engineer who built them" → names James Newlands (Wikipedia *History of water supply and sanitation*).
26. Filtration: "boiling kills everything… a filter takes out mud and parasites but not viruses" → "boiling kills every germ but does nothing about chemical contamination; a filter takes out mud and parasites, only a fine filter around 0.3 micron takes out bacteria, and none reliably removes viruses" (CDC backcountry water treatment).
27. Dental anaesthesia: "lidocaine 2% and long 27-gauge needles" → "2%, usually with adrenaline 1:80,000; long 27-gauge for a block, short 27 or 30-gauge for infiltration", plus "draw back on the plunger before injecting — never into a vessel".
28. **Lidocaine (safety):** mg/kg figures alone → adds the absolute ceilings, "**never more than 300 mg plain or 500 mg with adrenaline however heavy the patient**", plus the 20 mg/ml conversion; early signs corrected to slurred speech, tinnitus and circumoral tingling (StatPearls local anaesthetic toxicity; Wikipedia *Local anesthetic toxicity*).
29. **Ether (safety):** flammability only → adds the flash point of −45 °C and the **peroxide hazard**: ether in light and air forms peroxides that explode when dry, so store dark, stoppered and full, and never distil an old bottle to dryness (Wikipedia *Diethyl ether*).
30. Ether depth: "the false plane of the first minute or two" → named as the excitement stage with laryngospasm, vomiting and vagal arrest, and referred to Guedel's classification by name (Wikipedia *Guedel's classification*).
31. Sterilisation: "a pressure cooker is an autoclave" → "…but only used like one: 15 psi reaches 121 °C, and instruments need at least 30 minutes timed from full pressure" (Wikipedia *Autoclave*).
32. **Tetanus:** "half of those who develop tetanus die even in hospital" → "**about 1 in 10 die even with modern hospital care**, and far more with no ventilator, sedation or antitoxin" (Wikipedia *Tetanus*; CDC).
33. Expired drugs: "tetracyclines being the class to discard" → adds liquid antibiotics, insulin and anything mixed with water (FDA/SLEP via Wikipedia *Shelf life*).
34. Penicillin arithmetic: "100,000 to 200,000 units, about a third of one dose" → "perhaps a fifth to a tenth of one 600 mg dose of benzylpenicillin, which is a million units" (dose assumption made explicit).
35. **Sulfa drugs (safety):** "close to a college chemistry exercise", no hazard → adds Stevens–Johnson syndrome and marrow failure, and the 1937 elixir sulfanilamide disaster, with "the purity is the problem, not the synthesis" (Wikipedia *Stevens–Johnson syndrome*, *Sulfonamide (medicine)*, *Elixir sulfanilamide*).
36. Willow bark: "which Bayer synthesised in 1899" → "which Bayer brought to market as aspirin in 1899" (Wikipedia *Salicin*).
37. Willow bark: "not for children under 16" → names Reye's syndrome, and adds that bark strength varies enormously so the dose is never known: brew weak, stop at the first ringing in the ears (Wikipedia *Reye syndrome*; NHS aspirin).
38. Honey: "preliminary evidence that partial-thickness burns heal four to five days faster" → "**high-quality** trial evidence, about 4.7 days faster" (Cochrane CD005083, via Wikipedia *Honey*).
39. Honey: "it does not work for venous leg ulcers" → "the trials in venous leg ulcers are too weak to say either way" (same review: "unclear… low quality evidence").
40. **Honey (safety):** no infant caveat → "**never give honey by mouth to a baby under twelve months**" (infant botulism), plus prefer filtered honey from a known clean source (Wikipedia *Infant botulism*).

## pages/rebuild-restarting-science.md

41. "the French rejected the idea in 1790" → "the French Academy rejected the idea in **1791**, a year after it was proposed" (Wikipedia *Seconds pendulum*; Talleyrand proposed it in 1790).
42. "the kilogram was originally defined in 1795 as the mass of a cubic decimetre of water" → "the *Kilogramme des Archives* of **1799**… the 1795 law had defined the **gram** the same way, using a cubic centimetre at the ice point" (Wikipedia *Kilogram*).
43. Polaris: "good to a little over half a degree, which is around 60 km, and averaging sights taken twelve hours apart cancels most of it" → "around **70 km**" (0.66° × 111 km/°), and the unobtainable 12-hour pair replaced by a published Polaris correction or many sights across the year (Wikipedia *Polaris*).

## pages/rebuild-making-things.md

44. Ash lye: "a serious caustic in its own right" → "alkaline enough to burn eyes and damage skin on long contact; once strengthened with lime it becomes a true caustic in the same class as drain cleaner" (GHS classifications for K₂CO₃ vs KOH/NaOH).
45. Soap ratio: "a traditional Ozark ratio is about a quart of ash lye to six pounds of fat" (unverifiable) → removed, replaced by the egg-or-potato float test for lye strength plus a small test batch scaled up.
46. **Lye first aid:** "flush any splash with running water for many minutes" → "**at least 20 minutes**", with a separate eye instruction: hold the lids open and keep flushing while somebody fetches help (Wikipedia *Sodium hydroxide*).
47. **Charcoal (safety):** no self-heating warning → "let it cool spread out in the open for a day before bagging; fresh charcoal self-heats and has set fire to the sacks; not reckoned safe until about eight days' exposure to air" (Wikipedia *Spontaneous combustion*).
48. Lime mortar cure: "kept damp and frost-free" → adds "do not lay below 5 °C, and protect from frost for about three months" (Wikipedia *Lime mortar*).
49. Glass furnace: "works around 1,450 °C" → "1,450 to 1,600 °C, hotter still at the burners" (Wikipedia *Soda–lime glass*).
50. **Distilling law:** "requires a licence from HM Revenue and Customs" (implicitly ALDA 1979, repealed 1 August 2023) → "**HMRC approval under section 82 of the Finance (No. 2) Act 2023**; the home-use exemption in **section 84** covers beer, cider and wine but expressly not spirits, so there is no personal-use loophole" (legislation.gov.uk; the Act is not in the `legislation_uk` ZIM, so it is named in prose and the page keeps its *Homebrewing* link).
51. Methanol: rule stated without its reason → adds that ordinary fermentation and distillation do not make dangerous methanol, so the rule is about the *source*, not the technique (Wikipedia *Methanol toxicity*).
52. **Preserving (safety):** "none of them needs a jar that seals" → adds the two botulism exceptions: cured meat needs proper curing salt, and nothing is stored submerged in oil at room temperature (Wikipedia *Curing salt*, *Botulism*).

## pages/rebuild-iron-and-tools.md

53. **Test coupon (safety):** "break it in the vice" → adds eye protection and shielding the far side, because hardened steel shatters and throws fragments.
54. **Fume (safety):** "old plating may be cadmium, which is worse" → "metal fume fever from zinc is a day or two's illness; cadmium fume causes chemical pneumonitis and can kill. **If you cannot tell what the coating is, do not heat it.**" (Wikipedia *Metal fume fever*, *Cadmium poisoning*).
55. **Forge welding:** "common steel of 0.2 to 0.8% carbon welds at a bright yellow heat, pure iron at nearly white, between about 1,400 and 1,500 °C" → the two figures split: "common steel welds at a bright yellow heat, **around 1,300 °C**; pure iron needs nearly white, 1,400 to 1,500 °C. Taking the steel hotter than it needs burns it." (Wikipedia *Forge welding*).
56. **Annealing (safety):** "burying it in dry ash or lime" → "dry **wood ash or vermiculite** — **not quicklime**, which reacts with any moisture and spits caustic slurry at red-hot metal" (Wikipedia *Vermiculite*, *Calcium oxide*).
57. **Quench oil (safety):** no fire rule beside "a can of oil for quenching" → new warning: deep steel container, a lid to drop on and smother, enough oil that it cannot boil, no water in it, no plastic near it, tank clear of the fire.
58. Survivor Library: "some fifty thousand scanned pre-1920s trade books" (unverifiable count) → "tens of thousands".

## pages/rebuild-power.md

59. Hydro output: "enough for a village's lighting, all the charging, a fridge and a pump, with power to spare" → "a few households'…", plus "size the scheme on the flow you measure in a dry August, not February" (report A).
60. Flow measurement: float over a measured length × cross-section → adds the ×0.85 surface-velocity correction.
61. Undershot wheels: "historically managed around 20%" → "around 20% before the 18th century and 50 to 60% once their design was improved" (Wikipedia *Water wheel*).
62. Battery float: "float at around 2.27 V per cell" → adds that this is a flooded battery at 20 °C, with about 0.2 V less on a 12 V battery per 10 °C above that (Wikipedia *Lead–acid battery*).
63. Battery charge: "charge it at about 14.4 V" → adds that this is deliberately above the gassing voltage (hence the ventilation rule) and that sealed AGM and gel want less, nearer 13.8–14.1 V for gel, and are damaged by 14.4 V.
64. Hydrogen: ventilation rule → adds the 4%–75% flammable range in air, and airing after a hard charge before disturbing connections (Wikipedia *Lead–acid battery*).
65. **Fusing (safety):** "a properly rated fuse" → "rated to break DC at the current the bank can deliver — an ANL, MEGA or class-T type, because a blade fuse arcs rather than breaking a battery-bank short".
66. Cable resistance: "2.5 mm² is roughly 0.0067 Ω per metre" → adds "cold, and nearer 0.009 warm and working, so the figures below are the best case" (BS 7671 tabulates 18 mV/A/m at 70 °C).
67. Wood gas: "makes noticeably less power" → quantified: wood gas ~5.7 MJ/kg against petrol's 44.1, expect to lose roughly a third to a half of the power (Wikipedia *Wood gas*).
68. **Gasifier (safety):** no detector → "put a battery carbon monoxide alarm anywhere a gasifier or engine runs near people, and a second one if anyone sleeps nearby" (Wikipedia *Wood gas generator*).
69. Part P: "It is also notifiable work under Part P." → "In **England and Wales** this is likely to be notifiable — a new circuit or a change to the consumer unit certainly is — while Scotland and Northern Ireland have their own building standards" (`doc:ad-p`).
70. **Grid-parallel connection:** absent → new bullet: **ESQCR 2002 reg. 22** requires equipment that disconnects itself when the distributor's supply goes dead plus advance notice to the network operator, in practice **G98** notification up to 16 A per phase or **G99** application and approval above that, before connecting (legislation.gov.uk; the SI is not in the `legislation_uk` ZIM, so it is named in prose and linked to `page:solar-islanding` and *Islanding*).

## pages/rebuild-first-year.md

71. Work order: "shelter and water together, then sanitation…" cited to FM 21-76 p.38 → "Shelter first, then water: in cold weather shelter can outrank both food and water ([FM 21-76, p. 38]). Then sanitation, then food, then security" — the citation now supports only what the page says it does.
72. Slow sand filter: "a bed 1 to 2 m deep run at 200 to 400 litres per square metre per hour" → "about a metre of sand under about a metre of standing water, run at **100 to 300 L/m²/h**", plus "slower is better" and the weeks-long ripening of the biofilm (SSWM/WHO/Huisman; Wikipedia *Slow sand filter*).
73. Boiling: "kills everything including Cryptosporidium" → "kills every germ including Cryptosporidium, though it does nothing about chemical contamination" (CDC/EPA).
74. Water quantity: "about 10 litres once cooking and washing are counted" → "the humanitarian minimum is 15 litres a head a day, and 7.5 is a short-term emergency floor, not a target" (Sphere 2018 WASH 2.1).
75. **Latrines (safety):** 30 m / 50 m only → adds "the bottom of the pit at least 1.5 m above the water table, and further on chalk, limestone or fissured rock" (Sphere 3.2, p.114).
76. 1918 ration: "the 1918 basic ration came to about 1,680 calories" → "the 1918 ration **basket** — sugar, fats, tea, jam and meat — came to about 1,680 calories **on top of bread, which was never rationed**" (Wikipedia *Rationing in the United Kingdom*).
77. Ration figures: 2,000/2,500 presented flat → keeps them as ordinary-activity figures and adds "anyone doing farm or building work all day needs nearer 3,000", cross-linked to `page:rebuild-farming` so the two pages agree.
78. Potato yield: "roughly 1.7 kg per square metre at world average yields" → "roughly **2.2 kg per square metre**" (FAOSTAT 2024: 22.86 t/ha).
79. Potato claim: "the most food energy per area of any staple" → "more food energy per acre than any **cereal**" (CIP: two to four times the food quantity of grain crops).
80. Allotment: "sized to cover a family's vegetables for a year" → "…a family of four in vegetables, not staple calories, which need the acres on `page:rebuild-farming`".
81. Charcoal indoors: cited to Approved Document J → the CO rule now cites `card:carbon-monoxide`, and AD-J is cited only for fixed appliances' flues, air supply and alarms (AD-J covers fixed appliances, not the charcoal rule).
82. Burial lawfulness: "no law forbids burying a body on private land, but the landowner must agree" → "no **statute** forbids it, but the Environment Agency's distances are binding, planning and the deeds may constrain it, and environmental health should be told as soon as one can be reached".
83. **Burial distances (safety):** "as far from every well, borehole, spring and watercourse as the ground allows" → the Environment Agency's binding figures: **250 m** from any well, borehole or spring used for drinking water or food production, **30 m** from any spring or watercourse, **10 m** from any field drain or dry ditch, **1 m** of dry ground above the water table; with the explicit note that the 30 m latrine rule would put a grave eight times too close to a well (EA, *Protecting groundwater from human burials* and the low environmental risk cemeteries exemption — not in the library, so named in prose).
84. Epidemics: "bodies do not start epidemics" → "bodies of people who died of **injury** do not start epidemics", with cholera, dysentery and haemorrhagic fever called out for gloves, wrapping and distance from water (Sphere 2018 Health).
85. Hungry gap: "in April, not in January" → "from April into early June".

## pages/rebuild-keeping-the-box.md

86. Hardware spec cited to `page:about-sos`, which carries none of it → attributed in prose to the box's own README hardware table, which is the authority; the `about-sos` citation is kept only for the 8–15 hour runtime, which that page does carry.
87. Power supply: "a 27 W USB-C unit, but that is the headroom the Pi is allowed to draw" → "27 W, which delivers **25.5 W** at 5.1 V; the Pi's own typical figure is **4 W**, peaks around 12 W, and the official screen adds about **1 W**" (raspberrypi.com docs).
88. Power bank arithmetic: "perhaps 60 [Wh] survive the conversion… 4 to 5 W screen-off and 6 to 8 W lit" → "perhaps **45 to 60** survive… call it **4 to 5 W dark and 5 to 6 lit**, plus the drive".
89. Battery station: "runs it for about two days" → adds that this is on the DC/USB-C output, and that the AC inverter costs both conversion loss and a constant overhead.
90. Irradiance: "about 0.5 kWh/m²/day in December against 4.7 in July" → "**0.6** against **5.1**" (PVGIS v5.3 SARAH3, London horizontal, 2016–2023 mean).
91. LiFePO4: "tolerates 2,500 to more than 9,000 charge cycles" → "roughly 2,500 cycles at 80% depth of discharge and about 5,000 at 50%" (Victron LFP Smart datasheet).
92. SD cards: "cards are the part that fails first in a Raspberry Pi" → "a known wear-out item, and Raspberry Pi's own guidance recommends replacing them on a schedule" (RP-003610-WP).
93. Drive retention: "charge leaks away over years" → adds the numbers: one year at 30 °C for a worn-out consumer drive, roughly halving every 5 °C warmer, and "power every spare drive up **at least** once a year, sooner if heavily written" (JEDEC JESD218 / JC-64.8).
94. Faraday cage: "blocks external electric fields" → "blocks **some** electromagnetic fields — not steady magnetic ones, and only where the gaps are small compared with the wavelength"; the hedge about "not a sourced fact" replaced with CISA's EMP guidelines on metal bins and on wrapping items in insulation then two or more overlapping layers of heavy-duty foil.
95. Library size cited to `page:about-sos`, which carries neither figure → attributed to the manifest and the README hardware table in prose (core 203.5 GB, extended 664 GB, external drive 2 TB or more).
96. Copy commands: `rsync -av --partial --progress` described as resuming and copying only what changed → `rsync -avP --partial-dir=.rsync-partial`, with the explanation that a local-to-local copy sends whole files by default, that the match is on size and date, and with the `sha256sum` **generation** step and the working-directory requirement both shown.

## pages/rebuild-essentials-printed.md

97. Bow drill: "a hearth board of dry softwood" (contradicting `page:fieldcraft-fire`) → "dry, soft, non-resinous wood — lime, willow, sycamore or ivy, not conifer".
98. **Rainwater (safety):** "rain off a clean sheet, which needs no treatment" → "rain caught off a clean sheet, **treated like any other water**. Never drink runoff from a roof, gutter or downpipe." (CDC rainwater collection; also fixed in `page:fieldcraft-water`, below).
99. **Improvised filter (safety):** "filter through clean cloth or a bed of sand and gravel, which takes out mud and parasites but not viruses" → "takes out mud and makes the disinfection work — **it does not make the water safe, and it does not remove parasites**. Boil or chlorinate afterwards, always." (the parasite property belongs to the 0.1–0.2 micron row of `page:water-disinfection`; a schmutzdecke takes weeks to months).
100. Boiling: "kills everything" → "kills every germ… nothing here touches chemical contamination".
101. **Chlorination:** "double both if cloudy or cold" → "double **the bleach**, not the wait", plus the faint-chlorine smell check and a repeat dose with a further 15 minutes (CDC; EPA; matches `page:water-disinfection`).
102. **Latrines (safety):** 30 m / 50 m only → adds the 1.5 m water-table clearance and the fissured-rock caveat.
103. Handwashing: 20 seconds cited to the CMO outage script, which does not carry it → now cited to *Hand washing*.
104. Fouled surfaces: "one part 5% thin bleach to nine parts water" → "mop up with paper, clean with hot water and detergent, then one part in **fifty** (the NHS norovirus strength, 1,000 ppm); one in nine only for cholera or a known blood-borne risk" (UKHSA/DH norovirus guidance).
105. **Severe bleeding (safety):** "press hard and do not let go for at least 10 minutes" → "keep pressing; if it is not coming under control within a couple of minutes, escalate — do not wait out a fixed time" (the 10-minute rule is the nosebleed rule; RCUK 2025 sets an escalating approach).
106. **Severe bleeding (safety):** "if blood soaks through, add more on top, never removing the first pad" → "**take that pad off and press again with a fresh one — a sodden pad is not pressing on anything**" (St John Ambulance, severe bleeding).
107. **Severe bleeding (safety):** "pack a deep wound in the groin, armpit or neck" → "pack the groin or armpit; **for the neck, press directly on the wound, do not pack it and never put anything round the neck**" (airway compression and air embolism).
108. Tourniquet: adds RCUK 2025's two omitted lines — do not loosen it, and put a second one above the first if one is not enough.
109. CPR breaths: "2 breaths of a second each" → "each just big enough to make the chest start to rise" (RCUK 2025 is volume-based, not time-based).
110. CPR: "swap every two minutes" (unsupported) → "swap with someone else when you tire".
111. Recovery position: adds RCUK 2025's exclusion — not for agonal breathing or trauma.
112. Germination test: "counted after a week" → "count after a week, then again at three weeks", with the crops that take two to three weeks named and the count converted into a sowing rate.
113. **Soap (internal contradiction):** "pour into a mould, cut, and cure it for weeks" from wood-ash lye → "**wood-ash lye is potash lye and it makes soft soap — a jelly, not a bar**; a hard bar needs soda lye, historically by salting out the potash liquor" (Wikipedia *Soap*).
114. **Lye first aid:** "flood any splash with water" → "brush off dry powder first, then flood for a **full hour**, removing contaminated clothing while flooding; for eyes hold the lids open; put nothing else on it — no cream, no vinegar, no neutraliser" (NHS acid and chemical burns).
115. **Quicklime slaking (safety):** "a litre of water takes about 3.1 kg of quicklime and gives out about 3.54 MJ" — the stoichiometric minimum, pointing the reader at the least water and the most violent reaction → "use a generous excess, at least two or three litres of water per kilogram of quicklime, in a deep vessel no more than a third full"; energy corrected to **1.16 MJ per kg** and **3.6 MJ** for the 3.1 kg case, against the 2.6 MJ needed to boil the litre away; "never slake in a sealed or narrow-necked container" (NIST WebBook ΔfH°: CaO −635.09, Ca(OH)₂ −986.09, H₂O(l) −285.83 → −65.17 kJ/mol).
116. Slaked lime: "keeps for months under water" → "keeps **indefinitely** under water and improves with age" (Wikipedia *Lime mortar*).
117. Charcoal: "burns far hotter than wood" → quantified at 30–36 MJ/kg against wood's 15–18, with the ~25% by weight yield added (FAO).
118. **Charcoal (safety):** "let it cool sealed before opening: fresh charcoal reignites in air" → adds the actionable eight-day figure and the day spread out in the open before bagging (Wikipedia *Spontaneous combustion*).
119. Seconds pendulum: "0.994 m at ordinary British gravity" (0.994 m implies g = 9.810; British g is 9.812–9.818) → "about 0.994 m", with the instruction to adjust the length until it beats seconds against the sun.
120. Boiling point: "falls as pressure drops" → adds "roughly 1 °C for every 300 m of height" (Wikipedia *Boiling point*).

## pages/rebuild-law-and-trade.md

121. **Emergency powers:** "emergency regulations under the Civil Contingencies Act 2004 are **the only lawful route**" → "one route, and public health law is another — the 2020 lockdowns were made under **PHCDA 1984 s.45C**" (legislation.gov.uk; Wikipedia *Public Health (Control of Disease) Act 1984*).
122. **Emergency powers:** "they lapse after 30 days unless Parliament renews them" → "**both Houses must approve them within 7 days** of laying or they lapse, and they lapse anyway at 30 days — there is no renewal power, only fresh regulations" (CCA ss.26–27; `module:security-law` already stated the 7-day rule).
123. Citizen's arrest: "detaining someone briefly… is a citizen's arrest with narrow conditions" → brief restraint rests on the **common law breach-of-the-peace** power; a citizen's arrest proper needs an indictable offence that actually happened (honest suspicion is not enough, *R v Self*), with no power at all for summary offences, and only where a constable cannot realistically do it (PACE s.24A; CPS).
124. LASPO squatting: "a £5,000 fine" → "an **unlimited** fine — capped at £5,000 only until 12 March 2015" (LASPO s.85(1); SI 2015/664).
125. Adverse possession: "65 business days" → "65 **working** days" (HMLR Practice Guide 4; LRR 2003 r.189 as amended).
126. Adverse possession: "a counter-notice… normally defeats the application" → "usually but not always: the squatter still wins on any of three grounds, including a reasonable mistaken boundary belief, and may reapply after two years" (LRA 2002 Sch 6 para 5).
127. Adverse possession: unregistered land missing entirely → adds twelve years barring the owner's claim outright, with no notice and no counter-notice, under the Limitation Act 1980 s.15, and that much rural land is still unregistered.
128. **Self-defence:** "reasonable force is lawful in defence of yourself, another person **or property**… ([CLA 1967 s3])" → s.3 covers only preventing crime and lawful arrest; defence of the person is common law; defence of property is narrower still and gives no defence against a trespasser committing no crime (CPS self-defence guidance).
129. **Householder defence:** "force is unlawful **only** if it is grossly disproportionate" → "grossly disproportionate force is never lawful, **and force short of that must still be reasonable** in the circumstances as you honestly believed them" (*R v Ray* [2017] EWCA Crim 1391), plus the two missing limits: it covers defending **people** inside the dwelling, not property and not the garden (CJIA 2008 s.76(5A), (8A)).
130. Knives: "a folding non-locking knife **under** 3 inches" → "with a cutting edge of **3 inches (7.62 cm) or less**" — s.139 bites only where the edge *exceeds* 3 inches, and the box's own `page:knife-firearms-law` already said so (CJA 1988 s.139(3)).
131. FSCS: "per person per banking group… paid within days; joint accounts count double" → adds the stable shape: per eligible person per group, **not per account**; about seven working days for most claims; temporary high balances take longer; and the limit itself changes, so check it rather than memorise it.

## pages/rebuild-library-map.md

132. Medicine and Surgery sections did not mention `zimgit-medicine_en` at all → the **Medical Library (zimgit)** added to both, linked as `kiwix:zimgit-medicine_en/home` (path verified 200 on 127.0.0.1:8090 before linking).
133. Metalwork section did not mention the Survivor Library, which `page:rebuild-iron-and-tools` already recommends → added as a fourth, extended-tier line, naming its manifest id `survivorlibrary.com_en_all` in prose. **Not linked**: the ZIM is not on this PC and the link scheme requires `<id>/<path>`, so no article path could be verified.

## modules/rebuild.md

134. "plan for a quarter to a third of modern yields once industrial nitrogen is gone" → adds "rising towards a half once the leys and the muck are working" and "do the calorie sum on 3,000 kcal a day for anyone working the land, not on 2,000", so the module and `page:rebuild-farming` agree.

## Inherited errors fixed in pages already in the box

135. `pages/fieldcraft-water.md`: "rain… needs no treatment if the sheet was clean" → "rainwater is not automatically safe to drink, so treat it like any other water, and never take runoff from a roof, gutter or downpipe"; the `{{#unless water}}` branch's "rain caught off a clean sheet or a butt" now reads "…and then treated" (CDC; matches `page:water-disinfection`).
136. `cards/severe-bleeding.md`: step 3 "keep pressing for at least 10 minutes without lifting to look" → "not stopping in a couple of minutes? Escalate, do not wait it out" (kept under the 70-character one-screen limit); step 4 "add more on top; never remove the first pad" → "take that pad off and press with a fresh one"; step 5 neck packing removed in favour of direct pressure; step 6 gains the second tourniquet; a new `**Warning:**` states both rules; the Source line names St John Ambulance and RCUK 2025 as the authority, noting they are not in the library.
137. `pages/solar-islanding.md`: "0.5 kWh/m²/day in December and 4.7 in July" and, in the severe-winter branch, "0.7… against 5.2" — three different pairs across the box → both reconciled to **0.6 and 5.1** (PVGIS); LiFePO4 "2,500 to more than 9,000 cycles" → "roughly 2,500 at 80% DoD and about 5,000 at 50%".
138. `pages/death-and-grief.md`: "EA guidance sets minimum distances… treat the figures here as the floor. As the floor, apply the latrine rule: at least 30 metres" → the EA figures now stated in full (250 m / 30 m / 10 m / 1 m above the water table), matching `page:rebuild-first-year`.
139. `modules/security-law.md`: householder force "unlawful only if grossly disproportionate" → the *R v Ray* test plus the people-not-property, not-the-garden scope; "a folding non-locking knife under 3 inches" → "3 inches (7.62 cm) or less".
140. `pages/knife-firearms-law.md`: CLA 1967 s3 described as covering defence of self, others or property → corrected to prevention of crime and lawful arrest, with common law for the person and a narrower rule for property; both statements of the householder test corrected to the *R v Ray* wording.

---

## Left unresolved, and why

- **Legislation not in the `legislation_uk` ZIM.** That ZIM is a curated extract, not the whole corpus: Finance (No. 2) Act 2023 ss.82/84, ESQCR 2002 reg. 22, PHCDA 1984 s.45C, LASPO 2012 s.144, Limitation Act 1980 s.15 and CCA 2004 ss.26/27 all return 404 on the local kiwix (only `ukpga/2004/36/contents` is present for the CCA). Each is therefore **named with its Act and section in the body text**, linked to the nearest article that *is* in the library. Adding them to the ZIM is a manifest/build job, not a content one.
- **Survivor Library not linked.** `survivorlibrary.com_en_all` is in `manifest/extended.json` but the ZIM is not on this PC, and the link scheme requires `kiwix:<id>/<path>` — a path could not be verified, so the library map names the item and its manifest id in prose instead.
- **Environment Agency burial guidance and St John Ambulance / RCUK 2025 first-aid guidance are not in the library.** The figures and the teaching are recorded in the pages with the source named in prose, and both pages say so explicitly, as `page:death-and-grief` already did. Both would be worth adding to the manifest.
- **README hardware table is not a `doc:` item.** `page:rebuild-keeping-the-box` therefore states the Pi/drive/screen spec and the library sizes with their source named in prose (the box's own README and manifest) rather than mis-citing `page:about-sos`. The alternative fix — adding the spec to `page:about-sos` so the citation resolves to the claim — was not taken, to keep this round to corrections rather than new content.
- **Book-cited claims in `page:rebuild-medicine`** (Where There Is No Doctor, Where There Is No Dentist, Survival and Austere Medicine) were marked UNCHECKED in report B because those PDFs are not on this machine. They are unchanged except where the report gave an independent correction (lidocaine caps, ether peroxides, autoclave timing, penicillin dose arithmetic, sulfa hazards).
- **`nhs_uk` ZIM is absent on this PC**, so the pre-existing `kiwix:nhs_uk/www.nhs.uk/conditions/cuts-and-grazes/` link on `card:severe-bleeding` could not be re-requested. It is in the manifest and passes validation; it was left alone.
- **Report C's minor note that OpenStax Chemistry has no narrowing page anchor** in the library map was not acted on: no specific page range was identified, and guessing one would be worse than the current whole-book link.

## Verification

- `api/.venv/bin/python -m pytest api/tests -q` → **1283 passed**.
- `SOS_PLAYBOOKS_DIR=playbooks SOS_MANIFEST_DIR=manifest api/.venv/bin/sos validate-playbooks --all-scenarios` → **OK 131 documents**.
- All 382 distinct `kiwix:` targets in the 18 changed files requested against the live kiwix-serve: all 200 except the absent `nhs_uk` ZIM.
