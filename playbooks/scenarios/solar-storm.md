---
id: solar-storm
title: Solar superstorm
icon: sun
order: 5
summary: A Carrington-class geomagnetic storm. Regional blackouts, GPS and satellite loss, HF radio dead, and damaged transformers that take months to replace.
modules: [power, comms, navigation, water, food, vehicles-fuel]
overlays: [fuel, health]
reviewed: null
sources:
  - title: National Risk Register 2025
    doc: nrr-2025
    as_at: 2025-01-16
  - title: Carrington Event (Wikipedia)
    kiwix: wikipedia_en_all_maxi/Carrington_Event
    as_at: 2026-02-15
  - title: March 1989 geomagnetic storm (Wikipedia)
    kiwix: wikipedia_en_all_maxi/March_1989_geomagnetic_storm
    as_at: 2026-02-15
  - title: Geomagnetic storm (Wikipedia)
    kiwix: wikipedia_en_all_maxi/Geomagnetic_storm
    as_at: 2026-02-15
  - title: Coronal mass ejection (Wikipedia)
    kiwix: wikipedia_en_all_maxi/Coronal_mass_ejection
    as_at: 2026-02-15
  - title: RSGB Band Plans 2026
    doc: rsgb-band-plan-2026
    as_at: 2026-01-25
  - title: Prepare, be informed about hazards
    kiwix: prepare_uk/prepare.campaign.gov.uk/be-informed-about-hazards/
    as_at: 2026-09
---

## Right now

**You will have warning.** A coronal mass ejection takes one to three days to reach Earth, fifteen to twenty hours for the fastest ([Coronal mass ejection](kiwix:wikipedia_en_all_maxi/Coronal_mass_ejection)); the Met Office issues space weather forecasts and the Emergency Alert or news will say a severe storm is coming ([Met Office](kiwix:wikipedia_en_all_maxi/Met_Office)). The flare's X-rays and radio bursts arrive in eight minutes and black out HF radio on the sunlit side at once ([Solar flare](kiwix:wikipedia_en_all_maxi/Solar_flare)).

**Use the warning hours** as for a blackout that could last weeks: fill water, charge everything, get cash, fill the tank, buy the two-week food store, and write down where everyone is ([Prepare, hazards](kiwix:prepare_uk/prepare.campaign.gov.uk/be-informed-about-hazards/)). Unplug sensitive electronics before the storm arrives; the danger to house wiring is the surge when the grid protection trips, not the storm itself.

**When the lights go out**, treat it as the [grid collapse playbook](playbook:grid-collapse): 105, the one warm room, fridge shut, radio on ([Power module](module:power)). The register's planning case is a Carrington-scale event lasting one to two weeks with regional power disruption, loss of GPS, satellite communications and HF radio, aviation disruption and possible damage to ground electronics ([NRR 2025, p. 137](doc:nrr-2025#page=137)).

{{module:power}}

## First 72 hours

- **Expect it to repeat.** Each phenomenon "would likely occur several times during a 2-week period" ([NRR 2025, p. 137](doc:nrr-2025#page=137)); a grid brought back on day two may fall again on day four.
- **GPS is wrong or gone.** Loss of positioning and timing takes down transport, telecoms, financial services and emergency services "within a few hours" because they all take their clock from satellites ([NRR 2025, p. 86](doc:nrr-2025#page=86)). Card payments and cash machines depend on that timing; carry cash. Navigate by map, grid reference and compass; a magnetic compass still points north, a few degrees off during the storm ([Navigation module](module:navigation)).
- **Radio.** HF (shortwave and the amateur 160 m to 10 m bands) is dead for hours at a time; VHF and UHF (FM broadcast, PMR446, 2 m and 70 cm amateur) work as normal because they do not use the ionosphere ([Amateur bands](page:amateur-bands); [RSGB Band Plans 2026](doc:rsgb-band-plan-2026)). Satellite phones, satellite internet and satellite TV are unreliable ([Geomagnetic storm](kiwix:wikipedia_en_all_maxi/Geomagnetic_storm)).
- **Aviation** is diverted away from the poles and grounded where GPS approaches are unusable; do not plan to fly ([NRR 2025, p. 137](doc:nrr-2025#page=137)).
- **The aurora** will be visible far south of Scotland, as in May 2024, and is the one harmless part of the event ([May 2024 solar storms](kiwix:wikipedia_en_all_maxi/May_2024_solar_storms)).

{{module:comms}}

{{module:navigation}}

## First month

- **Transformers.** The 1989 storm tripped Quebec's grid in 90 seconds and left six million people without power for nine hours ([March 1989 geomagnetic storm](kiwix:wikipedia_en_all_maxi/March_1989_geomagnetic_storm)); geomagnetically induced currents heat and can destroy the large transformers at grid supply points, and a spare of that size takes months to build and move ([Geomagnetic storm](kiwix:wikipedia_en_all_maxi/Geomagnetic_storm)). If the national operator says transformers are lost, plan for rota disconnection for months ([NRR 2025, p. 94](doc:nrr-2025#page=94)).
- **Satellites** damaged or lost during the storm are not replaced quickly; weather forecasting, GPS accuracy and satellite broadband degrade for months ([NRR 2025, p. 84](doc:nrr-2025#page=84)).
- **Fuel and food** move on lorries whose depots, pumps and payment systems need power and timing; expect the shortages of the [supply chain playbook](playbook:supply-chain).
- **Water** treatment and pumping follow the grid; store, treat and ration as in the [water module](module:water).

{{module:water}}

{{module:food}}

## Long term

The 1859 Carrington event set telegraph offices on fire and lit the sky to the Caribbean; a storm that size against today's grid is the register's reasonable worst case ([Carrington Event](kiwix:wikipedia_en_all_maxi/Carrington_Event)). The storm passes in a fortnight; the damage does not. The pattern after is an intermittent grid for months, so the long-term work is the same as after any grid failure: a house that runs on little power, a battery and panel, a way to cook and heat without mains ([Solar panels in a power cut](page:solar-islanding); [Grid collapse playbook](playbook:grid-collapse)). Vehicles are unaffected by the storm itself; fuel supply is the limit ([Vehicles and fuel module](module:vehicles-fuel)).

{{module:vehicles-fuel}}

## UK specifics

- **Where it bites.** Geomagnetic effects grow with latitude, so Scotland and northern England see the strongest induced currents; the national operator can reconfigure the grid and shed load in advance when the Met Office Space Weather Operations Centre warns ([Met Office](kiwix:wikipedia_en_all_maxi/Met_Office); [Space weather](kiwix:wikipedia_en_all_maxi/Space_weather)).
- **What fails first:** GPS timing in mobile networks and payment systems, then satellite services, then HF radio, then regional power ([NRR 2025, p. 137](doc:nrr-2025#page=137); [NRR 2025, p. 86](doc:nrr-2025#page=86)). Emergency Alerts need a working 4G or 5G mast ([How alerts work](kiwix:govuk_resilience/www.gov.uk/alerts/how-alerts-work)).
- **Numbers:** 105 for power (GB), NIE 03457 643 643, the rest on [UK numbers](page:uk-numbers). Landline and mobile behaviour in a power cut is on [What still works](page:what-still-works).
- **Radio that works:** FM broadcast, PMR446 and the VHF and UHF amateur bands ([PMR446 channels](page:pmr446)); RAYNET volunteers pass traffic for councils when the phones are down ([Radio Amateurs Emergency Network](kiwix:wikipedia_en_all_maxi/Radio_Amateurs_Emergency_Network)).
- **Maps without GPS:** Ordnance Survey grid references off this box or a paper map, and a compass ([Navigation module](module:navigation)).

## Checklist

- [ ] On the warning: fill water, charge every battery, get cash, fill the tank {#warning-hours}
- [ ] Unplug computers, TV, router and chargers before the storm arrives {#unplug-electronics}
- [ ] Paper map or this box's grid reference for every place you may need to reach {#paper-navigation}
- [ ] Battery FM radio and PMR446 sets ready; know that HF and satellite will fail {#vhf-radio-ready}
- [ ] Two weeks of food and water on the shelf {#two-week-store}
- [ ] Blackout routine from the grid collapse playbook rehearsed with the household {#blackout-routine}
- [ ] Cash for a month; card and cash machine failure expected {#cash-month}
- [ ] Medical equipment users on the Priority Services Register {#psr-registered}
- [ ] Watch for repeat storms for two weeks; do not restock the freezer until it is over {#expect-repeats}

## Go deeper

- [Power module](module:power)
- [Communications module](module:comms)
- [Amateur radio bands](page:amateur-bands)
- [Carrington Event (Wikipedia)](kiwix:wikipedia_en_all_maxi/Carrington_Event)
- [Geomagnetic storm (Wikipedia)](kiwix:wikipedia_en_all_maxi/Geomagnetic_storm)
- [Satellite navigation (Wikipedia)](kiwix:wikipedia_en_all_maxi/Satellite_navigation)
- [Space weather (Ready.gov)](kiwix:www.ready.gov_en/www.ready.gov/space-weather)
- [Earth science Q&A](kiwix:earthscience.stackexchange.com_en_all/questions)
- [NRR 2025, severe space weather](doc:nrr-2025#page=137)
- [Grid collapse playbook](playbook:grid-collapse)
- [EMP playbook](playbook:emp)
