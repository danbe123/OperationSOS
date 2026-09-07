---
id: what-still-works
title: What still works in an outage
icon: plug
order: 4
summary: Service by service, what keeps going when the electricity stops and for how long, and how Emergency Alerts reach you.
category: comms
---

## The table

| Service | Works? | For how long | Notes |
|---|---|---|---|
| Landline (Digital Voice) | No, unless a battery unit | At least an hour of calls from the unit | Landlines now run over broadband and stop with the power; a vulnerable customer's provider must supply a free battery back-up unit that keeps the line up for at least an hour, often longer ([Prepare, phone outages](kiwix:prepare_uk/prepare.campaign.gov.uk/be-informed-about-hazards/phone-broadband-outages/)). The old copper network is being retired, now due January 2027 ([PSTN](kiwix:wikipedia_en_all_maxi/Public_switched_telephone_network)) |
| Mobile calls and data | Limited | Only about a fifth of masts hold an hour of battery and about a twentieth hold six | Parts of the network keep working for a while on back-up power, and the rest come back only as operators get generators to the sites; texts often get through when calls do not; a 999 call roams onto any network with signal ([Prepare, power cuts](kiwix:prepare_uk/prepare.campaign.gov.uk/be-informed-about-hazards/power-cuts/)) |
| Wi-Fi calling | Only while the broadband is up | | A phone set to Wi-Fi calling routes calls through the router when there is no mast signal ([Wi-Fi calling](kiwix:wikipedia_en_all_maxi/Wi-Fi_calling)); the router and fibre box need power, so a small UPS or the power bank keeps them alive |
| Satellite SOS from a phone | Yes, outdoors under open sky | | iPhone 14 and later can text the emergency services by satellite in the UK ([iPhone 14](kiwix:wikipedia_en_all_maxi/IPhone_14)); recent Pixel phones have Satellite SOS ([Pixel 9](kiwix:wikipedia_en_all_maxi/Pixel_9)); a Garmin inReach or similar messenger does the same on a subscription ([Garmin inReach](kiwix:wikipedia_en_all_maxi/Garmin_inReach)). Prepare says satellite services that connect to phones can help when the land networks are down ([Prepare, phone outages](kiwix:prepare_uk/prepare.campaign.gov.uk/be-informed-about-hazards/phone-broadband-outages/)) |
| eCall in the car | Yes, while any mast is up | | Every car type-approved since April 2018 has an SOS button, and an automatic call after a crash, that dials 112 over any mobile network ([eCall](kiwix:wikipedia_en_all_maxi/ECall)) |
| Emergency Alerts | Yes | While any 4G or 5G mast is up | Explained below |
| FM radio | Yes | Batteries or wind-up | BBC Radio 4 on 92.5 to 96.1 MHz ([BBC Radio 4](kiwix:wikipedia_en_all_maxi/BBC_Radio_4)) and BBC local radio; keep a battery or wind-up radio and try FM and digital ([Prepare, power cuts](kiwix:prepare_uk/prepare.campaign.gov.uk/be-informed-about-hazards/power-cuts/)) |
| DAB radio | Yes | Drains batteries faster than FM | DAB receivers need more power than FM sets ([DAB](kiwix:wikipedia_en_all_maxi/Digital_Audio_Broadcasting)) |
| Radio 4 long wave (198 kHz) | Yes, for now | Closure planned | The BBC plans to end Radio 4 on long wave in 2026 ([Droitwich transmitting station](kiwix:wikipedia_en_all_maxi/Droitwich_Transmitting_Station)) |
| TV | No | | |
| Home internet | No | | The router and the fibre box both need power ([Prepare, power cuts](kiwix:prepare_uk/prepare.campaign.gov.uk/be-informed-about-hazards/power-cuts/)) |
| Gas boiler, heat pump | No | | Both need electricity to run ([Prepare, power cuts](kiwix:prepare_uk/prepare.campaign.gov.uk/be-informed-about-hazards/power-cuts/)) |
| Gas hob | Yes | | Light it with a match |
| Mains water | Usually | Hours to days | Supply can be disrupted; high-rise flats lose it first when the booster pumps stop ([Water module](module:water)) |
| Sewers | Usually | | Unless a pumping station fails |
| Fridge | Yes, shut | About 4 hours | ([CMO food advice](kiwix:govuk_resilience/www.gov.uk/government/publications/public-health-advice-from-uk-cmos-during-a-national-power-outage/food-and-nutrition-scripts-for-broadcast-media)) |
| Freezer | Yes, shut | 48 hours if full, 24 hours if half full | ([CMO food advice](kiwix:govuk_resilience/www.gov.uk/government/publications/public-health-advice-from-uk-cmos-during-a-national-power-outage/food-and-nutrition-scripts-for-broadcast-media)) |
| Cash machines and card payments | No | | |
| Petrol pumps | No | | ([Vehicles and fuel](module:vehicles-fuel)) |
| Traffic lights | No | | |
| Trains | Electric: no. Diesel: limited | | |
| Lifts and electric gates | No | | Use the manual release |
| Grid-tied solar panels | No | | Unless a battery with an islanding switch ([Solar islanding](page:solar-islanding)) |
| Electric car (vehicle-to-load) | Yes | Days | ([Vehicles and fuel](module:vehicles-fuel)) |
| Hospitals | Yes | While the generator fuel lasts, then resupply | Standby generators carry A&E, theatres, lifts, IT and essential lighting, not the whole site. A hospital is not a warm place to go to: shelter, warmth and refreshment in an emergency are the council's rest centre ([Evacuation module](module:evacuation)) |
| This box, on a power bank | Yes | Roughly 8 to 15 hours | On the 20,000 mAh power bank ([About Operation SOS](page:about-sos)) |

## Emergency Alerts

Emergency Alerts are the UK's national warning system. They are cell broadcasts sent from 4G and 5G masts to every compatible phone in the affected area, so they need no phone number, no app, no data and no Wi-Fi; the phone makes a loud siren-like sound for about 10 seconds even on silent, and the message says what to do ([Emergency Alerts](kiwix:govuk_resilience/www.gov.uk/alerts); [how alerts work](kiwix:govuk_resilience/www.gov.uk/alerts/how-alerts-work)). You get nothing on a phone that is off, connected only to 2G or 3G, on Wi-Fi only, in airplane mode, or too old for the software (iOS 14.5 or Android 11 and later) ([how alerts work](kiwix:govuk_resilience/www.gov.uk/alerts/how-alerts-work)). UK networks are closing their 3G networks ([3G](kiwix:wikipedia_en_all_maxi/3G)), so an old phone kept "for emergencies" will never receive an alert. There is no national siren network: this is the warning, so check the setting is switched on.

## What to do about it

- Keep a battery or wind-up radio and spare batteries, and write the frequencies down ([Prepare, power cuts](kiwix:prepare_uk/prepare.campaign.gov.uk/be-informed-about-hazards/power-cuts/)).
- {{#if power}}Keep a charged power bank for phones and this box, and top it up whenever the mains is on.{{else}}The power bank is now all you have: phones off between check-ins, screens dim, and this box before anything else.{{/if}}
- {{#if shops}}Keep cash: card readers and cash machines go down with the network.{{else}}Cash is the only money that works: card readers and cash machines are down with the network, so spend small notes carefully.{{/if}}
- Fill in the [household plan](page:household-plan): meeting point, out-of-area contact, numbers on paper.
- If anyone in the house relies on the landline, ask the provider for a battery back-up unit before it is needed, and see the Priority Services Register on [UK numbers](page:uk-numbers).

{{#if scenario:grid-collapse}}
**Read the table as a timetable.** The register's reasonable worst case is a total loss with restoration over several days, up to seven; if the cause is a gas-supply failure instead, expect published rota disconnections on top ([NRR 2025, p. 45](doc:nrr-2025#page=45)), so the mast batteries go in the first hours, the freezer over the first days, and the water follows wherever the pumping needs electricity ([Grid collapse](playbook:grid-collapse)). Move to a listening schedule on FM rather than leaving the radio running, keep the power bank for this box and one phone, and expect fuel and food to be cash and queue rather than card and pump.
{{/if}}

{{#if scenario:emp}}
**Assume the whole column is "no", with no restoration date**, and that Emergency Alerts, which need a 4G or 5G mast, have gone with everything else ([EMP](playbook:emp)). Nobody can tell you in advance what survived, so test everything on receive first ([Nuclear electromagnetic pulse](kiwix:wikipedia_en_all_maxi/Nuclear_electromagnetic_pulse)). A surviving FM receiver is the one national link if the transmitters are still on air, so listen at agreed times rather than continuously.
{{/if}}

{{#if scenario:solar-storm}}
The register expects regional power disruption, loss of GPS, and disruption to satellite communications and shortwave, all at once rather than in a tidy order ([NRR 2025, p. 137](doc:nrr-2025#page=137); [Solar storm](playbook:solar-storm)). So a phone may show bars and still fail, and satellite SOS is unreliable, while FM radio, PMR446 and the VHF and UHF amateur bands keep working because they do not use the ionosphere ([PMR446 channels](page:pmr446)). Cash, paper records and a wind-up radio are the sensible fallbacks.
{{/if}}

## Go deeper

- [UK numbers](page:uk-numbers)
- [Power module](module:power)
- [Communications module](module:comms)
- [Grid collapse](playbook:grid-collapse)
- [Public switched telephone network](kiwix:wikipedia_en_all_maxi/Public_switched_telephone_network)
- [Getting help without phones](page:no-phones)
