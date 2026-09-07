---
id: comms
title: Communications
icon: radio
order: 7
summary: The numbers that matter, what still works when the power is off, Emergency Alerts, FM radio, PMR446, CB and amateur radio.
sources:
  - title: How emergency alerts work (GOV.UK)
    kiwix: govuk_resilience/www.gov.uk/alerts/how-alerts-work
    as_at: 2026-09-05
  - title: Prepare, phone and broadband outages
    kiwix: prepare_uk/prepare.campaign.gov.uk/be-informed-about-hazards/phone-broadband-outages/
    as_at: 2026-09-05
  - title: PMR446 (Wikipedia)
    kiwix: wikipedia_en_all_maxi/PMR446
    as_at: 2026-02-15
  - title: CB radio in the United Kingdom (Wikipedia)
    kiwix: wikipedia_en_all_maxi/CB_radio_in_the_United_Kingdom
    as_at: 2026-02-15
  - title: RSGB Band Plans 2026
    doc: rsgb-band-plan-2026
    as_at: 2026-01-25
  - title: Ofcom amateur radio licence conditions
    doc: ofcom-amateur-licence-2024
    as_at: 2024-02-21
  - title: National Risk Register 2025
    doc: nrr-2025
    as_at: 2025-01-16
---

## Key facts

- {{#if phones}}The numbers that matter:{{else}}The numbers that matter, none of which will connect until the network is back ([getting help without phones](page:no-phones)):{{/if}} 999 or 112 from any phone with a SIM; 999 by text after registering by texting "register" to 999; 111; 105; the gas emergency line 0800 111 999 in Great Britain (0800 002 001 in Northern Ireland); Floodline 0345 988 1188 in England, Scotland and Wales (0300 2000 100 in Northern Ireland); 101; Samaritans 116 123. The full list is on [UK numbers](page:uk-numbers).
- The National Risk Register lists a simultaneous loss of all fixed and mobile forms of communication among its reasonable worst-case scenarios, alongside the risk of a cyber attack on telecommunications systems ([NRR 2025, p. 88](doc:nrr-2025#page=88); [NRR 2025, p. 55](doc:nrr-2025#page=55)).
- In a power cut the landline, the broadband and most mobile masts stop within hours; what keeps going, for how long, and the satellite and Wi-Fi routes that still reach 999 are all on [What still works](page:what-still-works) ([Prepare, phone outages](kiwix:prepare_uk/prepare.campaign.gov.uk/be-informed-about-hazards/phone-broadband-outages/)).

## What to do

1. Get a battery or wind-up FM radio and write down the frequencies you use; the stations, and how long each service lasts without power, are on [What still works](page:what-still-works) ([Prepare, phone outages](kiwix:prepare_uk/prepare.campaign.gov.uk/be-informed-about-hazards/phone-broadband-outages/)).
2. Check Emergency Alerts are switched on: the phone-based national warning, explained on [What still works](page:what-still-works) ([how alerts work](kiwix:govuk_resilience/www.gov.uk/alerts/how-alerts-work)).
3. For short-range talking, use PMR446 walkie-talkies: licence-free and good for a few kilometres; the channels, tones and rules are on [PMR446 channels](page:pmr446) ([PMR446](kiwix:wikipedia_en_all_maxi/PMR446)).
4. Fill in the household communications plan on [Household plan](page:household-plan): meeting point, out-of-area contact, every number on paper, and the "come now" signal.
5. Listening to any radio service needs no licence; transmitting on the amateur or marine bands does ([Amateur bands](page:amateur-bands)). When nothing connects, [Getting help without phones](page:no-phones) covers runners, radios and satellite, and the whistle rescue signal is on [Getting found](page:fieldcraft-rescue).

{{#unless mobile}}
**An emergency call is the last thing to go.** A 999 call roams onto any network that has coverage, so a phone showing no bars on your own network, or "emergency calls only", may still get through — [[call 999]] ([Prepare, power cuts](kiwix:prepare_uk/prepare.campaign.gov.uk/be-informed-about-hazards/power-cuts/)). Move before you give up: higher ground, an upstairs window, the far side of the building, a main road. A text often gets through where a call will not, and 999 by text works from a phone registered in advance. Emergency Alerts ride on 4G and 5G masts, so they stop when the masts do ([What still works](page:what-still-works)).
{{/unless}}

{{#unless landline}}
**The landline is broadband now.** A Digital Voice line stops with the power or the broadband, and a provider must give a vulnerable customer a free battery back-up unit that holds the line up for at least an hour, often longer: ask for it before you need it ([Prepare, phone outages](kiwix:prepare_uk/prepare.campaign.gov.uk/be-informed-about-hazards/phone-broadband-outages/); [What still works](page:what-still-works)). With the line dead, what is left is a mobile, a neighbour's phone on a different network, or a walk to a fire station, which stays crewed and keeps its own radio to control ([Getting help without phones](page:no-phones)).
{{/unless}}

{{#unless internet}}
**Nothing that needs the internet will work:** messaging, email, Wi-Fi calling, video calls and every instruction that says check the website ([What still works](page:what-still-works)). This box needs none of it and serves everything over its own Wi-Fi. Take the official picture from BBC local radio on FM and from Emergency Alerts, which are broadcast by the masts and need no data at all. Put what the street needs to know on a noticeboard at a place everyone passes, the hall door or the shop window, with the date and time written on every notice.
{{/unless}}

{{#unless phones}}
**Fall back to runners, radio and a board.** Send messages in pairs, on foot or by bicycle, written down: who, what, where as a grid reference from the map, when, and how many ([Getting help without phones](page:no-phones)). Agree one PMR446 channel for the street and a listening schedule, a few minutes on the hour, so that nobody flattens a battery listening all day ([PMR446 channels](page:pmr446)). Keep one household by the radio to write down each bulletin, and put the summary on the noticeboard so the same question is not asked at forty doors.
{{/unless}}

## UK specifics

- CB radio is licence-free in the UK, FM at 4 W around 27 MHz; the amateur licence has had three levels since February 2024; RAYNET is the volunteer emergency network: all on [Amateur bands](page:amateur-bands) ([CB radio in the United Kingdom](kiwix:wikipedia_en_all_maxi/CB_radio_in_the_United_Kingdom); [Ofcom amateur licence conditions](doc:ofcom-amateur-licence-2024); [RSGB Band Plans 2026](doc:rsgb-band-plan-2026)).
- Radio 4 long wave on 198 kHz is due to close; the date and the FM frequencies that replace it are on [What still works](page:what-still-works).

## Go deeper

- [UK numbers](page:uk-numbers)
- [What still works](page:what-still-works)
- [PMR446 channels](page:pmr446)
- [Amateur bands](page:amateur-bands)
- [Amateur Radio Q&A](kiwix:ham.stackexchange.com_en_all/questions)
- [Cell Broadcast (Wikipedia)](kiwix:wikipedia_en_all_maxi/Cell_Broadcast)
- [RAYNET (Wikipedia)](kiwix:wikipedia_en_all_maxi/Radio_Amateurs_Emergency_Network)
- [Getting found](page:fieldcraft-rescue)
- [Getting help without phones](page:no-phones)
