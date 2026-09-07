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
  - title: Geomagnetically induced current (Wikipedia)
    kiwix: wikipedia_en_all_maxi/Geomagnetically_induced_current
    as_at: 2026-02-15
  - title: Coronal mass ejection (Wikipedia)
    kiwix: wikipedia_en_all_maxi/Coronal_mass_ejection
    as_at: 2026-02-15
  - title: RSGB Band Plans 2026
    doc: rsgb-band-plan-2026
    as_at: 2026-01-25
  - title: Prepare, power cuts
    kiwix: prepare_uk/prepare.campaign.gov.uk/be-informed-about-hazards/power-cuts/
    as_at: 2026-09
---

## Right now

**You will have warning.** A coronal mass ejection takes one to three days to reach Earth, fifteen to twenty hours for the fastest ([Coronal mass ejection](kiwix:wikipedia_en_all_maxi/Coronal_mass_ejection)); severe space weather is a listed national risk, forecast like weather, so an Emergency Alert or the news will say a severe storm is coming ([NRR 2025, p. 137](doc:nrr-2025#page=137); [Space weather](kiwix:wikipedia_en_all_maxi/Space_weather)). The flare's X-rays and radio bursts arrive in eight minutes and black out HF radio on the sunlit side at once ([Solar flare](kiwix:wikipedia_en_all_maxi/Solar_flare)).

{{#if power}}**Use the warning hours** as for a blackout that could last weeks: fill water, charge everything, get cash, fill the tank, buy the two-week food store, and write down where everyone is{{else}}**The warning hours have gone** with the power: ration the batteries and the power bank, spend the cash you have, fill every container while the water still runs, and write down where everyone is{{/if}} ([Prepare, hazards](kiwix:prepare_uk/prepare.campaign.gov.uk/be-informed-about-hazards/)). Unplug computers, the TV, the router and chargers before the storm arrives; it is the surge when power comes back that damages them ([Prepare, power cuts](kiwix:prepare_uk/prepare.campaign.gov.uk/be-informed-about-hazards/power-cuts/)).

**When the lights go out**, treat it as the [grid collapse playbook](playbook:grid-collapse): the one warm room, fridge shut, radio on, and the network operator told — [[call 105]] ([Power module](module:power)). The register's planning case is a Carrington-scale event lasting one to two weeks with regional power disruption, loss of GPS, satellite communications and HF radio, aviation disruption and possible damage to ground electronics ([NRR 2025, p. 137](doc:nrr-2025#page=137)).

{{module:power}}

## First 72 hours

- **Expect it to repeat.** Each phenomenon "would likely occur several times during a 2-week period" ([NRR 2025, p. 137](doc:nrr-2025#page=137)); a grid brought back on day two may fall again on day four.
- **GPS is wrong or gone.** Loss of positioning and timing takes down transport, telecoms, financial services and emergency services "within a few hours" because they all take their clock from satellites ([NRR 2025, p. 86](doc:nrr-2025#page=86)). Card payments and cash machines depend on that timing; carry cash. Navigate by map, grid reference and compass, and know that a magnetic compass can be disturbed while the storm is running ([Geomagnetic storm](kiwix:wikipedia_en_all_maxi/Geomagnetic_storm); [Navigation module](module:navigation)).
- **Radio.** HF (shortwave and the amateur 160 m to 10 m bands) is dead for hours at a time; VHF and UHF (FM broadcast, PMR446, 2 m and 70 cm amateur) work as normal because they do not use the ionosphere ([Amateur bands](page:amateur-bands); [RSGB Band Plans 2026](doc:rsgb-band-plan-2026)). Satellite phones, satellite internet and satellite TV are unreliable ([Geomagnetic storm](kiwix:wikipedia_en_all_maxi/Geomagnetic_storm)).
- **Aviation** is diverted away from the poles and grounded where GPS approaches are unusable; do not plan to fly ([NRR 2025, p. 137](doc:nrr-2025#page=137)).
- **The aurora** will be visible far south of Scotland, as in May 2024, and is the one harmless part of the event ([May 2024 solar storms](kiwix:wikipedia_en_all_maxi/May_2024_solar_storms)).

{{module:comms}}

{{module:navigation}}

## First month

- **Transformers.** The 1989 storm tripped Quebec's grid in 90 seconds and left six million people without power for nine hours ([March 1989 geomagnetic storm](kiwix:wikipedia_en_all_maxi/March_1989_geomagnetic_storm)); geomagnetically induced currents heat and can destroy the large transformers at grid supply points ([Geomagnetic storm](kiwix:wikipedia_en_all_maxi/Geomagnetic_storm)). The register expects power lost to safety trips in urban areas to come back within hours, but where a transformer in a remote coastal area has to be replaced, recovery takes several months on mobile generation ([NRR 2025, p. 138](doc:nrr-2025#page=138)); if that is your area, plan for the rota disconnection of the [grid collapse playbook](playbook:grid-collapse).
- **Satellites** come back over several days, a small number never; flight schedules take weeks to settle ([NRR 2025, p. 138](doc:nrr-2025#page=138)).
- **Fuel and food** move on lorries whose depots, pumps and payment systems need power and timing; expect the shortages of the [supply chain playbook](playbook:supply-chain).
- **Water** treatment and pumping follow the grid; store, treat and ration as in the [water module](module:water).

{{module:water}}

{{module:food}}

## Long term

The storm passes in a fortnight; three things outlast it. **Timing.** The register's own assumption for a long loss of satellite positioning and timing is that "sectors would revert to older technologies or alternatives" ([NRR 2025, p. 86](doc:nrr-2025#page=86)): paper maps, mechanical and radio-set clocks, cash, cheques and paper records, which is why a household that has kept those habits through the first month should keep them until the banks and the phone networks say their timing is stable. **Satellites.** Those damaged or dragged out of orbit by the heated upper atmosphere are gone ([Geomagnetic storm](kiwix:wikipedia_en_all_maxi/Geomagnetic_storm)); a small number are written off after the register's storm, and the catalogue of what is still up there takes weeks to rebuild, raising the collision risk for the rest ([NRR 2025, p. 138](doc:nrr-2025#page=138)), so satellite broadband, satellite phones and GPS accuracy stay degraded long after the aurora has faded. **Recurrence.** Carrington in 1859 was the largest storm on record and Kew and Greenwich magnetograms show it exceeded the one-in-a-hundred-years value for this latitude ([Carrington Event](kiwix:wikipedia_en_all_maxi/Carrington_Event)); storms of 1872 and 1921 were comparable by some measures, and in July 2012 an ejection of comparable strength missed the Earth ([Carrington Event](kiwix:wikipedia_en_all_maxi/Carrington_Event)); 1989 and 2003 were smaller and still tripped grids ([Geomagnetic storm](kiwix:wikipedia_en_all_maxi/Geomagnetic_storm)). The sun runs an eleven-year cycle ([Solar cycle](kiwix:wikipedia_en_all_maxi/Solar_cycle)), so expect a lesser storm every decade or so and a Carrington-scale one within a long lifetime: whatever you had to improvise this time (a battery, a way to cook, a paper map, cash) becomes permanent kit ([Solar panels in a power cut](page:solar-islanding)).

{{module:vehicles-fuel}}

## UK specifics

- **Where it bites.** The impacts depend on latitude, on how much a place relies on satellites, and on how resilient its engineered systems are ([NRR 2025, p. 138](doc:nrr-2025#page=138)). Since 1989 power companies in the United Kingdom and elsewhere have invested against induced currents ([Geomagnetically induced current](kiwix:wikipedia_en_all_maxi/Geomagnetically_induced_current)), and on a warning the operator can protect transformers by disconnecting them or shedding load, which is a planned blackout rather than a broken one ([Geomagnetic storm](kiwix:wikipedia_en_all_maxi/Geomagnetic_storm)).
- **What fails first:** GPS timing in mobile networks and payment systems, then satellite services, then HF radio, then regional power ([NRR 2025, p. 137](doc:nrr-2025#page=137); [NRR 2025, p. 86](doc:nrr-2025#page=86)). Emergency Alerts need a working 4G or 5G mast ([How alerts work](kiwix:govuk_resilience/www.gov.uk/alerts/how-alerts-work)).
- **How long here:** urban power lost to safety trips returns in hours; a remote coastal transformer takes months to replace and its area runs on mobile generators meanwhile; satellite services days; long-haul flights weeks ([NRR 2025, p. 138](doc:nrr-2025#page=138)).
- **Radio that works:** FM broadcast, PMR446 and the VHF and UHF amateur bands ([PMR446 channels](page:pmr446)); RAYNET volunteers pass traffic for councils when the phones are down ([Radio Amateurs Emergency Network](kiwix:wikipedia_en_all_maxi/Radio_Amateurs_Emergency_Network)).
- **Stock:** the government's baseline is three days; this box plans for 14 days at 3 litres a person a day, food for two weeks, and cash for two weeks of essentials in small notes ([Prepare](kiwix:prepare_uk/prepare.campaign.gov.uk/get-prepared-for-emergencies/)).

## Checklist

- [ ] On the warning: every container filled, every battery and power bank charged, cash drawn, tank filled {#warning-hours now}
- [ ] Computers, TV, router and chargers unplugged before the storm arrives {#unplug-electronics now}
- [ ] Battery FM radio on and PMR446 sets ready; expect HF, satellite and GPS to fail {#vhf-radio-ready now}
- [ ] When the lights go: the grid collapse routine — fridge shut, cooker off, one warm room, radio on {#blackout-routine now}
- [ ] Paper map out, or this box's grid reference written down for every place you may need to reach {#paper-navigation hour}
- [ ] Two weeks of food and water on the shelf {#two-week-store today}
- [ ] Cash for two weeks of essentials in small notes; card and cash machine failure expected {#cash-month today}
- [ ] Medical equipment users on the Priority Services Register {#psr-registered week}
- [ ] Repeat storms watched for over two weeks; the freezer not restocked until it is over {#expect-repeats week}

## Go deeper

- [Power module](module:power)
- [Communications module](module:comms)
- [Amateur radio bands](page:amateur-bands)
- [Carrington Event (Wikipedia)](kiwix:wikipedia_en_all_maxi/Carrington_Event)
- [Geomagnetic storm (Wikipedia)](kiwix:wikipedia_en_all_maxi/Geomagnetic_storm)
- [Geomagnetically induced current (Wikipedia)](kiwix:wikipedia_en_all_maxi/Geomagnetically_induced_current)
- [Satellite navigation (Wikipedia)](kiwix:wikipedia_en_all_maxi/Satellite_navigation)
- [Space weather (Ready.gov)](kiwix:www.ready.gov_en/www.ready.gov/space-weather)
- [Earth science Q&A](kiwix:earthscience.stackexchange.com_en_all/questions)
- [NRR 2025, severe space weather](doc:nrr-2025#page=137)
- [Grid collapse playbook](playbook:grid-collapse)
- [EMP playbook](playbook:emp)
