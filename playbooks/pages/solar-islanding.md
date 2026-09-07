---
id: solar-islanding
title: Solar panels in a power cut
icon: sun
order: 8
summary: Why a normal solar system switches off with the grid, what it takes to keep the lights on, and what panels and batteries give in Britain.
category: reference
---

## Why the panels go dark

Grid-tied solar inverters are required to disconnect the moment the grid fails, a safety feature called loss-of-mains or anti-islanding protection under the G98 and G99 connection rules, so that linesmen repairing the network are not electrocuted by power fed back from someone's roof ([Islanding](kiwix:wikipedia_en_all_maxi/Islanding); [Solar inverter](kiwix:wikipedia_en_all_maxi/Solar_inverter)). The result is that a standard grid-tied array, however sunny the day, produces nothing usable the moment the power cuts out.

{{#unless power}}
Your roof is producing nothing usable at this moment unless the system has a battery and an islanding switch: the inverter disconnected itself when the grid failed, and that is a safety requirement rather than a fault ([Islanding](kiwix:wikipedia_en_all_maxi/Islanding)). Find out whether the installation has an emergency power supply socket or a changeover switch, and where it is, before you need it. If it has neither, the portable power station and folding panel are what you have: spend that power on this box, phones and torches first.
{{/unless}}

## Keeping some power

There are two ways round it. A hybrid inverter paired with a battery and an emergency power supply (EPS) output can automatically island a separate circuit when the grid drops, feeding chosen sockets or a consumer unit sub-board; a manual changeover switch does the same job by hand. Both routes add a new circuit, which is notifiable electrical work under Part P and needs a registered installer ([Approved Document P, p. 14](doc:ad-p#page=14); [Mains electricity](page:mains-electricity)). The simpler alternative is a portable "solar generator": a lithium power station paired with a folding panel, enough to keep phones, radios, this box and a few LED lights going, and to run a fridge for part of each day if the sun cooperates.

## What a panel gives in Britain

UK solar yield varies hugely by season. London receives about 0.5 kWh of sunshine per square metre a day in December and 4.7 in July, and UK panels average a capacity factor of around 10 per cent over the year ([Solar power in the United Kingdom](kiwix:wikipedia_en_all_maxi/Solar_power_in_the_United_Kingdom)), so a 1 kWp array gives well under 1 kWh a day in midwinter and several kWh a day in midsummer, and a small 100 W folding panel in December is realistically a phone charger, not a heater. A car battery, reached through its 12 V socket and a small inverter, is a useful fallback when there is no sun, but a starter battery is not built for deep discharge and a full discharge shortens its life ([Automotive battery](kiwix:wikipedia_en_all_maxi/Automotive_battery); [Vehicles and fuel](module:vehicles-fuel)). LiFePO4 batteries, the type used in most solar generators, have a nominal 3.2 V per cell, so a 12.8 V 100 Ah battery holds about 1,280 Wh, and they tolerate 2,500 to more than 9,000 charge cycles ([Lithium iron phosphate battery](kiwix:wikipedia_en_all_maxi/Lithium_iron_phosphate_battery)).

{{#if scenario:grid-collapse}}
Over days, run the panel and battery to a routine rather than to demand: charge in the middle of the day, run the fridge or freezer in bursts while the sun is on the panel rather than overnight, give the box and the radio a small fixed share, and stop drawing at the point that leaves enough to start tomorrow ([Grid collapse](playbook:grid-collapse)). LiFePO4 cells tolerate thousands of charge cycles, so daily cycling is exactly what they are for ([Lithium iron phosphate battery](kiwix:wikipedia_en_all_maxi/Lithium_iron_phosphate_battery)).
{{/if}}

{{#if scenario:severe-winter}}
Do not plan a winter around the panels. London receives about 0.7 kWh of sunshine per square metre a day in December against 5.2 in July, so a well-sited 1 kWp array gives roughly one kilowatt-hour a day in midwinter, less if it faces east or west, and a 100 W folding panel is realistically a phone charger, not a heater ([Solar power in the United Kingdom](kiwix:wikipedia_en_all_maxi/Solar_power_in_the_United_Kingdom)). Keep snow and frost off the panel, expect several dull short days in a row, and treat the battery as a store to refill slowly rather than a supply ([Severe winter](playbook:severe-winter)).
{{/if}}

## Go deeper

- [Power module](module:power)
- [Mains electricity](page:mains-electricity)
- [Vehicles and fuel module](module:vehicles-fuel)
- [energypedia](kiwix:energypedia_en_all_maxi/Main_Page)
- [Solar inverter](kiwix:wikipedia_en_all_maxi/Solar_inverter)
