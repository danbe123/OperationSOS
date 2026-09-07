---
id: rebuild-power
title: Power from scratch
icon: bolt
order: 206
summary: Water, wind, scrap alternators, lead-acid batteries and wood gas, with the arithmetic to size them, the honest limits and the safety rules.
category: rebuild
---

## Decide what the power is for

Generating electricity is easy; generating enough is not. Settle the priorities first, because they decide the design:

1. **Light.** LED lamps turn a few watt-hours into a usable evening, and light is what most changes how much a day contains.
2. **Charging.** This box, radios, torches, power banks and hand tools. A few tens of watt-hours a day covers it.
3. **Refrigeration for medicines.** Insulin and some other drugs need cold, and a small fridge run intermittently is the first load big enough to design around.
4. **Pumping water.** Lifting water beats carrying it, and a pump run for an hour a day serves a lot of people.
5. **The workshop.** Grinding, drilling and charging batteries; the largest and the most postponable.

Everything below charges a battery bank and the loads run off the battery: very little of what you build makes power at the moment you want it.

## Water, if you have any

Falling water is the best small power source there is: it runs day and night, it is strongest in a British winter when sun is weakest, and a wheel or turbine can be built from scrap ([Micro hydro](kiwix:wikipedia_en_all_maxi/Micro_hydro)). Two numbers decide everything — the **head**, the vertical drop in metres, and the **flow** in cubic metres per second.

**Gross power = ρ g Q H**, where ρ is 1,000 kg/m³ for water, g is 9.81 m/s², Q is the flow in m³/s and H the head in metres ([College Physics 2e](doc:openstax-college-physics-2e)).

**Worked example.** A stream you can dam to give a 3 m drop, running 20 litres a second, which is 0.02 m³/s:

- Gross: 1,000 × 9.81 × 0.02 × 3 = **589 W**.
- Take the losses. Turbine efficiency is generally 50 to 80%, and pipe friction, the drive and the generator take more ([Micro hydro](kiwix:wikipedia_en_all_maxi/Micro_hydro)). At an honest 50% overall you have about **295 W**.
- Continuously, that is 7 kWh a day — enough for a village's lighting, all the charging, a fridge and a pump, with power to spare.

Measure the flow with a bucket and a pendulum clock — time a ten-litre bucket filling from the full stream, or a float over a measured channel length times the cross-section — and the head with a levelled board or a water-filled hose. Then pick the machine: high head and low flow suit a Pelton wheel made from spoons or split pipe; low head and high flow suit an overshot or breastshot wheel or an Archimedes screw. Overshot wheels are the efficient ones, up to about 90%, while undershot wheels historically managed around 20% ([Water wheel](kiwix:wikipedia_en_all_maxi/Water_wheel); [Water wheel calculations](kiwix:engineering.stackexchange.com_en_all/questions/24083/water-wheel-calculations-required); [Hydraulic wheels and impulse turbines](kiwix:appropedia_en_all/Hydraulic_wheels_and_impulse_turbines); [Microhydro](kiwix:appropedia_en_all/Microhydro)).

Mind the mill work as well as the electricity. A wheel turns at perhaps 10 to 30 rpm and any generator wants thousands, so the step-up gearing is most of the engineering — and while it turns, every part of the drive is a trap. Build a sluice that stops the wheel from a safe standing position, and never work on the drive without it shut.

## Wind

Wind power goes as the cube of the wind speed: **P = ½ ρ A v³**, with ρ about 1.225 kg/m³, A the swept area in m² and v in m/s. No machine can take more than 59.3% of that — the Betz limit — and a small real one takes far less ([Betz's law](kiwix:wikipedia_en_all_maxi/Betz's_law); [Wind turbine](kiwix:wikipedia_en_all_maxi/Wind_turbine)).

**Worked example.** A 2 m diameter rotor sweeps 3.14 m². At 5 m/s the wind carries 241 W through it; the Betz limit allows 143 W; a home-built machine at perhaps 30% overall gives about **72 W**. At 7 m/s the same rotor sees 660 W in the wind and roughly 200 W out.

The cube is the whole lesson. Doubling the wind gives eight times the power, so where you put the machine — high, clear of buildings and trees by a good margin — matters far more than how cleverly it is built ([Small wind turbine](kiwix:appropedia_en_all/Small_wind_turbine); [Types of wind turbines](kiwix:appropedia_en_all/Types_of_wind_turbines)). Wind also needs a dump load or a way to furl: a turbine left spinning with nothing connected can run away and destroy itself.

## A generator from scrap

**A car alternator** is the obvious donor and it disappoints people. It is built to be belt-driven at two to three times engine speed, so it needs high rpm before it gives anything useful, and a water wheel at 20 rpm needs something like a hundred to one step-up to feed it. It needs field excitation, a small current fed in to start it generating, so it will not self-start from a dead battery without help. Its regulator is set to charge a 12 V lead-acid battery and does nothing else. Efficiency at medium speed is about 70 to 80% and falls off sharply at high speed, mostly in the cooling fan ([Alternator (automotive)](kiwix:wikipedia_en_all_maxi/Alternator_(automotive)); [Motor/generator set using a car alternator](kiwix:electronics.stackexchange.com_en_all/questions/592741/motor-generator-set-using-car-alternator)). What it is good at is exactly one job: charging a 12 V battery bank when driven fast and steadily.

**Permanent-magnet machines are better at low speed.** The direct-drive stator out of a modern washing machine, rectified through three-phase diodes, makes a genuinely useful low-rpm generator, and a treadmill motor gives DC directly. The brushed "universal" motor from an older washing machine is a poor generator and needs rewiring to work at all ([Converting a washing machine motor](kiwix:electronics.stackexchange.com_en_all/questions/647764/is-it-possible-to-convert-a-washing-machine-motor-to-become-a-useful-wind-turb); [Electric generator](kiwix:wikipedia_en_all_maxi/Electric_generator)).

Whatever the machine, put a rectifier, a fuse and a charge controller between it and the battery: an unregulated generator with no load will over-volt and cook what it feeds ([Charge controller](kiwix:wikipedia_en_all_maxi/Charge_controller)).

## Lead-acid batteries, and their hazards

Lead-acid is the battery you will actually have: it is in every vehicle, it tolerates being rebuilt, and it does not need electronics to keep it safe. Treat it well and it lasts years; treat it badly and it dies in months ([Lead–acid battery](kiwix:wikipedia_en_all_maxi/Lead–acid_battery); [Deep-cycle battery](kiwix:wikipedia_en_all_maxi/Deep-cycle_battery)).

- A cell sits at about 2.10 V open-circuit when fully charged, so a rested 12 V battery reads about 12.6 V. Float it at around 2.27 V per cell — some 13.6 V — and charge it at about 14.4 V ([Lead–acid battery](kiwix:wikipedia_en_all_maxi/Lead–acid_battery); [Safe float charge levels](kiwix:electronics.stackexchange.com_en_all/questions/161147/determine-lead-acid-battery-safe-float-charge-level-for-a-range-of-state-of-ch)).
- **Do not leave it flat.** Deep discharge and standing discharged cause sulfation, which permanently takes away capacity. Recharge promptly, and design the system so a half-discharged bank is a full day's use.
- **Charging makes hydrogen.** Overcharging electrolyses the water into hydrogen and oxygen; that mixture explodes, and an exploding battery sprays acid and casing fragments. Charge in a ventilated place, never a sealed cupboard, no flames, no smoking, no sparks; make and break connections at the charger end, away from the battery.
- **The electrolyte is sulphuric acid.** Goggles and gloves; flush any splash with a great deal of water; top up only with distilled or clean rainwater, after charging, never before.
- **Fuse it at the battery.** A car battery will push hundreds of amps into a short circuit and set a cable or a spanner glowing in seconds. Put a properly rated fuse in the positive lead within a few centimetres of the terminal, use cable that suits the current, and keep tools away from the terminals ([Choosing a fuse for a battery system](kiwix:electronics.stackexchange.com_en_all/questions/459603/how-to-choose-the-correct-fuse-in-a-double-paralled-battery-supply-system); [Fuse](kiwix:wikipedia_en_all_maxi/Fuse_(electrical))).

## Wood gas, for engines

A gasifier partly burns wood or charcoal with restricted air and makes producer gas, which an ordinary petrol engine will run on. One measured charcoal producer gave 50.9% nitrogen, 27% carbon monoxide, 14% hydrogen, 4.5% carbon dioxide and 3% methane ([Wood gas](kiwix:wikipedia_en_all_maxi/Wood_gas)). Two honest limits follow from that. Half of it is nitrogen doing nothing, so the gas holds far less energy per litre than petrol vapour and the engine makes noticeably less power than it did on petrol. And tar is the practical enemy: a gasifier running too cool produces tar, and tar gums up an engine quickly, so the gas must be cooled and filtered before it goes anywhere near one ([Wood gas generator](kiwix:wikipedia_en_all_maxi/Wood_gas_generator)). Charcoal gasifiers are much simpler than wood gasifiers for exactly this reason — the tar was already driven off when the charcoal was made ([Making things again](page:rebuild-making-things)).

**The fuel is a poison.** Better than a quarter of that gas is carbon monoxide, which has no smell and no warning. Gasifiers of proven design are used outdoors or in a partially enclosed space; never run or refuel one inside a building, and never test a leak by breathing ([Wood gas generator](kiwix:wikipedia_en_all_maxi/Wood_gas_generator); [Carbon monoxide card](card:carbon-monoxide)).

## The first grid

Low-voltage direct current does not travel, and the arithmetic makes the point. Copper has a resistivity of about 1.68 × 10⁻⁸ Ω·m, so 2.5 mm² cable is roughly 0.0067 Ω per metre. A run 20 m out and back is 40 m and about 0.27 Ω; at 10 A that loses 2.7 V — more than a fifth of a 12 V supply — and wastes 27 W as heat in the wire ([Electrical resistivity](kiwix:wikipedia_en_all_maxi/Electrical_resistivity_and_conductivity); [Voltage drop](kiwix:wikipedia_en_all_maxi/Voltage_drop); [A 12 V lighting circuit in a house](kiwix:engineering.stackexchange.com_en_all/questions/289/would-it-make-sense-to-have-a-12v-lighting-circuit-in-a-house)).

So the first grid is not a grid. In order of sense: put the loads where the power is, so the workshop, the mill and the pump sit at the water wheel; charge batteries and lamps at a central charging point and carry them home; use fat cable and short runs for anything that must be wired; and raise the voltage before you lengthen the wire, because at 48 V the same power draws a quarter of the current and loses a sixteenth of the energy. Wiring a village properly, at mains voltage, needs a transformer, regulation, earthing and protection, and belongs well down the road.

## Safety, and the law that still applies

- Every source gets an isolator you can reach and a fuse close to it. Label both.
- **Never connect a generator, an inverter or a battery system to the house wiring except through a changeover switch that disconnects the property from the network first.** Back-feeding energises the street cables and can kill someone working on what they believe is a dead line. It is also notifiable work under Part P. The full rules are on [Mains electricity](page:mains-electricity) and, for panels and islanding, [Solar panels in a power cut](page:solar-islanding).
- Run any fuel-burning engine or generator outdoors, well away from doors and windows, exhaust pointing away ([Power module](module:power)).
- Store petrol and diesel within the household limits in the [Vehicles and fuel module](module:vehicles-fuel).
- Prove dead before touching anything, and treat every circuit as live until you have ([Tools and repair module](module:tools-repair)).

## Go deeper

- [Micro hydro](kiwix:wikipedia_en_all_maxi/Micro_hydro)
- [Water wheel](kiwix:wikipedia_en_all_maxi/Water_wheel)
- [Betz's law](kiwix:wikipedia_en_all_maxi/Betz's_law)
- [Lead–acid battery](kiwix:wikipedia_en_all_maxi/Lead–acid_battery)
- [College Physics 2e (OpenStax)](doc:openstax-college-physics-2e)
- [Electronics Q&A](kiwix:electronics.stackexchange.com_en_all/questions)
- [Engineering Q&A](kiwix:engineering.stackexchange.com_en_all/questions)
- [Solar panels in a power cut](page:solar-islanding)
- [Power module](module:power)
