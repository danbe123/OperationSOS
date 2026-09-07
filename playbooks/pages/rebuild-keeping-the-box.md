---
id: rebuild-keeping-the-box
title: Keeping the box alive
icon: drive
order: 201
summary: Power, drives and spares for this box, from solar and battery to card and SSD lifespan, a spare Pi in a tin, and what to print first.
category: rebuild
---

## What this box is, in hardware

A Raspberry Pi 5 with 8 GB of memory, a 500 GB NVMe solid-state drive on a carrier board under the Pi, a 7-inch touchscreen, and its own WiFi. It needs no internet, no mobile network and no grid: only a USB-C supply and somewhere dry ([About Operation SOS](page:about-sos)). Everything below is about keeping that small machine running for as long as it can be run, and getting the knowledge off it before it stops.

Treat it as a library, not a gadget. It is the only thing in the village that holds the NHS pages, Wikipedia, the manuals and the maps, and the day it fails is the day that knowledge is whatever somebody wrote down.

## Power: how little it needs

The official supply is a 27 W USB-C unit, but that is the headroom the Pi is allowed to draw, not what this box uses. Work from the runtime instead: a 20,000 mAh USB-C power bank runs it for roughly 8 to 15 hours, the longer figure with the screen off ([About Operation SOS](page:about-sos); [What still works](page:what-still-works)). A 20,000 mAh cell at its nominal 3.7 volts holds about 74 watt-hours, and perhaps 60 survive the conversion to 5 volts, so those runtimes work out at roughly 4 to 5 watts with the screen off and 6 to 8 watts with it lit. That is arithmetic from the box's own figures rather than a measurement, but it is the right order: this box costs about as much power as a bright LED bulb, and a 250 Wh portable battery station runs it for about two days.

That changes what it takes to keep it alive:

- **A panel and a battery, sized for a lamp rather than a house.** UK panels average a capacity factor of about 10 per cent over the year, so a 100 W panel averages around 10 W, and London gets about 0.5 kWh of sunshine per square metre a day in December against 4.7 in July ([Solar panels in a power cut](page:solar-islanding)). A single 100 W folding panel with a charge controller therefore covers this box comfortably in summer and only on the brighter winter days, so the battery, not the panel, is what carries it through a dull week ([Photovoltaic system](kiwix:wikipedia_en_all_maxi/Photovoltaic_system); [Maximum power point tracking](kiwix:wikipedia_en_all_maxi/Maximum_power_point_tracking)).
- **Store in LiFePO4 if you have the choice.** A 12.8 V 100 Ah lithium iron phosphate battery holds about 1,280 Wh and tolerates 2,500 to more than 9,000 charge cycles, which is weeks of this box per charge and years of cycling; a car starter battery is not built for deep discharge and a full discharge shortens its life ([Solar panels in a power cut](page:solar-islanding); [Power module](module:power)).
- **Run it to a timetable.** An hour in the morning and an hour in the evening, with a written list of what to look up, uses a fraction of what leaving it on all day does. The box's own low power mode dims the screen and stops the AI, and it stops the AI again if the processor gets too hot.

{{#unless power}}
With the mains off, this box is on the power bank and every hour of it is spent, so decide what it is for: looking things up that people need today, and printing while the printer can still be run. Screen off between questions, low power mode on, and the panel or the bank charged in daylight rather than left to run flat overnight ([Power module](module:power)).
{{/unless}}

## The drives, and how long they last

This box boots and reads from an NVMe solid-state drive, not a memory card, which is deliberate: cards are the part that fails first in a Raspberry Pi. Both store data as trapped electrical charge, and that has two consequences worth knowing.

**Writing wears it out; reading does not.** Flash has a finite number of program–erase cycles, and controllers spread writes across the chip to make them last ([Flash memory](kiwix:wikipedia_en_all_maxi/Flash_memory); [Wear leveling](kiwix:wikipedia_en_all_maxi/Wear_leveling); [Solid-state drive](kiwix:wikipedia_en_all_maxi/Solid-state_drive)). A library that is read all day and written to rarely is the gentlest possible use. What does damage it is losing power mid-write, so shut the box down properly rather than pulling the plug.

**An unpowered drive is not an archive.** The stored charge leaks away over years through imperfect insulation, faster when it is warm ([Data degradation](kiwix:wikipedia_en_all_maxi/Data_degradation); [Flash memory](kiwix:wikipedia_en_all_maxi/Flash_memory)). So a drive in a drawer is a copy with an expiry date nobody can read. Power every spare drive up once a year, read the whole of it back, and copy it afresh onto another drive every few years. Store drives cool and dry, in a sealed bag with a desiccant sachet, out of the sun.

## A spare card and a spare Pi, in a tin

Keep, in one metal tin with a tight lid: a spare Raspberry Pi, a microSD card with the operating system written to it, a spare USB-C cable and supply, and one copy of the library on a drive. Wrap each item in cloth, cardboard or bubble wrap so nothing touches the metal, and keep the tin closed and the contents unplugged from anything.

The reason for the tin is electromagnetic pulse, and it needs stating honestly. A Faraday cage is a continuous conductive covering or mesh that blocks external electric fields, which is why sensitive electronics travel in conductive bags ([Faraday cage](kiwix:wikipedia_en_all_maxi/Faraday_cage); [Electromagnetic pulse](kiwix:wikipedia_en_all_maxi/Electromagnetic_pulse)). Nobody can tell you in advance what would survive a pulse; the reasoning, not a sourced fact, is that what was switched off, unplugged and away from long wires is the likelier survivor ([Power module](module:power)). A biscuit tin is not a laboratory enclosure. It costs nothing, it also keeps out damp, mice and casual borrowing, and that is reason enough.

## Copying the library

The library is about 200 GB in the core tier and several hundred more in the extended one, so the core copy fits a 500 GB drive and the whole thing wants 2 TB ([About Operation SOS](page:about-sos)). Copy it with `rsync`, which resumes where it stopped and copies only what changed, and check the copy afterwards rather than assuming it ([rsync](kiwix:wikipedia_en_all_maxi/Rsync)):

```
rsync -av --partial --progress /srv/sos/ /mnt/spare/sos/
sha256sum -c checksums.txt
```

Then follow the ordinary rule for anything you cannot lose: three copies, on two kinds of media, with one of them somewhere else ([Backup](kiwix:wikipedia_en_all_maxi/Backup)). In a village that means the box, a drive in another building, and paper. Label every drive with what it holds and the date it was copied, because an unlabelled drive gets wiped by whoever finds it.

## What to print, and in what order

Printing is the one irreversible win: paper needs no power, no drive and no you. Print while there is still a working printer and ink, one side of the sheet, on the best paper you have, and keep it dry and flat in a box; acid-free paper is what archives use because ordinary paper goes brittle and brown ([Acid-free paper](kiwix:wikipedia_en_all_maxi/Acid-free_paper)). Two copies, in two buildings. In this order:

1. **[The essentials, printed](page:rebuild-essentials-printed)** — the one-page sheets, printed as a bundle. If you print nothing else, print this.
2. **The medical cards** you would use in the dark: [severe bleeding](card:severe-bleeding), [CPR](card:cpr-adult), [recovery position](card:recovery-position), [burns](card:burns), [wound cleaning](card:wound-cleaning), [childbirth](card:childbirth).
3. **[Water disinfection](page:water-disinfection)**, the whole table, because it is the difference between drinking and dysentery.
4. **[The first year](page:rebuild-first-year)** and your filled-in [household plan](page:household-plan), with the village register, rota and charter copied out fresh.
5. **Your map**, printed at a scale you can walk with, with grid references on it ([Navigation module](module:navigation)).
6. **The growing and animal calendar** for your own ground ([Growing food module](module:growing-food); [Livestock module](module:livestock)).

## Teaching from it before it dies

The box is a school for as long as it runs, and what leaves it in somebody's head or handwriting outlives it. The library holds full textbooks: chemistry, physics, biology, anatomy and physiology, microbiology, nutrition, pre-algebra and statistics ([Chemistry](doc:openstax-chemistry-2e); [College Physics](doc:openstax-college-physics-2e); [Biology](doc:openstax-biology-2e); [Prealgebra](doc:openstax-prealgebra-2e)), and the extended tier carries the Khan Academy lessons for the same subjects.

An hour a day, with a named teacher and a rota of children, in this order: reading and writing, then arithmetic and measurement, then the practical science of water, food, illness and materials ([Restarting science](page:rebuild-restarting-science)), then everything else. The output is not a screen watched but a notebook written, copied out by hand, kept in the hall. That is how libraries survived every previous collapse, and it is the only method here that does not depend on a machine.

## The day it dies

It will die, and probably without warning. When it does, the printed bundle is the library, so keep it where it can be found and read aloud ([The essentials, printed](page:rebuild-essentials-printed)). Keep the drives even so: they are ordinary files, and a working computer may turn up years later in a village that still has power and someone who can read them ([Total collapse and the long rebuild](playbook:long-rebuild)).

## Go deeper

- [The first year](page:rebuild-first-year)
- [The essentials, printed](page:rebuild-essentials-printed)
- [Law, records and trade](page:rebuild-law-and-trade)
- [About Operation SOS](page:about-sos)
- [What still works](page:what-still-works)
- [The library map](page:rebuild-library-map)
- [Power from scratch](page:rebuild-power)
- [Solar panels in a power cut](page:solar-islanding)
- [Power module](module:power)
- [Tools and repair module](module:tools-repair)
- [Solar energy on Low-tech Magazine](kiwix:solar.lowtechmagazine.com_mul_all/solar.lowtechmagazine.com/)
- [energypedia](kiwix:energypedia_en_all_maxi/Main_Page)
- [Appropedia](kiwix:appropedia_en_all/Welcome_to_Appropedia)
