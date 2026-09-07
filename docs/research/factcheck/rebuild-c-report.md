# Rebuild library map + rebuild module — factcheck report

Checked against a live `kiwix-serve` on :8090 (urlRoot `/kiwix`), `manifest/core.json` /
`manifest/extended.json`, PDFs under `~/sos-content/docs` (page counts via `pypdf`, no
`pdfinfo` on this box), and files under `playbooks/`.

## 1. Links

83 distinct `kiwix:` links, 17 distinct `doc:` ids, and ~45 `page:`/`module:`/`card:` ids
appear across the two source files. Every one resolves. Table below is the library map's
"three things per domain" plus the header/footer links; full anchor lists (Wikipedia
anchors under each domain) all returned 200 and are omitted for space.

| Link | Status | Note |
|---|---|---|
| module:water, page:water-disinfection | 200 / file exists | — |
| kiwix:zimgit-water_en/home | 200 | title "Water Treatment Library" |
| module:sanitation | file exists | — |
| doc:fm-4-25-12-field-sanitation | in core.json | — |
| doc:ad-h | in core.json | title "Drainage and waste disposal" — matches |
| page:rebuild-medicine | file exists | — |
| doc:where-there-is-no-doctor, doc:where-there-is-no-dentist | in core.json | — |
| doc:survival-austere-medicine-2017 | in core.json | — |
| module:medical, card:severe-bleeding/wound-cleaning/wound-closure/sepsis | files exist | — |
| doc:fm-4-25-11-first-aid | in core.json | — |
| doc:emergency-war-surgery-2018, doc:st-31-91b-sf-medical-handbook | in core.json | — |
| page:rebuild-farming, module:growing-food, module:livestock | files exist | — |
| kiwix:gardening.stackexchange.com_en_all/questions | 200 | — |
| kiwix:cd3wdproject.org_en_all/.../GRNSTOR3.HTM | 200 | title "STORAGE METHODS" — matches "grain storage" claim |
| page:rebuild-making-things | file exists | — |
| kiwix:appropedia_en_all/Welcome_to_Appropedia | 200 | — |
| doc:openstax-chemistry-2e | in core.json, 1203pp | no page anchor used, nothing to check |
| kiwix:chemistry.stackexchange.com_en_all/questions | 200 | — |
| page:rebuild-iron-and-tools, module:tools-repair | files exist | — |
| kiwix:ifixit_en_all/home/home | 200 | title "iFixit: The Free Repair Manual" — good fit |
| kiwix:engineering.stackexchange..., kiwix:woodworking.stackexchange... | 200 each | — |
| page:rebuild-power, module:power, module:comms, page:what-still-works | files exist | — |
| kiwix:electronics.stackexchange..., kiwix:ham.stackexchange..., kiwix:energypedia_en_all_maxi/Main_Page | 200 each | — |
| doc:rsgb-band-plan-2026, page:amateur-bands | in core.json / file exists | RSGB doc confirmed a real 2026 band plan |
| doc:ad-a, doc:ad-b1, doc:ad-j | in core.json | — |
| kiwix:diy.stackexchange..., kiwix:wikibooks_en_all_maxi/Do-It-Yourself | 200 each | — |
| doc:openstax-prealgebra-2e, doc:openstax-college-physics-2e, doc:openstax-introductory-statistics-2e | in core.json | — |
| kiwix:wikibooks_en_all_maxi/Subject:Mathematics, .../Subject:Physics | 200 each | — |
| page:rebuild-keeping-the-box | file exists | — |
| kiwix:wikibooks_en_all_maxi/Wikijunior, .../Main_Page | 200 each | — |
| kiwix:wikipedia_en-simple_all_maxi/Main_Page | 200 | — |
| page:rebuild-law-and-trade, module:security-law, page:knife-firearms-law | files exist | — |
| kiwix:legislation_uk/.../ukpga/2004/36/contents, .../2008/4/section/76 | 200 each | — |
| kiwix:zimgit-post-disaster_en/home | 200 | title "Post Disaster Resource Library" |
| kiwix:wikiciv_en_all/Main_Page | 200 | 326 articles, "wiki manual for building civilization from scratch" |
| kiwix:wikipedia_en_all_maxi/Water_purification (all-3-things anchor) | 200 | — |
| doc:nrr-2025#page=22 | in core.json, PDF has 187 pages (matches manifest description) | page 22 text quoted verbatim, see §3 |

All 83 `kiwix:` anchor links in the "Anchors:" lines under each domain (Water_purification,
Slow_sand_filter, Blacksmith, Tempering_(metallurgy), Parish_council_(England), etc.,
including the ones with literal parentheses in the title) returned **200**, none redirected.
All 17 `doc:` ids are present in `manifest/core.json` or `manifest/extended.json`. All
`page:`/`module:`/`card:` ids referenced have a matching file under `playbooks/pages`,
`playbooks/modules` or `playbooks/cards`.

## 2. Reading-quality judgement

| Domain | Reading | Verdict |
|---|---|---|
| Water | module:water; page:water-disinfection; zimgit-water_en | Correct scale-up: household action → dosing table → village-scale treatment library. Good. |
| Sanitation | module:sanitation; FM 4-25-12; AD H | FM 4-25-12 is a real US Army field-sanitation manual (camp hygiene); AD H is drainage/cesspools/septic tanks — title matches exactly. Good progression. |
| Medicine | page:rebuild-medicine; WTIND; Survival & Austere Medicine (+ WTI-Dentist) | WTIND is the standard village medical handbook; SAM covers the harder end (confirmed: its own pages on anaesthesia, penicillin arithmetic, etc. are accurately quoted elsewhere in the pack). Good, but see gap below. |
| Surgery/first aid | module:medical + cards; FM 4-25-11; Emergency War Surgery (+ SF Medical Handbook) | Correct escalation from illustrated drills to hospital-less triage/damage control. Good. |
| Farming and food | page:rebuild-farming; growing-food/livestock modules; Gardening Q&A + CD3WD (grain storage) | Grain-storage sub-link opens directly on the right VITA "STORAGE METHODS" document. Good, specific. |
| Materials/chemistry | page:rebuild-making-things; Appropedia; OpenStax Chemistry + Chem Q&A | Appropedia is genuinely built-and-tested appropriate tech, as claimed. OpenStax Chemistry is 1203pp of general theory — a big ask for "the theory"; no page anchor is given to narrow it, unlike almost every other doc: reference in the pack. Minor weakness, not wrong. |
| Metalwork/engineering | page:rebuild-iron-and-tools; tools-repair + iFixit; Engineering/Woodworking Q&A | iFixit is a genuine large repair-guide corpus, matches "keeping what exists working." **Gap**: rebuild-iron-and-tools.md itself recommends the extended-tier Survivor Library ("~50,000 pre-1920s trade books, including blacksmithing, farriery, edge-tool making") but the library map's Metalwork picks (and its anchors) never mention it, even as a fourth "if you have the extended shelf" line — a clearly better deep reference for this specific domain that the map is silent on. |
| Electricity/radio | page:rebuild-power + module:power; module:comms + what-still-works; Electronics/Ham Q&A + Energypedia; RSGB band plan | Coherent path from theory to law. RSGB PDF is real and dated 2026, matches doc id. Good. |
| Building | AD A; AD B1 + AD J; DIY Q&A + Wikibooks DIY | AD A confirmed "how much a wall, beam or roof will carry" (structure); AD B1 confirmed escape/fire; correct order (structure before finishes). Good. |
| Maths/physics | OpenStax Prealgebra; OpenStax College Physics; Wikibooks Maths/Physics + Intro Statistics | Arithmetic → mechanics/heat/electricity → teaching material + stats — sound order, and both OpenStax figures used elsewhere in the pack (pendulum length, hydro power) are drawn correctly from College Physics-level material. Good. |
| Teaching children | page:rebuild-keeping-the-box; Wikijunior/Wikibooks; Simple English Wikipedia | Reasonable, though item 1 is really about *why* to teach from the library rather than a teaching resource itself — a thinner fit than the other domains' item 1s, most of which are actionable pages. |
| Law/records/history | page:rebuild-law-and-trade; security-law + knife-firearms-law; UK legislation (CCA 2004) | Confirmed CCA 2004 and CJIA 2008 s.76 are the correct, currently-cited Acts for emergency powers and householder self-defence respectively (cross-checked against rebuild-law-and-trade.md, which cites the same sections accurately). Good. |
| "If you can only keep three" | zimgit-post-disaster; WTIND; Wikipedia (+ WikiCiv) | Sound triage of the whole library into three items. |

**Most important quality finding:** `zimgit-medicine_en` ("Medical Library (zimgit)" — "Curated
public-domain medical PDFs including field first-aid and austere care guides", core tier,
tagged for scenario `long-rebuild` in the manifest) is not mentioned anywhere in the Medicine
or Surgery/first-aid sections of the library map, nor in their anchors, despite being a closer
match to "field and emergency medicine" than some of what is listed. It resolves fine
(`kiwix:zimgit-medicine_en/home`, 200) — it is simply absent from the map.

## 3. Module timeline/checklist vs. long-rebuild scenario and the 11 rebuild pages

| Module claim | Verdict | Note |
|---|---|---|
| "Recovery ... can last months, years or even decades" ([NRR 2025, p. 22]) | **Confirmed accurate** | PDF page 22 (index 21, footer "National Risk Register 2025 / 22") reads verbatim: "Recovery from a serious incident can last months, years or even decades." Same page also supports "works best where the affected community takes part in deciding how." Identical citation used correctly in long-rebuild.md and rebuild-first-year.md. |
| "Liverpool's life expectancy was 19 years before its sewers and had more than doubled within a working lifetime after them" | **Confirmed accurate, verbatim** | `History_of_water_supply_and_sanitation` reads: "life expectancy in Liverpool was 19 years, and by the time Newlands retired it had more than doubled." Identical figure reused correctly in rebuild-medicine.md. |
| First month → first year → years 1–3 (food/health) → years 3–10 (trades/power) → decade after | **Consistent** | Matches long-rebuild.md's own "Year one to three: food and health" / "Year three to ten: trades and materials" headings, and matches the internal order in rebuild-first-year.md, rebuild-farming.md and rebuild-iron-and-tools.md (blacksmithing on scrap before any bloomery, which both pages independently push out to "the far future"/"generations away", i.e. consistently beyond the year-10 horizon). |
| Order of work: shelter+water, then sanitation, then food, then security | **Consistent** | Same order stated in long-rebuild.md and rebuild-first-year.md, both citing FM 21-76 p.38 for the shelter-before-food point. |
| "plan for a quarter to a third of modern yields once industrial nitrogen is gone" | **Confirmed accurate** | rebuild-farming.md derives this from the same Wikipedia figures: 1890s wheat yield "30 bushels an acre... 2,080 kg a hectare" is verbatim from `British_Agricultural_Revolution` ("averaging 30 bushels per acre (2,080 kg/ha) by the 1890s"), against a modern ~8 t/ha, i.e. roughly a quarter to a third. The "8 bushels" 1300s figure is also consistent with that article's yield table (8.24–8.71 bushels/acre for 1250–1349). |
| Potato/wheat energy-yield figures used in rebuild-farming.md (95 GJ/ha vs 31 GJ/ha; 9.2M vs 3M kcal/acre) | **Confirmed accurate, verbatim** | Matches the `Potato` article's figures exactly. |
| Checklist ordering (hour → today → week tags) | **No contradiction found** | Same relative priority (playbook-for-the-cause first, box/ledger next, water/latrines/food/skills within the week) as long-rebuild.md's own checklist, which uses an equivalent now/today/week scheme. |
| "Two people apprenticed to each of midwifery, wound care, teeth and the pharmacy" (module checklist) vs "a midwife and a first-aider trained" (long-rebuild.md checklist) | **Consistent, not contradictory** | Different granularity (module is decade-scope and more demanding; long-rebuild.md's checklist item is a first-month minimum), not a conflicting figure. |
| Burial/latrine distances | **No numeric contradiction, but inconsistent specificity** | long-rebuild.md gives explicit burial distances (250 m from a well/borehole/spring used for drinking water, 30 m from any other watercourse, 10 m from a field drain); rebuild-first-year.md and the module both stay qualitative ("as far... as the ground allows"). Not wrong, but a reader bouncing between the module and rebuild-first-year.md gets no number where long-rebuild.md has one — worth aligning if these pages are meant to be interchangeable entry points. |

## Counts

- Links checked: 83 `kiwix:`, 17 `doc:`, ~45 `page:`/`module:`/`card:` = **145 total, 0 broken** (0 non-200, 0 missing manifest ids, 0 missing files).
- PDF page-anchor check: 1 anchor in rebuild.md (`nrr-2025#page=22`) — valid and quote-accurate.
- Domains judged: 12 numbered domains + "if you can only keep three" = 13, all readings on-topic and correctly ordered (general → specific or news → handbook → deep reference).
- Module timeline/checklist claims checked against the 11 rebuild pages + long-rebuild.md: 9 checked, 0 contradictions, 2 confirmed-accurate figures/quotes verified against source text, 1 specificity mismatch (burial distances) noted as a possible tidy-up rather than an error.

## Most important fixes

1. **Add `zimgit-medicine_en` ("Medical Library (zimgit)") to the Medicine and/or Surgery-and-first-aid sections of the library map.** It is a core-tier, `long-rebuild`-tagged item of exactly the field/austere-medicine PDFs those two sections are about, and it is currently invisible from the map entirely.
2. **Add the Survivor Library as a fourth, extended-tier line under Metalwork and engineering** (or at least an anchor), since rebuild-iron-and-tools.md already tells the reader it exists and is worth copying, but the library map — the page whose whole job is to say what to read — never surfaces it there.
3. **Optional tidy-up:** give rebuild-first-year.md's burial-siting paragraph the same explicit distances (250 m / 30 m / 10 m) that long-rebuild.md already states, so the two pages agree in specificity as well as substance.

No broken links, no inaccurate figures, and no real contradictions were found in the timeline or checklist; the issues above are gaps and polish, not errors.
