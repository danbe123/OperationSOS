---
id: tools-repair
title: Tools and repair
icon: tools
order: 15
summary: The tool kit and spares to keep, fixing what you have, and the safety rules for chainsaws, roofs and building work.
sources:
  - title: iFixit
    kiwix: ifixit_en_all/home/home
    as_at: 2025-12-21
  - title: Home Improvement Q&A
    kiwix: diy.stackexchange.com_en_all/questions
    as_at: 2026-08-03
  - title: HSE INDG317 Chainsaws at work
    doc: hse-indg317
    as_at: 2026-09
  - title: Knots Library (zimgit)
    kiwix: zimgit-knots_en/home
    as_at: 2024-08-29
  - title: Approved Document A
    doc: ad-a
    as_at: 2013-04
  - title: HSE INDG231 Electrical safety and you
    doc: hse-indg231
    as_at: 2026-09
  - title: Restarters wiki
    kiwix: restarters_en_all/Main_Page
    as_at: 2026-04-25
  - title: FM 5-125 Rigging Techniques
    doc: fm-5-125-rigging
    as_at: 1995-01
---

## Key facts

- Keep a core kit: claw hammer, saw, adjustable spanner, pliers, screwdrivers, Stanley knife, tape measure, spirit level, hand drill, wire cutters, work gloves and safety glasses.
- Keep spares too: 13 A and 3 A BS 1362 fuses, duct tape, cable ties, galvanised wire, screws and nails, tarpaulin, rope, plastic sheeting and silicone sealant.
- Asbestos is common in pre-2000 buildings: never cut or sand a material you suspect contains it ([DIY Q&A](kiwix:diy.stackexchange.com_en_all/questions)).

## What to do

1. Before writing off a dead torch, radio, power bank, phone or generator, follow the iFixit teardown and repair guide for that device, and check the Restarters wiki on battery faults, which are most of what fails ([iFixit torches](kiwix:ifixit_en_all/Device/Flashlight); [radios](kiwix:ifixit_en_all/Device/Radio); [power banks](kiwix:ifixit_en_all/Device/Power_Bank); [generators](kiwix:ifixit_en_all/Device/Generator); [Restarters: batteries](kiwix:restarters_en_all/Batteries)).
2. For plumbing and general building questions, the DIY Q&A is a good source, but remember it is largely American, so its wiring advice does not apply here ([diy Q&A](kiwix:diy.stackexchange.com_en_all/questions)).
3. If you must use a chainsaw, wear chaps, a helmet and gloves, never cut above shoulder height, and stay clear of the kickback zone ([HSE INDG317, p. 1](doc:hse-indg317#page=1)).
4. Do not go outside to repair storm damage while the storm is still blowing ([Prepare, storms](kiwix:prepare_uk/prepare.campaign.gov.uk/be-informed-about-hazards/storms/)). Afterwards, cover a damaged roof from a ladder or inside the loft with a tarpaulin held by battens screwed through it into the rafters, never by bricks that blow off, and board broken windows with plywood screwed to the frame; leave anything that means standing on the roof to a roofer with scaffolding.
5. Learn a handful of knots and lashings for improvised shelters and securing loads ([Knots Library](kiwix:zimgit-knots_en/home)).

{{#unless power}}
**Hand tools only.** A brace and bit, a hand drill, a panel saw and a sharp chisel do everything a cordless tool does, more slowly, and the battery packs are a finite store for the jobs nothing else can do. Work in daylight where you can and by head torch where you cannot. Never assume a circuit is dead because the power is off: supply can return without warning. Switching off at the consumer unit is as far as an untrained person should go — safe isolation and proving dead need training and proper test equipment under the Electricity at Work Regulations 1989, so leave anything beyond that to a registered electrician ([HSE INDG231, p. 3](doc:hse-indg231#page=3)).
{{/unless}}

{{#unless shops}}
**Repair rather than replace, and keep the carcass.** With nothing to buy, a dead appliance is a store of screws, wire, switches, bearings and a good mains lead: strip it, label the parts and keep them dry ([iFixit](kiwix:ifixit_en_all/home/home); [Restarters](kiwix:restarters_en_all/Main_Page)). Standardise on the fixings and battery sizes you already hold so that parts move between tools. Consumables run out long before tools do — blades, drill bits, fuses, tape, sealant, screws and glue — so ration them, and sharpen what can be sharpened, which is salvage practice rather than guidance ([woodworking Q&A](kiwix:woodworking.stackexchange.com_en_all/questions)).
{{/unless}}

{{#if scenario:grid-collapse}}
**What fails in a blackout is the small equipment you have suddenly started depending on:** torches, radios, power banks and the generator. Most of those failures are the battery or the power supply rather than the device, so open them before writing them off ([Restarters: batteries](kiwix:restarters_en_all/Batteries)). Keep a stock of the cells your torches and radio actually take. Check the generator before you need it, oil, fuel and air filter, and run it occasionally under load: that is maintenance practice rather than published guidance, but a generator that has stood unused for a year is the one that will not start ([iFixit generator guides](kiwix:ifixit_en_all/Device/Generator)).
{{/if}}

{{#if scenario:supply-chain}}
**Buy the consumables, not more tools.** What stops a repair is rarely the tool: it is the blade, the fuse, the sealant, the tarpaulin or the right screw. Fill those gaps early and in ordinary quantities while deliveries are still running, and buy the spares specific to what you own, the boiler's seals, the pump's impeller, the bicycle's tubes and brake blocks. Keep tarpaulin, plastic sheeting, timber, screws and rope in hand, because a storm-damaged roof gets covered with whatever is already in the shed. No official list covers this; it is what repairs actually take ([Post Disaster Resource Library](kiwix:zimgit-post-disaster_en/home)).
{{/if}}

{{#if scenario:long-rebuild}}
**Treat tools as capital.** Sharpen with a stone rather than replacing, re-handle rather than discarding, keep steel oiled and out of the damp, and teach whoever will learn: the household that can sharpen, solder, sew and splice still has working things in year two. Pool the heavy and rarely used tools in one place, with a written register and a borrowing book ([Community module](module:community)). Move heavy loads with rope, tackle and levers instead of machines ([Rigging Techniques, FM 5-125](doc:fm-5-125-rigging)), and salvage carefully: pre-2000 buildings are full of asbestos, which is never cut or sanded.
{{/if}}

## UK specifics

- Know where your stopcock is and how to deal with a frozen pipe before winter arrives, covered in the [severe winter playbook](playbook:severe-winter) (lag pipes, the loft hatch, the stopcock, a frozen boiler condensate pipe).
- Do not remove or cut into a structural wall or prop without checking Approved Document A first ([Approved Document A](doc:ad-a)).
- Keep tools sharp with a stone rather than replacing them, and use the woodworking Q&A for longer-term projects ([woodworking Q&A](kiwix:woodworking.stackexchange.com_en_all/questions)).

## Go deeper

- [iFixit](kiwix:ifixit_en_all/home/home)
- [Home Improvement Q&A](kiwix:diy.stackexchange.com_en_all/questions)
- [Woodworking Q&A](kiwix:woodworking.stackexchange.com_en_all/questions)
- [Knots Library](kiwix:zimgit-knots_en/home)
- [Approved Document H, p. 31](doc:ad-h#page=31)
- [Power module](module:power)
- [Restarters: how things work and how to fix them](kiwix:restarters_en_all/Main_Page)
- [Rigging Techniques, FM 5-125 (moving heavy loads by rope and tackle)](doc:fm-5-125-rigging)
- [Rope, knots and tools](page:fieldcraft-rope-tools)
