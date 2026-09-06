---
id: emp
title: EMP attack
icon: zap
order: 6
summary: A high-altitude nuclear burst kills electronics, some vehicles and radios nationwide. A blackout with no restoration date, and a war may follow.
modules: [power, comms, vehicles-fuel, navigation, water, medical, tools-repair]
overlays: [fuel, health, rail]
reviewed: null
sources:
  - title: Nuclear electromagnetic pulse (Wikipedia)
    kiwix: wikipedia_en_all_maxi/Nuclear_electromagnetic_pulse
    as_at: 2026-02-15
  - title: Electromagnetic pulse (Wikipedia)
    kiwix: wikipedia_en_all_maxi/Electromagnetic_pulse
    as_at: 2026-02-15
  - title: Starfish Prime (Wikipedia)
    kiwix: wikipedia_en_all_maxi/Starfish_Prime
    as_at: 2026-02-15
  - title: Faraday cage (Wikipedia)
    kiwix: wikipedia_en_all_maxi/Faraday_cage
    as_at: 2026-02-15
  - title: National Risk Register 2025
    doc: nrr-2025
    as_at: 2025-01-16
  - title: iFixit repair guides
    kiwix: ifixit_en_all/home/home
    as_at: 2025-12-21
  - title: Electrical Engineering Q&A (Stack Exchange)
    kiwix: electronics.stackexchange.com_en_all/questions
    as_at: 2026-08-01
---

## Right now

**Recognise it.** Everything electronic stops at the same instant: lights, phones, the router, the car dashboard, possibly the car; there may have been a flash high in the sky and there is no explosion ([Nuclear electromagnetic pulse](kiwix:wikipedia_en_all_maxi/Nuclear_electromagnetic_pulse)). What it is and why is under UK specifics; act first.

**Do this in the first hour:** torch; battery radio, if it still works, on FM; {{#if water}}every container filled while the mains still runs{{else}}the stored water rationed, because the pumps are electric{{/if}}; fridge and freezer shut; cooker knobs off; cash counted; then the rest of the [grid collapse playbook](playbook:grid-collapse), with no restoration date: the register's grid-failure planning assumptions apply without the "up to 7 days" ([NRR 2025, p. 90](doc:nrr-2025#page=90)).

**Treat the next hours as an attack warning.** A high-altitude burst is a nuclear weapon used in anger, and the register's nuclear-attack scenario is classified ([NRR 2025, p. 184](doc:nrr-2025#page=184)): go to the fall-out room and the warning steps of the [nuclear war playbook](playbook:nuclear-war). A burst high above the atmosphere leaves little local fallout of its own because the fireball never touches the ground ([Nuclear fallout](kiwix:wikipedia_en_all_maxi/Nuclear_fallout)); what follows it may.

{{module:power}}

## First 72 hours

- **Test what survived.** Small battery devices that were switched off and not plugged in, anything in a metal box, older vehicles, hand tools and mechanical things are the likely survivors; what was on and connected to long wires (the mains, phone lines, aerials) is the likely casualty ([Electromagnetic pulse](kiwix:wikipedia_en_all_maxi/Electromagnetic_pulse)). Do not throw away a dead device: some recover when the battery is pulled and replaced, and many failures are the power supply, not the device ([iFixit](kiwix:ifixit_en_all/home/home)).
- **Vehicles.** A pulse would probably not affect most cars, because their wiring is short and the metal body shields it, but even a few per cent failing would jam the roads ([Nuclear electromagnetic pulse](kiwix:wikipedia_en_all_maxi/Nuclear_electromagnetic_pulse)); the most robust are older diesels with mechanical injection and anything with a magneto or points ignition ([Ignition system](kiwix:wikipedia_en_all_maxi/Ignition_system)). Pumps are electric: the fuel in the tank is the fuel you have ([Vehicles and fuel module](module:vehicles-fuel)).
- **Communications.** Nothing on the network will work: no mobile, no landline, no internet, no Emergency Alerts ([What still works](page:what-still-works)). A radio kept in a tin will receive whatever is still on air; which transmitters survive cannot be known in advance, so listen on FM at set times rather than draining the batteries. PMR446 and amateur handhelds that were in a tin will talk to each other ([PMR446 channels](page:pmr446)); agree a channel and a schedule with the street ([Communications module](module:comms)).
- **Water** and sewage pumps are electric; store and treat as in the [water module](module:water) and expect no mains within days.
- **Medical devices:** insulin pumps, CPAP, oxygen concentrators and stairlifts all depend on electronics or the mains; make the plan for each person now ([Medical module](module:medical)).

{{module:comms}}

{{module:vehicles-fuel}}

{{module:water}}

## First month

- **Faraday cage.** A metal box or biscuit tin lined with cardboard so nothing touches the metal, lid taped, holds a spare radio, torch, PMR446 pair, a phone, chargers, a small solar panel, a spare copy of this box's drive and the cables, and a cheap multimeter ([Faraday cage](kiwix:wikipedia_en_all_maxi/Faraday_cage)). Fill one now; empty it after.
- **Repair.** With the grid gone for months, the skills that matter are the ones in the [tools and repair module](module:tools-repair): mechanical fixes, small engines, batteries and inverters ([Electrical Engineering Q&A](kiwix:electronics.stackexchange.com_en_all/questions)). Solar panels themselves usually survive; inverters and charge controllers often do not, so a spare in the tin is worth more than a spare panel ([Solar panels in a power cut](page:solar-islanding)).
- **Navigation** without GPS is map, compass and grid reference ([Navigation module](module:navigation)); trains, signals and fuel deliveries stop ([NRR 2025, p. 86](doc:nrr-2025#page=86)).
- **Food:** the [supply chain playbook](playbook:supply-chain) applies from day one, because tills, lorries and refrigeration are all electronic.

{{module:navigation}}

{{module:medical}}

## Long term

**What survives sets the order of rebuilding.** The pulse does its damage by voltage, and long conductors collect it: what was plugged into the mains, a phone line or an aerial is the likely loss, while short, unplugged things (wristwatches, mobile phones, hand-held radios, anything that sat in a metal box) would most likely come through ([Nuclear electromagnetic pulse](kiwix:wikipedia_en_all_maxi/Nuclear_electromagnetic_pulse)). Valve equipment is far less vulnerable than transistors and chips, and a fast pulse is too quick for an ordinary surge protector ([Nuclear electromagnetic pulse](kiwix:wikipedia_en_all_maxi/Nuclear_electromagnetic_pulse)). Cars are probably mostly fine ([Nuclear electromagnetic pulse](kiwix:wikipedia_en_all_maxi/Nuclear_electromagnetic_pulse)); panels survive and their electronics do not ([Solar panels in a power cut](page:solar-islanding)). **Rebuild in this order:** water first, a hand pump or a way to carry and treat it ([Water module](module:water)); then light and a listening schedule from a car battery, a panel and the spare controller from the tin; then cold storage for medicines; then power for tools, from water, wind and salvaged panels ([Tools and repair module](module:tools-repair)). The grid itself is last: the slow third pulse damages transformers the way a geomagnetic storm does ([Nuclear electromagnetic pulse](kiwix:wikipedia_en_all_maxi/Nuclear_electromagnetic_pulse)), a replacement of that size takes months ([NRR 2025, p. 138](doc:nrr-2025#page=138)), and the control systems that would black-start it are the electronics most exposed. The [solar storm playbook](playbook:solar-storm) covers that recovery, and the [long rebuild playbook](playbook:long-rebuild) the years after.

{{module:tools-repair}}

## UK specifics

- **What it is.** A nuclear weapon detonated far above the atmosphere. Its first pulse rises in nanoseconds and breaks down the insulation in chips; the second is like lightning; the third is slow and overloads the grid like a solar storm; everything in line of sight of the burst is exposed, which from 400 km up is most of a continent ([Nuclear electromagnetic pulse](kiwix:wikipedia_en_all_maxi/Nuclear_electromagnetic_pulse)). The 1962 Starfish Prime test put out streetlights 1,400 km away in Hawaii ([Starfish Prime](kiwix:wikipedia_en_all_maxi/Starfish_Prime)).
- **The register** does not list EMP by name; the nuclear attack scenario is classified ([NRR 2025, p. 184](doc:nrr-2025#page=184)) and the closest public planning cases are severe space weather ([NRR 2025, p. 137](doc:nrr-2025#page=137)), loss of positioning and timing ([NRR 2025, p. 86](doc:nrr-2025#page=86)), and total loss of fixed and mobile communications ([NRR 2025, p. 88](doc:nrr-2025#page=88)).
- **What has stopped**, service by service, is on [What still works](page:what-still-works); the nearest fire or police station is where to take an emergency in person ([getting help without phones](page:no-phones)).
- **Water and sewage** in Britain are pumped; high-rise flats lose water first ([CMO outage advice](kiwix:govuk_resilience/www.gov.uk/government/publications/public-health-advice-from-uk-cmos-during-a-national-power-outage)).
- **Radio:** a surviving FM receiver on 92 to 95 MHz is the one national link if the BBC's transmitters are still on air ([What still works](page:what-still-works)); licensed amateurs may pass messages for anyone in a genuine emergency ([Amateur bands](page:amateur-bands)).
- **Law does not switch off** with the electronics: taking fuel or goods is theft, and the emergency powers are those of the Civil Contingencies Act 2004 ([Security and the law module](module:security-law)).

## Checklist

- [ ] Faraday tin filled: radio, torch, PMR446 pair, phone, chargers, solar panel, spare drive, multimeter {#faraday-tin}
- [ ] Attack-warning actions from the nuclear war playbook done in the first minutes {#treat-as-attack}
- [ ] Blackout routine: water filled, fridge shut, cooker off, cash counted {#blackout-routine}
- [ ] Every device tested; dead ones kept for battery pulls and power-supply repairs {#test-devices}
- [ ] Vehicles tried; the one that runs is kept for essentials only {#test-vehicles}
- [ ] Medical device users' plans written: pump, CPAP, oxygen, stairlift {#medical-device-plans}
- [ ] Street radio channel and check-in times agreed {#street-radio-plan}
- [ ] Paper map and compass out; grid references written for key places {#paper-navigation}
- [ ] Two weeks of food and water; supply chain playbook started {#two-weeks-store}

## Go deeper

- [Power module](module:power)
- [Tools and repair module](module:tools-repair)
- [What still works in an outage](page:what-still-works)
- [Nuclear electromagnetic pulse (Wikipedia)](kiwix:wikipedia_en_all_maxi/Nuclear_electromagnetic_pulse)
- [Faraday cage (Wikipedia)](kiwix:wikipedia_en_all_maxi/Faraday_cage)
- [Crystal radio (Wikipedia)](kiwix:wikipedia_en_all_maxi/Crystal_radio)
- [Electrical Engineering Q&A](kiwix:electronics.stackexchange.com_en_all/questions)
- [Motor vehicle repair Q&A](kiwix:mechanics.stackexchange.com_en_all/questions)
- [iFixit](kiwix:ifixit_en_all/home/home)
- [Nuclear war playbook](playbook:nuclear-war)
- [Solar storm playbook](playbook:solar-storm)
- [Restarters: how things work and how to fix them](kiwix:restarters_en_all/Main_Page)
- [Map Reading and Land Navigation, FM 3-25.26](doc:fm-3-25-26-map-reading)
- [Field craft in Britain](page:fieldcraft-basics)
- [Moving across country](page:fieldcraft-moving)
