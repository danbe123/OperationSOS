---
id: power
title: Power
icon: bolt
order: 6
summary: What stops when the grid stops, 105 and your network operator, generators, batteries, solar, fallen lines and staying safe around 230 volts.
sources:
  - title: National Risk Register 2025
    doc: nrr-2025
    as_at: 2025-01-16
  - title: Prepare, power cuts
    kiwix: prepare_uk/prepare.campaign.gov.uk/be-informed-about-hazards/power-cuts/
    as_at: 2026-09-05
  - title: UK CMOs' advice during a national power outage, keeping warm or cool
    kiwix: govuk_resilience/www.gov.uk/government/publications/public-health-advice-from-uk-cmos-during-a-national-power-outage/keeping-warm-or-cool-in-extreme-weather-scripts-for-broadcast-media
    as_at: 2026-09-05
  - title: HSE INDG231 Electrical safety and you
    doc: hse-indg231
    as_at: 2026-09
  - title: Approved Document P
    doc: ad-p
    as_at: 2013-04
  - title: iFixit generator guides
    kiwix: ifixit_en_all/Device/Generator
    as_at: 2025-12-21
  - title: Electromagnetic pulse (Wikipedia)
    kiwix: wikipedia_en_all_maxi/Electromagnetic_pulse
    as_at: 2026-02-15
  - title: Coronal mass ejection (Wikipedia)
    kiwix: wikipedia_en_all_maxi/Coronal_mass_ejection
    as_at: 2026-02-15
---

## Key facts

- The National Risk Register's reasonable worst case for national electricity transmission failure is a total loss with restoration over several days, up to seven, and rota disconnection afterwards ([NRR 2025, p. 45](doc:nrr-2025#page=45); [p. 90](doc:nrr-2025#page=90)).
- Your electricity network operator hears about the cut on **105**, free from any phone in Great Britain (Northern Ireland: NIE Networks 03457 643 643; Republic of Ireland: ESB Networks 1800 372 999) ([Prepare, power cuts](kiwix:prepare_uk/prepare.campaign.gov.uk/be-informed-about-hazards/power-cuts/)) — [[call 105]]. The full list is on [UK numbers](page:uk-numbers).
- Gas boilers and heat pumps stop with the grid, as do the landline, the broadband and, after their batteries, the mobile masts; the full service-by-service list with timings is on [What still works](page:what-still-works) ([Prepare, power cuts](kiwix:prepare_uk/prepare.campaign.gov.uk/be-informed-about-hazards/power-cuts/)). Fridge and freezer timings are in the [Food module](module:food).

## What to do

1. Know your network operator: UK Power Networks, National Grid Electricity Distribution, SP Energy Networks, SSEN, Northern Powergrid, Electricity North West, NIE Networks, ESB Networks, Manx Utilities, Jersey Electricity or Guernsey Electricity, depending on region, and {{#if phones}}join the Priority Services Register if anyone in the house depends on electrical medical equipment{{else}}tell the operator's engineers, the rest centre or the police in person that someone here depends on electrical medical equipment, and join the Priority Services Register once the lines are back{{/if}} ([UK numbers](page:uk-numbers)).
2. Never work on a live circuit: isolate, then prove dead ([HSE INDG231, p. 3](doc:hse-indg231#page=3)); how the house is wired, RCDs and what needs an electrician are on [Mains electricity](page:mains-electricity).
3. Run a generator outdoors, at least 6 metres (20 feet) from doors and windows with the exhaust facing away, never in a garage, because the exhaust is carbon monoxide ([CMO outage advice, keeping warm](kiwix:govuk_resilience/www.gov.uk/government/publications/public-health-advice-from-uk-cmos-during-a-national-power-outage/keeping-warm-or-cool-in-extreme-weather-scripts-for-broadcast-media)). Never back-feed it through a socket; only a transfer switch fitted by an electrician, which is notifiable work ([Approved Document P, p. 14](doc:ad-p#page=14); [Mains electricity](page:mains-electricity)).
4. Store generator petrol within the legal household limits (see [vehicles and fuel](module:vehicles-fuel)).
5. {{#if power}}Use LED lighting wherever possible and treat candles as a last resort, not a first one; charge the power bank, the torches and the phones now, while the mains is on.{{else}}Light the house with LED torches and lanterns and treat candles as a last resort, not a first one; the power bank goes to phones and this box, not to lighting.{{/if}} Torches are safer than candles ([Prepare, power cuts](kiwix:prepare_uk/prepare.campaign.gov.uk/be-informed-about-hazards/power-cuts/)).
6. Keep away from fallen or damaged power lines: high voltage jumps gaps with no warning; report them on 105 ([Prepare, power cuts](kiwix:prepare_uk/prepare.campaign.gov.uk/be-informed-about-hazards/power-cuts/); [Mains electricity](page:mains-electricity)).
7. Claim compensation for a prolonged outage from your network operator under Ofgem's guaranteed standards once power is restored.

{{#if scenario:grid-collapse}}
**Plan in days, not hours.** The register's worst case is a total failure of the transmission system in winter, every customer off without warning and restoration taking up to seven days ([NRR 2025, p. 90](doc:nrr-2025#page=90); [NRR 2025, p. 91](doc:nrr-2025#page=91)). Rota disconnection belongs to a gas or electricity shortfall rather than to this scenario. Water, sewage, fuel pumps, cash machines and card terminals go with it. Ration the power bank from the first hour: this box and one phone, screens dim, phones off between check-ins. Listen to BBC local radio on FM at agreed times rather than leaving the set running, and expect the mobile network to fail area by area as the mast batteries run down ([What still works](page:what-still-works)).
{{/if}}

{{#if scenario:emp}}
**Assume no restoration date at all.** Nobody can tell you in advance what survived. The reasoning — not a sourced fact — is that what was switched off, unplugged and away from long wires is the likelier survivor, and what was on and connected to the mains, a phone line or an aerial the likelier casualty ([Electromagnetic pulse](kiwix:wikipedia_en_all_maxi/Electromagnetic_pulse)). Do not throw a dead device away: many failures are the power supply or the battery rather than the device, and the repair guides are in the [tools and repair module](module:tools-repair). Unplug computers, the router and chargers now, because the surge when supply returns is what finishes them off ([Prepare, power cuts](kiwix:prepare_uk/prepare.campaign.gov.uk/be-informed-about-hazards/power-cuts/)).
{{/if}}

{{#if scenario:solar-storm}}
**You get warning; use it.** A coronal mass ejection takes one to three days to reach Earth, fifteen to twenty hours for the fastest ([Coronal mass ejection](kiwix:wikipedia_en_all_maxi/Coronal_mass_ejection)). Charge everything, fill the tank, draw cash, then unplug computers, the TV, the router and chargers before it arrives ([Prepare, power cuts](kiwix:prepare_uk/prepare.campaign.gov.uk/be-informed-about-hazards/power-cuts/)). The planning case is a Carrington-scale event running one to two weeks, with regional power disruption and loss of GPS, satellite communications and HF radio, each phenomenon likely to happen several times in that fortnight ([NRR 2025, p. 137](doc:nrr-2025#page=137)), so a grid brought back on day two may fall again on day four.
{{/if}}

{{#if scenario:cyber-attack}}
**A restoration estimate is not a repair time.** The planning case for the grid is pockets back within hours and up to seven days for full restoration, longer if the attack damaged the systems themselves ([NRR 2025, p. 45](doc:nrr-2025#page=45)). Act on nothing arriving as a text or email claiming to be your supplier: report the cut on 105 — [[call 105]], Great Britain only, with Northern Ireland on 03457 643643 — and take the rest from BBC local radio on FM. You may not be able to top a prepay meter up while the systems are down, but the meter itself holds emergency credit and friendly-hours protection: use them rather than assuming you are cut off ([Mains electricity](page:mains-electricity)).
{{/if}}

## UK specifics

- Grid-tied solar panels shut down in a power cut unless paired with a battery and an islanding switch; what panels and batteries give in Britain is on [Solar islanding](page:solar-islanding) ([Approved Document P, p. 14](doc:ad-p#page=14)).
- In a rota disconnection each area is cut for around three hours at a time by "load block letter", printed on some bills ([Prepare, power cuts](kiwix:prepare_uk/prepare.campaign.gov.uk/be-informed-about-hazards/power-cuts/)).
- A prepayment or smart prepay meter cuts you off when the credit runs out even with the grid up; emergency credit and "friendly credit" hours are explained on [Mains electricity](page:mains-electricity). Repair guides for generators are in the [iFixit generator guides](kiwix:ifixit_en_all/Device/Generator).

## Go deeper

- [What still works](page:what-still-works)
- [Mains electricity](page:mains-electricity)
- [Solar islanding](page:solar-islanding)
- [UK numbers](page:uk-numbers)
- [Vehicles and fuel](module:vehicles-fuel)
- [2025 Iberian Peninsula blackout (Wikipedia)](kiwix:wikipedia_en_all_maxi/2025_Iberian_Peninsula_blackout)
- [Lithium iron phosphate battery (Wikipedia)](kiwix:wikipedia_en_all_maxi/Lithium_iron_phosphate_battery)
- [Fuel stations on the map](map:?overlay=fuel)
