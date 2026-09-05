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

**Recognise it.** Everything electronic stops at the same instant: lights, phones, the router, the car dashboard, possibly the car; there may have been a flash high in the sky and there is no explosion. A nuclear EMP is a nuclear weapon detonated far above the atmosphere; its three pulses (a nanosecond spike that fries chips, a lightning-like second pulse, and a slow third pulse that overloads the grid like a solar storm) reach everything in line of sight of the burst, which from 400 km up is most of Europe ([Nuclear electromagnetic pulse](kiwix:wikipedia_en_all_maxi/Nuclear_electromagnetic_pulse)). The 1962 Starfish Prime test put out streetlights 1,400 km away in Hawaii ([Starfish Prime](kiwix:wikipedia_en_all_maxi/Starfish_Prime)).

**Assume a war has started.** A high-altitude burst is usually described as the opening move; go to the [nuclear war playbook](playbook:nuclear-war) for shelter and fallout (there is no fallout from a burst in space, but there may be from what follows) and treat the next hours as an attack warning.

**Then treat it as a blackout with no restoration date:** torch, battery radio (if it still works), water filled, fridge shut, cooker off, cash ([Grid collapse playbook](playbook:grid-collapse)). The register's grid-failure planning assumptions apply, without the "up to 7 days" ([NRR 2025, p. 90](doc:nrr-2025#page=90)).

{{module:power}}

## First 72 hours

- **Test what survived.** Small battery devices that were switched off and not plugged in, anything in a metal box, older vehicles, hand tools and mechanical things are the likely survivors; what was on and connected to long wires (the mains, phone lines, aerials) is the likely casualty ([Electromagnetic pulse](kiwix:wikipedia_en_all_maxi/Electromagnetic_pulse)). Do not throw away a dead device: some recover when the battery is pulled and replaced, and many failures are the power supply, not the device ([iFixit](kiwix:ifixit_en_all/home/home)).
- **Vehicles.** Tests on cars found most kept running or restarted after a pulse; the vulnerable ones are those with the most electronics, and the most robust are older diesels with mechanical injection and anything with a magneto or points ignition ([Nuclear electromagnetic pulse](kiwix:wikipedia_en_all_maxi/Nuclear_electromagnetic_pulse); [Ignition system](kiwix:wikipedia_en_all_maxi/Ignition_system)). Pumps are electric: the fuel in the tank is the fuel you have ([Vehicles and fuel module](module:vehicles-fuel)).
- **Communications.** Nothing on the network will work: no mobile, no landline, no internet, no Emergency Alerts. A radio in a tin will receive whatever a transmitter with backup power is sending; PMR446 and amateur handhelds that were in a tin will talk to each other ([PMR446 channels](page:pmr446)). Agree a channel and a schedule with the street ([Communications module](module:comms)).
- **Water** and sewage pumps are electric; store and treat as in the [water module](module:water) and expect no mains within days.
- **Medical devices:** pacemakers are shielded and usually unaffected; insulin pumps, CPAP, oxygen concentrators and stairlifts may not be; make the plan for each person now ([Medical module](module:medical)).

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

Recovery from an EMP is recovery from a grid collapse whose transformers, control systems and substations have all been damaged at once, with the factories that make replacements in the same state ([Nuclear electromagnetic pulse](kiwix:wikipedia_en_all_maxi/Nuclear_electromagnetic_pulse)). The long-term plan is the [long rebuild playbook](playbook:long-rebuild): local power from water, wind and salvaged panels, hand tools, and repair. Reading the [solar storm playbook](playbook:solar-storm) is worthwhile because the slow third pulse is the same phenomenon ([Geomagnetic storm](kiwix:wikipedia_en_all_maxi/Geomagnetic_storm)).

{{module:tools-repair}}

## UK specifics

- **The register** does not list EMP by name; the nuclear attack scenario is classified ([NRR 2025, p. 184](doc:nrr-2025#page=184)) and the closest public planning cases are severe space weather ([NRR 2025, p. 137](doc:nrr-2025#page=137)), loss of positioning and timing ([NRR 2025, p. 86](doc:nrr-2025#page=86)), and total loss of fixed and mobile communications ([NRR 2025, p. 88](doc:nrr-2025#page=88)).
- **What will not help:** 105, 999 by phone, Emergency Alerts, cash machines, card readers, petrol pumps, lifts, electric gates, Digital Voice landlines ([What still works](page:what-still-works)); the nearest fire or police station is where to take an emergency in person.
- **Water and sewage** in Britain are pumped; high-rise flats lose water first ([CMO outage advice](kiwix:govuk_resilience/www.gov.uk/government/publications/public-health-advice-from-uk-cmos-during-a-national-power-outage)).
- **Radio:** BBC transmitters have standby generators, so a surviving FM receiver on 92 to 95 MHz is the one national link ([What still works](page:what-still-works)); licensed amateurs may pass messages for anyone in a genuine emergency ([Amateur bands](page:amateur-bands)).
- **Law does not switch off** with the electronics: taking fuel or goods is theft, and the emergency powers of the Civil Contingencies Act 2004 are what the authorities would use ([Civil Contingencies Act 2004](kiwix:legislation_uk/www.legislation.gov.uk/ukpga/2004/36/contents)).

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
