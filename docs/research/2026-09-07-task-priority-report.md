# The to-do list, prioritised: what was authored

Date: 2026-09-07. Against docs/superpowers/specs/2026-09-07-task-priority-design.md, on the engine
of commit 37ff49a. Twenty scenario checklists re-authored as sequences, `playbooks/rules/tasks.yaml`
made scenario-aware. `sos validate-playbooks --all-scenarios` prints OK; `pytest api/tests` passes.

## How the list is ordered

Bucket first (`now`, `hour`, `today`, `week`), then `rank`, then the order things were written in:

| rank | what sits there |
|---|---|
| 10 | a scenario's leading branch: the thing that kills or the mistake to head off first (15 rules) |
| 100 | the running scenario's own checklist, in the order its author wrote it |
| 110 | a scenario's conditional refinements — what a fixed line cannot say because it depends on which services are up (27 rules) |
| 150 | the generic housekeeping (15 rules): fridge doors, cooker, CO alarm, the bath, charging, and the rest |

With no scenario running, every rule in `tasks.yaml` shares rank 150, so the generic list reads in file
order exactly as it did before. `unless: {scenario: [...]}` stands a generic job down entirely in the
scenarios whose own checklist already carries it (nuclear war's "mains off" supersedes `cooker-off`).

## Per scenario: the `now` items in order, and the rules added

### nuclear war — 13 items (6 now, 4 hour, 2 today, 1 week)

1. `stay-48-hours` — Everyone and the pets in, doors shut: nobody leaves the house for 48 hours, then reassess by radio
2. `mains-off-windows-shut` — Gas and electricity off at the mains, any fire damped, every window, door and vent shut, curtains drawn
3. `decontaminate-at-door` — Anyone who was outside: outer clothes off and bagged at the door, then wash hair and skin
4. `radio-and-light` — Radio on and left on, torch and spare batteries beside it, candles and matches out of the way
5. `choose-fallout-room` — Into the fall-out room: basement or ground-floor middle room, fewest outside walls
6. `fourteen-days-water-food` — Water and food carried in: 3 litres a person a day, 14 days of it, covered, and tinned food that needs no cooking

Rules added:

- `nuclear-war-mains-off-now` (rank 110, power: working) — Turn the gas and electricity off at the mains while you can still see to do it → page:mains-electricity
- `nuclear-war-water-in-first` (rank 110, water: working) — Carry the water in before you shut the room: 3 litres a person a day, covered → module:water
- `nuclear-war-radio-is-the-all-clear` (rank 110, phones: off) — The wind-up radio is the only all-clear you will get: keep it on and write down each bulletin → page:no-phones

### nuclear accident — 10 items (4 now, 4 hour, 2 today, 0 week)

1. `go-in-stay-in` — Everyone and the pets into the nearest building, not home if home is a journey; doors and windows shut, fans, extractors and the boiler off
2. `tune-in` — Radio on; Emergency Alerts switched on in every phone; nobody goes out to collect children, who are kept in and told what to do
3. `decontaminate` — Anyone who was outside: outer clothes bagged at the door, shower, no conditioner
4. `site-and-wind` — Nearest nuclear site found on the map and the wind direction from it noted

Rules added:

- `nuclear-accident-shelter-nearest-building` (rank 110, always, while the scenario runs) — Shelter in the nearest building, not at home if home is a journey away → module:radiation
- `nuclear-accident-leave-the-children` (rank 10, always, while the scenario runs) — Do not go out to collect children from school or nursery → module:radiation

### pandemic — 11 items (6 now, 0 hour, 4 today, 1 week)

1. `sickroom` — Anyone ill into one room, door shut and window open, own bathroom or a lidded bucket
2. `one-carer` — One carer named and a second in reserve; mask on (FFP2 or FFP3 if you have them), gloves and apron at the door
3. `hand-washing` — Hand-washing station at the door: 20 seconds of soap and water after every contact, and a separate cup, plate, towel and bedding
4. `sickroom-kit` — Rehydration salts mixed and to hand; paracetamol, thermometer, oximeter and bleach in the room
5. `red-flags-on-wall` — Emergency signs on the wall: breathless, blue lips, confused, no urine, rash that does not fade
6. `single-runner` — Non-essential trips stopped; one person does all outside errands and strips and washes at the door

Rules added:

- `pandemic-hand-washing-without-mains` (rank 110, water: ['degraded', 'off']) — Hand washing is a jug poured over a bowl after every contact, gel only as a stopgap → module:sanitation
- `pandemic-999-on-foot` (rank 110, phones: off) — Agree now who runs for an ambulance, and where to, if someone cannot finish a sentence → page:no-phones

### grid collapse — 12 items (6 now, 3 hour, 2 today, 1 week)

1. `call-105` — {{#if phones}}Trip switches checked, then 105 called (GB) or NIE 03457 643 643 (NI); note what they say and when{{else}}Trip switches checked; the time the power went and how far the dark street runs written down, because nobody can be told until a phone works{{/if}}
2. `torch-radio-powerbank` — Torch out, radio on BBC local FM, phone brightness down, power bank found
3. `fill-water` — Kettle, pans, bottles and bath filled while the water still runs
4. `fridge-freezer-shut` — Fridge and freezer doors shut, and the time they lost power written on them
5. `appliances-off` — Cooker and hob off at the knobs; computers and TV unplugged against the return surge
6. `no-co-indoors` — Generator, barbecue and stove outdoors only; CO alarm tested

Rules added:

- `grid-collapse-tell-the-operator` (rank 110, phones: working) — Tell the network operator: 105 in Great Britain, NIE Networks 03457 643 643 in Northern Ireland → page:uk-numbers
- `grid-collapse-lift-alarm` (rank 10, always, while the scenario runs) — Anyone stuck in a lift presses the alarm and waits; nobody forces the doors → module:power

### solar storm — 9 items (4 now, 1 hour, 2 today, 2 week)

1. `warning-hours` — On the warning: every container filled, every battery and power bank charged, cash drawn, tank filled
2. `unplug-electronics` — Computers, TV, router and chargers unplugged before the storm arrives
3. `vhf-radio-ready` — Battery FM radio on and PMR446 sets ready; expect HF, satellite and GPS to fail
4. `blackout-routine` — When the lights go: the grid collapse routine — fridge shut, cooker off, one warm room, radio on

Rules added:

- `solar-storm-use-the-warning-hours` (rank 110, power: ['working', 'degraded']) — Use the warning hours while the power is still on: water, charging, cash, fuel → module:power
- `solar-storm-no-satnav` (rank 10, always, while the scenario runs) — Do not trust GPS or satellite: paper map and compass for any journey → module:navigation

### emp — 9 items (3 now, 3 hour, 2 today, 1 week)

1. `blackout-routine` — First minutes: torch out, every container filled, fridge and freezer shut, cooker knobs off, cash counted
2. `treat-as-attack` — Treated as an attack warning: the nuclear war playbook's first actions — everyone in, mains off, windows shut, radio on
3. `faraday-tin` — Faraday tin opened: radio, torch, PMR446 pair, phone, chargers, solar panel, spare drive, multimeter

Rules added:

- `emp-no-restoration-date` (rank 10, always, while the scenario runs) — Ration the batteries from the first hour: there is no restoration date → module:power
- `emp-test-one-device-at-a-time` (rank 110, always, while the scenario runs) — Test what survived one device at a time, and keep the dead ones for parts → module:tools-repair

### cyber attack — 9 items (3 now, 2 hour, 3 today, 1 week)

1. `which-service-down` — Work out which service is down and whether 999 works on any phone in the house
2. `radio-and-share` — Battery radio on; Emergency Alerts on; SHARE checklist before believing or forwarding anything
3. `stored-water-notice` — If a do-not-drink notice is issued: stored or bottled water only, because boiling may not make it safe

Rules added:

- `cyber-attack-999-on-another-network` (rank 10, mobile: ['degraded', 'off']) — 999 may be unreachable on that network: try another phone, a neighbour's landline, or go in person → page:what-still-works
- `cyber-attack-do-not-drink-notice` (rank 110, water: ['degraded', 'off']) — On a do-not-drink notice, boiling may not make it safe: stored or bottled water only → module:water

### invasion — 10 items (4 now, 3 hour, 2 today, 1 week)

1. `blast-room` — Everyone into the blast room and lying down: no windows, two walls from outside, ground floor or basement
2. `targets-mapped` — Away from substations, depots, ports, airfields, barracks, bridges and masts; the route round them found on the map
3. `evacuate-when-told` — Radio and Emergency Alerts on: they say stay or go, and an evacuation you are told to make is not delayed
4. `bleeding-kit` — Bleeding kit out: pressure dressings, packing gauze, a tourniquet, gloves

Rules added:

- `invasion-do-not-go-and-look` (rank 10, always, while the scenario runs) — Do not go out to look at a strike, do not film it, do not drive towards it → doc:nrr-2025#page=23
- `invasion-unexploded-ordnance` (rank 110, always, while the scenario runs) — Nobody touches unexploded ordnance or the debris that may hide it; mark it and tell the police → module:security-law

### civil unrest — 11 items (5 now, 3 hour, 2 today, 1 week)

1. `everyone-home` — Everyone home; doors locked, curtains closed, car moved quietly off the street
2. `do-not-go-out` — Nobody goes out to watch, to film or to guard a shop
3. `fire-ready` — Smoke alarms tested; stairs clear; back way out known; buckets of water by the front door
4. `official-sources` — Radio on BBC local; Emergency Alerts on; SHARE checklist before forwarding anything
5. `nothing-visible` — Nothing valuable or edible visible from the street; keep away from street-side windows

Rules added:

- `civil-unrest-fire-still-answered` (rank 10, phones: working) — Fire is what still gets answered in a riot: 999 for fire, even when a burglary will not be attended → page:uk-numbers
- `civil-unrest-no-phone-fire-plan` (rank 10, phones: off) — With no phone there is no 999: agree the back way out and who runs where before dark → page:no-phones

### economic collapse — 11 items (3 now, 0 hour, 4 today, 4 week)

1. `no-panic-moves` — Nothing sold at panic prices, no bank queue joined on a rumour, no savings moved on the strength of a message
2. `cash-month` — Cash for two weeks of essentials drawn in small notes and kept in two places
3. `buy-essentials-now` — Two weeks of food, medicines and the things that break bought while cards still work

Rules added:

- `economic-collapse-machines-are-dead` (rank 110, power: off) — The cash machines are dead with the power: the notes in the house are the money you have → page:what-still-works
- `economic-collapse-check-the-guarantee` (rank 10, always, while the scenario runs) — Check the deposit guarantee in the library before you move a penny → kiwix:wikipedia_en_all_maxi/Financial_Services_Compensation_Scheme

### supply chain — 12 items (3 now, 3 hour, 2 today, 4 week)

1. `dont-panic-buy` — Do not join the queue: buy the gaps only, in ordinary quantities, from ordinary shops
2. `stock-count` — Stock count written on the fridge door: food, medicines, fuel, cash, nappies, pet food, gas
3. `prescriptions-early` — {{#if phones}}Repeat prescriptions ordered early and alternatives discussed with the pharmacist{{else}}The repeat slip or the labelled box taken to the pharmacy counter in person, and alternatives asked about while you are there{{/if}}

Rules added:

- `supply-chain-do-not-join-the-queue` (rank 110, shops: ['working', 'degraded']) — Do not join the queue: buy the gaps only, in ordinary quantities, from ordinary shops → module:food
- `supply-chain-formula-is-the-tightest-line` (rank 10, always, while the scenario runs) — A baby on formula is the tightest supply line in the house: read the fallback before the tin runs out → page:infant-feeding

### storms flooding — 13 items (5 now, 3 hour, 2 today, 3 week)

1. `flood-kit-upstairs` — People, pets, medicines, documents and the flood kit upstairs or to higher ground: go up, not out, unless you are told to leave
2. `mains-labelled` — Gas, electricity and water off at the mains as the water comes in; stopcock, gas valve and consumer unit found and labelled
3. `car-high-ground` — Never walk or drive through floodwater; the car moved to high ground before the water, not through it
4. `flood-warnings-signed-up` — {{#if phones}}Warning in force checked with Floodline on 0345 988 1188 (NI 0300 2000 100){{else}}Warning in force taken from BBC local radio, since Floodline needs a phone{{/if}}
5. `stay-in-from-the-storm` — In a storm: everyone in and away from windows, off the coast and sea walls, cars parked away from trees

Rules added:

- `storms-flooding-never-drive-through-it` (rank 110, roads: ['degraded', 'off']) — The road is under water: turn back rather than drive on, and send nobody to wade it → module:evacuation
- `storms-flooding-electrics-stay-off` (rank 110, power: ['degraded', 'off']) — Leave the electrics and the gas off until they have been checked; never touch a wet consumer unit → page:mains-electricity
- `storms-flooding-floodline` (rank 110, phones: working) — Get the warning in force: Floodline 0345 988 1188, or 0300 2000 100 in Northern Ireland → page:uk-numbers

### severe winter — 12 items (3 now, 4 hour, 4 today, 1 week)

1. `warm-room-18` — One warm room chosen and everyone in it; 18 °C target; thermometer in it
2. `curtains-and-layers` — Curtains shut at dusk, doors closed, draughts blocked, hats and layers on
3. `co-alarm-tested` — CO alarm tested; nothing burning indoors that belongs outdoors

Rules added:

- `severe-winter-one-room-now` (rank 110, heating: ['degraded', 'off']) — One room heated and everyone in it, doors shut on the rest of the house → module:shelter-heat
- `severe-winter-no-journeys` (rank 10, roads: ['degraded', 'off']) — No journey in a red warning; if you must go, winter kit in the car and somebody told the route → module:vehicles-fuel

### heat drought — 10 items (4 now, 2 hour, 3 today, 1 week)

1. `shade-and-ventilate` — Blinds and curtains shut on the sunny side; windows opened only when it is cooler outside; sleep on the lowest floor
2. `drink-enough` — Two to three litres of water a person a day drunk; rehydration salts to hand
3. `medicines-midday` — Inhalers and heart medicines within reach; nobody out at midday
4. `check-vulnerable` — Older neighbours, babies and anyone alone checked twice a day in a red alert

Rules added:

- `heat-drought-heatstroke-is-999` (rank 10, always, while the scenario runs) — Hot skin, confusion or a fit and no better after 30 minutes is heatstroke: cool them and call 999 → card:heat-stroke
- `heat-drought-find-the-bowser` (rank 110, water: ['degraded', 'off']) — Find the bowser or bottled water station the company has announced → module:water

### volcanic — 11 items (5 now, 1 hour, 3 today, 2 week)

1. `seal-the-house` — Doors, windows and vents shut; damp cloths at the sills; extractors off in ashfall
2. `cover-water` — Water butts, troughs and tanks covered and the downpipes disconnected before the ash arrives; two weeks of drinking water at 3 litres a person a day
3. `inhalers-ready` — Inhalers and heart medicines to hand; asthma plan written; anyone who cannot speak in sentences needs 999
4. `masks-and-goggles` — FFP2 or FFP3 masks and goggles for anyone who must go out; children kept in on bad-air days
5. `animals-in` — Livestock and poultry under cover on stored feed; pets in

Rules added:

- `volcanic-cover-the-water-first` (rank 110, water: working) — Cover the butts and pull the downpipes out before the ash arrives, and fill containers first → module:water
- `volcanic-bad-air-day` (rank 10, always, while the scenario runs) — On a bad-air day nobody exerts themselves outdoors; anyone who cannot speak in sentences needs 999 → card:asthma-attack

### chemical — 12 items (5 now, 4 hour, 1 today, 2 week)

1. `go-in-stay-in` — Everyone in and upwind of it: outdoors, move across the wind and uphill, away from the smell, and never drive into it
2. `shelter-room` — Into the room with the fewest openings, upstairs for a heavy gas: doors, windows, fans, extractors and the boiler off, gaps taped or towelled
3. `remove-remove-remove` — Anyone exposed: away from the source, clothing cut off rather than pulled over the head, skin blotted then washed, clothes bagged
4. `radio-on` — Radio on and Emergency Alerts on: what was released, which way it is going, and whether to stay in or leave
5. `no-confined-space-rescue` — Nobody enters a cellar, tank or building to rescue a collapsed person

Rules added:

- `chemical-heavy-gas-go-up` (rank 110, always, while the scenario runs) — Go up, not down: chlorine and most industrial gases pool in cellars, pits and low ground → card:chemical-exposure
- `chemical-wash-with-stored-water` (rank 110, water: ['degraded', 'off']) — Wash the exposed with stored water, poured slowly and generously: a shortage is no reason to skimp → card:chemical-exposure

### famine — 12 items (4 now, 0 hour, 3 today, 5 week)

1. `count-calories` — Store counted in days at 2,000 to 2,500 kcal a person, and the weekly ration written down today
2. `feed-the-weakest-first` — Children, pregnant women, nursing mothers and the sick fed first, at every meal
3. `plant-everything` — Every bed, tub and lawn edge sown with what the month allows; seed potatoes chitting
4. `foraging-rules` — Nothing eaten that cannot be named: the two deadly plants learned by every adult before anyone forages

Rules added:

- `famine-refeeding-kills` (rank 10, always, while the scenario runs) — Anyone who has gone hungry is fed small meals first → module:medical
- `famine-water-for-the-beds` (rank 110, water: ['degraded', 'off']) — Grey water and butt water keep the beds alive when the mains does not → module:growing-food

### impact winter — 11 items (3 now, 0 hour, 4 today, 4 week)

1. `store-and-seed` — This year's harvest brought in and stored for two years; seed set aside before anyone eats
2. `stove-ready` — Stove, flue and carbon monoxide alarm checked sound; a season's fuel by the door
3. `wood-a-year-ahead` — Wood cut and stacked to dry a year ahead, because green wood will not burn; coppice planted

Rules added:

- `impact-winter-seed-before-supper` (rank 110, always, while the scenario runs) — Set next year's seed aside before anyone eats this year's harvest → module:growing-food
- `impact-winter-fuel-before-the-cold` (rank 110, heating: ['degraded', 'off']) — One warm room and a season's fuel at the door before the first winter → module:shelter-heat

### terrorism — 10 items (3 now, 3 hour, 2 today, 2 week)

1. `run-hide-tell` — Run if there is a route away, hide if there is not — out of sight, phone silent, door barricaded — and tell the police on 999 once you are safe
2. `second-device-rule` — After an explosion: away from the scene and out of sight of it, no gathering, no filming, nothing gone back for
3. `carry-bleeding-kit` — Once you are clear, stop the bleeding: pressure, packing, a tourniquet on a limb, and keep them warm

Rules added:

- `terrorism-tourniquet-and-the-time` (rank 110, always, while the scenario runs) — Catastrophic limb bleeding: a tourniquet high and tight, and write the time on it → card:severe-bleeding
- `terrorism-tell-them-in-person` (rank 110, phones: off) — Tell them in person: the nearest police or fire station, once you are away and safe → page:no-phones

### long rebuild — 13 items (4 now, 0 hour, 2 today, 7 week)

1. `first-month-done` — The cause's playbook worked through for the first month before this one starts
2. `street-water` — Shelter and water together: the street's water source found, tested, filtered and disinfected; a hand pump planned
3. `latrines-sited` — Latrines dug 30 metres from water and downhill, before anyone is ill; burial ground sited to the burial distances
4. `asset-register` — Skills, tools, animals, land, seed and medicines registered on paper in the hall

Rules added:

- `long-rebuild-shelter-and-water-first` (rank 10, always, while the scenario runs) — Order of work: shelter and water together, then sanitation, then food, then security → module:sanitation
- `long-rebuild-boil-until-it-is-tested` (rank 110, water: ['degraded', 'off']) — Every drop boiled or treated until the street's source has been tested → page:water-disinfection

## The drills

`POST /api/drill` with `power`, `mobile` and `landline` off (the box's water was already set to off
by hand, which is why `boil-water` fires), then `DELETE /api/drill`.

### nuclear-war

```
 1 now   checklist:nuclear-war/stay-48-hours                Everyone and the pets in, doors shut: nobody leaves the house for 48 hours, then reassess by radio
 2 now   checklist:nuclear-war/mains-off-windows-shut       Gas and electricity off at the mains, any fire damped, every window, door and vent shut, curtains drawn
 3 now   checklist:nuclear-war/decontaminate-at-door        Anyone who was outside: outer clothes off and bagged at the door, then wash hair and skin
 4 now   checklist:nuclear-war/radio-and-light              Radio on and left on, torch and spare batteries beside it, candles and matches out of the way
 5 now   checklist:nuclear-war/choose-fallout-room          Into the fall-out room: basement or ground-floor middle room, fewest outside walls
 6 now   checklist:nuclear-war/fourteen-days-water-food     Water and food carried in: 3 litres a person a day, 14 days of it, covered, and tinned food that needs no cooking
 7 now   nuclear-war-radio-is-the-all-clear                 The wind-up radio is the only all-clear you will get: keep it on and write down each bulletin
 8 now   fridge-doors-shut                                  Keep the fridge and freezer doors shut, and write the time on them
 9 now   co-alarm-power                                     Test the carbon monoxide alarm before you burn anything indoors
10 now   boil-water                                         Boil or treat every drop, including the first day the mains comes back
11 now   meeting-point                                      Agree the meeting point and who runs where
12 now   check-on-people-nearby                             Check on anyone nearby who would struggle on their own
13 hour  checklist:nuclear-war/refuge-materials             Inner refuge packed round with earth, sand, books and boxes; windows blocked
14 hour  checklist:nuclear-war/bucket-toilet                Lidded bucket, bin liners, disinfectant, toilet paper and a second bin for refuse set up in the room
15 hour  checklist:nuclear-war/map-sites-and-wind           Nearest nuclear site and the wind direction marked on the map
16 hour  checklist:nuclear-war/iodine-only-if-told          No iodine tablets unless the authorities say so; note who took what and when
17 hour  bucket-flush                                       Flush with a bucket of grey water, and bag it if the drains back up
18 today checklist:nuclear-war/log-vomiting-times           Time of any vomiting after exposure written down, per person
19 today checklist:nuclear-war/no-milk-or-greens            Tins wiped before opening; no fresh milk, leafy greens or open-grown food until cleared
20 today one-warm-room                                      Heat one room, close the doors on the rest and sleep in it
21 week  checklist:nuclear-war/first-trip-outside           The first trip outside kept short, skin covered, outer layer and boots left at the door
```

### chemical

```
 1 now   checklist:chemical/go-in-stay-in                   Everyone in and upwind of it: outdoors, move across the wind and uphill, away from the smell, and never drive into it
 2 now   checklist:chemical/shelter-room                    Into the room with the fewest openings, upstairs for a heavy gas: doors, windows, fans, extractors and the boiler off, gaps taped or towelled
 3 now   checklist:chemical/remove-remove-remove            Anyone exposed: away from the source, clothing cut off rather than pulled over the head, skin blotted then washed, clothes bagged
 4 now   checklist:chemical/radio-on                        Radio on and Emergency Alerts on: what was released, which way it is going, and whether to stay in or leave
 5 now   checklist:chemical/no-confined-space-rescue        Nobody enters a cellar, tank or building to rescue a collapsed person
 6 now   chemical-heavy-gas-go-up                           Go up, not down: chlorine and most industrial gases pool in cellars, pits and low ground
 7 now   chemical-wash-with-stored-water                    Wash the exposed with stored water, poured slowly and generously: a shortage is no reason to skimp
 8 now   fridge-doors-shut                                  Keep the fridge and freezer doors shut, and write the time on them
 9 now   cooker-off                                         Turn the cooker, the iron and any electric heater off at the knobs
10 now   co-alarm-power                                     Test the carbon monoxide alarm before you burn anything indoors
11 now   boil-water                                         Boil or treat every drop, including the first day the mains comes back
12 now   meeting-point                                      Agree the meeting point and who runs where
13 now   check-on-people-nearby                             Check on anyone nearby who would struggle on their own
14 hour  checklist:chemical/animals-in                      Pets in; livestock under cover
15 hour  checklist:chemical/cover-water                     Water butts covered; open-source water not drunk
16 hour  checklist:chemical/sites-and-wind                  Nearest chemical, fuel and refinery sites found on the map; wind direction noted
17 hour  checklist:chemical/evacuate-when-told              Evacuate only when told, by the route given
18 hour  bucket-flush                                       Flush with a bucket of grey water, and bag it if the drains back up
19 today checklist:chemical/symptom-log                     Symptoms and times written down for everyone exposed
20 today one-warm-room                                      Heat one room, close the doors on the rest and sleep in it
21 week  checklist:chemical/clean-up-after                  After the all-clear: ventilate, wash surfaces, launder, discard exposed food
22 week  checklist:chemical/register-and-records            Registered with the incident helpline; exposure recorded in GP notes; every letter kept
```

### storms-flooding

```
 1 now   checklist:storms-flooding/flood-kit-upstairs       People, pets, medicines, documents and the flood kit upstairs or to higher ground: go up, not out, unless you are told to leave
 2 now   checklist:storms-flooding/mains-labelled           Gas, electricity and water off at the mains as the water comes in; stopcock, gas valve and consumer unit found and labelled
 3 now   checklist:storms-flooding/car-high-ground          Never walk or drive through floodwater; the car moved to high ground before the water, not through it
 4 now   checklist:storms-flooding/flood-warnings-signed-up Warning in force taken from BBC local radio, since Floodline needs a phone
 5 now   checklist:storms-flooding/stay-in-from-the-storm   In a storm: everyone in and away from windows, off the coast and sea walls, cars parked away from trees
 6 now   storms-flooding-never-drive-through-it             The road is under water: turn back rather than drive on, and send nobody to wade it
 7 now   storms-flooding-electrics-stay-off                 Leave the electrics and the gas off until they have been checked; never touch a wet consumer unit
 8 now   fridge-doors-shut                                  Keep the fridge and freezer doors shut, and write the time on them
 9 now   boil-water                                         Boil or treat every drop, including the first day the mains comes back
10 now   meeting-point                                      Agree the meeting point and who runs where
11 now   check-on-people-nearby                             Check on anyone nearby who would struggle on their own
12 hour  checklist:storms-flooding/defences-fitted          Sandbags or flood boards fitted; airbricks covered; valuables raised
13 hour  checklist:storms-flooding/rest-centre-route        Rest centre location and evacuation route written down
14 hour  checklist:storms-flooding/pumps-outdoors           Pumps and generators outdoors only; CO alarm on
15 hour  bucket-flush                                       Flush with a bucket of grey water, and bag it if the drains back up
16 today checklist:storms-flooding/floodwater-hygiene       Hands washed after any floodwater contact; food it touched thrown away
17 today checklist:storms-flooding/photograph-damage        Every damaged item photographed before disposal; the claim written up on paper for the insurer
18 today one-warm-room                                      Heat one room, close the doors on the rest and sleep in it
19 week  checklist:storms-flooding/check-before-reconnect   Electrics and gas checked by a professional before reconnection
20 week  checklist:storms-flooding/chainsaw-safety          Chainsaw kit complete, or the job left to someone with it
21 week  checklist:storms-flooding/flood-risk-checked       Long-term flood risk for the address checked; flood zone on the map looked at
```

