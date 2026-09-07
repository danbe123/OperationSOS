---
id: amateur-bands
title: Amateur radio bands
icon: antenna
order: 2
summary: UK amateur bands, calling frequencies, repeater shifts, licence levels and callsigns, CB radio, and who may transmit in an emergency.
category: comms
---

## Licence levels and callsigns

Since February 2024, Ofcom's amateur licence has three levels: Foundation (25 W), Intermediate (100 W) and Full (1,000 W), each opening more of the spectrum and requiring a harder exam ([Ofcom amateur licence conditions, p. 15](doc:ofcom-amateur-licence-2024#page=15); [p. 20](doc:ofcom-amateur-licence-2024#page=20)). New callsigns start M7 (Foundation), 2E0 (Intermediate) or M0 (Full); older licences still carry M3 and M6 (Foundation), 2E1 (Intermediate) or G and M1 (Full). The second character is a Regional Secondary Locator that says where the station is: E for England (optional), M for Scotland, W for Wales, I for Northern Ireland, D for the Isle of Man, J for Jersey and U for Guernsey, so a Scottish Foundation station is MM7, an Intermediate one 2M0 and a Full one MM0; Intermediate callsigns beginning with 2 must always carry the locator ([Ofcom amateur licence conditions, p. 7](doc:ofcom-amateur-licence-2024#page=7); [p. 8](doc:ofcom-amateur-licence-2024#page=8)). Listening on any band needs no licence at all; transmitting on an amateur band without one is a criminal offence, and PMR446 and CB are the licence-free alternatives ([PMR446 channels](page:pmr446)).

## Bands

| Band | Frequencies |
|---|---|
| 160 m | 1.810 to 2.000 MHz |
| 80 m | 3.500 to 3.800 MHz |
| 40 m | 7.000 to 7.200 MHz |
| 30 m | 10.100 to 10.150 MHz |
| 20 m | 14.000 to 14.350 MHz |
| 17 m | 18.068 to 18.168 MHz |
| 15 m | 21.000 to 21.450 MHz |
| 12 m | 24.890 to 24.990 MHz |
| 10 m | 28.000 to 29.700 MHz |
| 6 m | 50.000 to 52.000 MHz |
| 4 m | 70.000 to 70.500 MHz |
| 2 m | 144.000 to 146.000 MHz |
| 70 cm | 430.000 to 440.000 MHz |

These are the band edges from the current RSGB plan; which slice of each band you may use, and at what power, depends on your licence level ([RSGB Band Plans 2026](doc:rsgb-band-plan-2026)).

## Calling and repeaters

The FM calling frequencies are 145.500 MHz on 2 m and 433.500 MHz on 70 cm; the SSB calling frequency on 2 m is 144.300 MHz. Repeaters listen on one frequency and transmit on another: 2 m repeaters use a 600 kHz shift and 70 cm repeaters a 1.6 MHz shift, all listed in the RSGB plan ([RSGB Band Plans 2026](doc:rsgb-band-plan-2026)). What works when: 2 m and 70 cm carry local, line-of-sight traffic; 40 m and 80 m reach across the UK by day and night; 20 m reaches Europe and beyond, conditions allowing. A solar storm can black out HF propagation for hours at a time ([Solar storm](playbook:solar-storm)).

{{#if scenario:solar-storm}}
**HF is the casualty, VHF and UHF are not.** The flare's X-rays black out shortwave on the sunlit side within minutes, so 160 m to 10 m may be dead for hours at a time and satellite links are unreliable ([Solar flare](kiwix:wikipedia_en_all_maxi/Solar_flare); [Solar storm](playbook:solar-storm)). Work 2 m, 70 cm and the local repeaters, which do not use the ionosphere and keep going, and try HF again at intervals and after dark rather than sitting on a dead band ([RSGB Band Plans 2026](doc:rsgb-band-plan-2026)).
{{/if}}

## CB radio

UK CB radio is licence-free: FM only, 4 W output, on the 40 UK channels and the 40 CEPT channels around 27 MHz ([CB radio in the United Kingdom](kiwix:wikipedia_en_all_maxi/CB_radio_in_the_United_Kingdom); [Citizens band radio](kiwix:wikipedia_en_all_maxi/Citizens_band_radio)). Channel 9 is the emergency calling channel by convention and channel 19 the calling channel; there is no 24-hour monitoring service in the UK, only whoever happens to be listening ([CB radio in the United Kingdom](kiwix:wikipedia_en_all_maxi/CB_radio_in_the_United_Kingdom)). A CB set in a car reaches further than PMR446 and needs no exam.

## In an emergency

RAYNET volunteers provide backup communications to local councils, the emergency services and event organisers, and can be activated through the local authority in a major incident ([RAYNET](kiwix:wikipedia_en_all_maxi/Radio_Amateurs_Emergency_Network)). An unlicensed person may only use a licensed station with the licensee present and in control of it ([Ofcom amateur licence conditions](doc:ofcom-amateur-licence-2024)). In a genuine emergency, when there is a danger to life, a licensee may pass a message for anyone. Anyone may listen: a cheap scanner or a handheld tuned to 145.500 MHz hears what the local operators are saying.

{{#unless mobile}}
With the mobile network down, radio is how households talk to each other and to whoever is organising help. Listen first, on 145.500 MHz, on 433.500 MHz and on the local repeaters, which needs no licence at all, and note who is on the air and at what times. In a genuine emergency, where there is a danger to life, a licensee may pass a message for anyone ([Ofcom amateur licence conditions](doc:ofcom-amateur-licence-2024)); RAYNET is activated through the local authority, so the rest centre or the council's emergency planners are the way in ([RAYNET](kiwix:wikipedia_en_all_maxi/Radio_Amateurs_Emergency_Network); [getting help without phones](page:no-phones)).
{{/unless}}

{{#unless internet}}
There is no callsign lookup, no online repeater directory and no cluster to tell you what is open: the band table and the shifts on this page, and the RSGB plan in the library, are what you have ([RSGB Band Plans 2026](doc:rsgb-band-plan-2026)). Write your nearest repeater's frequency and shift, and the calling frequencies, onto the paper household plan now, while you can still read them here ([Household plan](page:household-plan)).
{{/unless}}

{{#if scenario:emp}}
**Test on receive before you transmit.** Assume anything that was plugged into the mains or an outside aerial is a loss, and that short, unplugged equipment, a handheld that sat in a metal tin above all, most likely came through ([Nuclear electromagnetic pulse](kiwix:wikipedia_en_all_maxi/Nuclear_electromagnetic_pulse); [EMP](playbook:emp)). Listen on the FM broadcast band and on 145.500 MHz at agreed times rather than continuously, keep the cells for those schedules, and expect which transmitters survived to be the thing nobody can tell you in advance.
{{/if}}

## Go deeper

- [PMR446 channels](page:pmr446)
- [Communications module](module:comms)
- [Getting help without phones](page:no-phones)
- [Amateur Radio Q&A](kiwix:ham.stackexchange.com_en_all/questions)
- [RSGB Band Plans 2026](doc:rsgb-band-plan-2026)
