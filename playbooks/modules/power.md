---
id: power
title: Power
icon: bolt
order: 6
summary: What stops when the grid stops, 105 and your network operator, generators, batteries, solar and staying safe around 230 volts.
sources:
  - title: National Risk Register 2025
    doc: nrr-2025
    as_at: 2025-01-16
  - title: Prepare, be informed about hazards
    kiwix: prepare_uk/prepare.campaign.gov.uk/be-informed-about-hazards/
    as_at: 2026-09
  - title: HSE INDG231 Electrical safety and you
    doc: hse-indg231
    as_at: 2026-09
  - title: Approved Document P
    doc: ad-p
    as_at: 2013-04
  - title: iFixit generator guides
    kiwix: ifixit_en_all/Device/Generator
    as_at: 2025-12-21
  - title: Petroleum (Consolidation) Regulations 2014
    kiwix: legislation_uk/www.legislation.gov.uk/uksi/2014/1637/contents
    as_at: 2026-09
---

## Key facts

- The National Risk Register's reasonable worst case for national electricity transmission failure is a total loss with restoration over several days, up to seven, and rota disconnection afterwards ([NRR 2025, p. 45](doc:nrr-2025#page=45); [p. 90](doc:nrr-2025#page=90)).
- Your electricity network operator hears about the cut on **105**, free from any phone in Great Britain (Northern Ireland: NIE Networks 03457 643 643; Republic of Ireland: ESB Networks 1800 372 999) — [[call 105]]. The full list is on [UK numbers](page:uk-numbers).
- When the grid goes down, gas boilers, Digital Voice landlines, most mobile masts after their battery runs out, cash machines, petrol pumps, lifts and electric gates all stop too ([What still works](page:what-still-works); [Prepare hazards](kiwix:prepare_uk/prepare.campaign.gov.uk/be-informed-about-hazards/)). Fridge and freezer timings are covered in the [Food module](module:food).

## What to do

1. Know your network operator: UK Power Networks, National Grid Electricity Distribution, SP Energy Networks, SSEN, Northern Powergrid, Electricity North West, NIE Networks, ESB Networks, Manx Utilities, Jersey Electricity or Guernsey Electricity, depending on region, and {{#if phones}}register on the Priority Services Register if anyone in the house depends on electrical medical equipment{{else}}tell the operator's engineers, the rest centre or the police in person that someone here depends on electrical medical equipment, and register on the Priority Services Register once the lines are back{{/if}}.
2. Remember the basics of the mains: 230 V at 50 Hz, ring finals protected by a 32 A breaker, plugs fused at 13 A, and a 30 mA RCD protecting the circuit; never work on a live circuit ([HSE INDG231, p. 3](doc:hse-indg231#page=3); [Mains electricity](page:mains-electricity)).
3. Run a generator outdoors, at least 6 metres from doors and windows, and never in a garage. Never back-feed it into the house wiring through a "suicide lead"; only feed the house through a transfer switch fitted by an electrician, which is notifiable building work ([Approved Document P, p. 7](doc:ad-p#page=7)).
4. Store petrol for a generator within the 30-litre household limit without notifying the council (Petroleum Regulations link); the detail is in [Vehicles and fuel](module:vehicles-fuel).
5. {{#if power}}Use LED lighting wherever possible and treat candles as a last resort, not a first one; charge the power bank, the torches and the phones now, while the mains is on.{{else}}Light the house with LED torches and lanterns and treat candles as a last resort, not a first one; the power bank goes to phones and this box, not to lighting.{{/if}}
6. Claim compensation for a prolonged outage from your network operator under Ofgem's guaranteed standards once power is restored.

## UK specifics

- Grid-tied solar panels shut themselves down in a power cut unless they are paired with a battery and an islanding switch, so a rooftop array gives no power at all during a typical outage without one ([Solar islanding](page:solar-islanding)).
- A 12.8 V 100 Ah LiFePO4 battery holds about 1,280 Wh; a car battery run through an inverter should not be discharged below half; a 20,000 mAh power bank can keep a phone going for roughly a week of light use.
- Storing petrol at home above 30 litres and up to 275 litres requires written notice to the Petroleum Enforcement Authority ([Petroleum (Consolidation) Regulations 2014](kiwix:legislation_uk/www.legislation.gov.uk/uksi/2014/1637/contents)); repair guides for generators are in the [iFixit generator guides](kiwix:ifixit_en_all/Device/Generator).

## Go deeper

- [What still works](page:what-still-works)
- [Mains electricity](page:mains-electricity)
- [Solar islanding](page:solar-islanding)
- [UK numbers](page:uk-numbers)
- [2025 Iberian Peninsula blackout (Wikipedia)](kiwix:wikipedia_en_all_maxi/2025_Iberian_Peninsula_blackout)
- [Lithium iron phosphate battery (Wikipedia)](kiwix:wikipedia_en_all_maxi/Lithium_iron_phosphate_battery)
- [Fuel stations on the map](map:?overlay=fuel)
