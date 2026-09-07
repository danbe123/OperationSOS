# Map: layers in view, one base, and place cards

Date: 2026-09-07. Status: approved in conversation (the owner: "the layers should be always visible, remove base map choice, split airports and military bases up, the tool tips need much more useful information … they wont be able to research what kind of facility, resources etc if they are planning to go there for safety").

## 1. What this is

Four changes to the Map screen and the data behind it:

1. The overlay toggles are always on screen, as a row of chips along the top of the map, not behind a "Layers" button.
2. There is one base map. The OSM (Protomaps) base is used everywhere; the OS Zoomstack choice leaves the interface. (The OS tiles stay on disk and in the build for a later decision; nothing offers them.)
3. "Airports and military bases" becomes two overlays, `airports` and `military`, each with its own chip, colour and icon.
4. Tapping a place opens a **place card** instead of a tooltip: what the place is, what it has, how far it is and how long it takes to walk there, and what to expect from that kind of place in an emergency, with a route and a pin one tap away. Hovering (mouse) keeps a small tooltip with the name and type.

## 2. Layers in view

- A `.map-chips` row sits under the toolbar strip, above the map, scrolling horizontally on a phone: one chip per overlay in the config's order, each with the overlay's icon, a colour dot in the overlay's colour, and a short label (`Footpaths`, `Access land`, `Flood zones`, `Health`, `Fuel`, `Water`, `Rail`, `Nuclear`, `Chemical`, `Airports`, `Military`), pressed when on (`aria-pressed`). Two more chips at the end, `Contours` and `Hillshade`, replace the terrain checkboxes. An unavailable overlay (not built for this box) shows disabled with its coverage note in `title`.
- The Layers button, `LayerPanel` and the legend strip go. The link scheme `map:?overlay=<id>` and the `overlays` query still work; a scenario opening the map switches its overlays on as today.
- The chips' labels come from a short-label map in the frontend (the manifest titles stay long for search and the card).

## 3. One base

`baseId` state, the `BASE_KEY` storage, the base radio and `config.bases` selection in the frontend go; the map always loads the `osm` style for the current theme. The API's `/map/config` keeps listing bases (the field is harmless and other tools read it); the frontend ignores all but `osm`. The OS style files and build step are untouched.

## 4. Airports and military

- `manifest/overlays.json`: `airports-military` becomes two items, `airports` (`nwr/aeroway=aerodrome`; icon `plane`; colour as today) and `military` (`nwr/military=*` plus `nwr/landuse=military`; icon `shield`; colour `#4b6b2f` (the spec first said `#8c564b`, which chemical-sites already uses)), same coverage; the full build measured airports at 1.4 MB, so it ships as geojson, and military at 1.8 MB of tiles, pmtiles. The build (`api/sos/mapbuild/overlays.py`), the verifier, the style layer list (`tools/map-styles/layers/overlays.json`), the describer's titles, and the three scenarios that switch the old overlay on (`invasion`, `volcanic`, `nuclear-war`: their `overlays:` lists and any `map:?overlay=` links) are updated; `sos validate-playbooks` must pass.
- The overlays are rebuilt on this PC from the OSM extract (`sos build-maps --steps overlays --force`, then the `verify` step), copied into the dev content root, and the manifest's `size_bytes`/`as_at` refreshed.

## 5. Richer data

The overlay build keeps more of what OSM already has, so the card can say it. Per overlay, the properties kept (all optional; the card shows only what is present):

| Overlay | Properties kept |
|---|---|
| health | `name, amenity, healthcare, emergency, beds, operator, phone, website, opening_hours, wheelchair, dispensing` |
| fuel | `name, brand, operator, opening_hours, phone, fuel:diesel, fuel:lpg, fuel:electricity, shop` |
| water | `name, man_made, natural, water, landuse, operator, description` |
| rail | `name, operator, network, platforms, wheelchair` |
| airports | `name, aerodrome, aerodrome:type, icao, iata, operator, surface, military` (surface and length of the longest runway are not on the aerodrome node; omitted) |
| military | `name, military, landuse, operator, description, access` |
| chemical-sites | as today plus `operator, hazmat, description` |
| nuclear-sites | as today (hand-authored: type, status, operator) |
| footpaths, access-land, flood-zones | as today |

Values are passed through as strings; a tag missing in OSM is simply absent. The build's property allow-list is one table in `overlays.py`.

## 6. The place card

Opened by a tap (or Enter on a keyboard-focused feature) on any overlay feature, as a panel like the existing `MapPanel`s (a bottom sheet on a phone, the right-hand panel on the kiosk), dismissed with its close button, Escape, or a tap on the map elsewhere. Contents, top to bottom:

1. **Name** (or the type when unnamed) and a type line: "NHS hospital · emergency department" / "Fuel station · Tesco" / "Water treatment works" / "Royal Air Force station" / "International airport" / "Barracks" / "Railway station · Southern" / "Nuclear power station · operating" / "Flood zone 3" / "Public footpath".
2. **Distance and time**: from home when set, else from the map centre: "4.6 km, WNW, about 56 min on foot" (existing `distanceKm`, `bearingDeg`, `naismithMinutes`), and the OS grid reference.
3. **What it has**, as rows, from the data: for health, A&E (from `emergency=yes`), beds, dispensing, wheelchair, opening hours, phone, website, operator; for fuel, brand, diesel/LPG/electric availability, opening hours, phone, whether it has a shop; for water, the type (works, reservoir, spring), operator; for rail, operator, platforms; for airports, type, ICAO/IATA, operator; for military, the type, operator, access; for chemical and nuclear, the type, status, operator; for flood zones, the chance line; for footpaths, the designation and who may use it.
4. **What to expect here**, a short paragraph for the place's kind, written once as content and citing the guides: for example, for a hospital in an outage, that A&E stays open on generators for a few days but non-urgent care stops, to go only for a life-threatening problem and take medicines and a list; for a fuel station, that pumps need mains power and most close in a blackout, that cash may be the only payment, and the 30 L rule; for a water works, that it is not a place to fetch water and that treated water comes from bowsers and the company's bottled-water stations; for a military base, that it is not a refuge, that armed guards will turn people away, and that in an invasion or nuclear scenario it is a target to move away from; for an airport, that it closes to the public in a crisis and is a target and an evacuation hub only under official instruction; for a nuclear site, the REPPIR zone and the go in, stay in, tune in rule; for a chemical site, the plume rule and going upwind; for a rail station, that it is a landmark and a shelter with a roof, not a service; for a flood zone, what the zone means for staying or leaving; for a footpath, the access law in one line. Each paragraph ends with one link into the guides (`page:`, `module:` or `card:`).
5. **Actions**: "Route from home" (the existing route description), "Pin this place", "Nearby from here" (opens the Nearby panel centred on the place).

The guidance lives in `playbooks/map/places.yaml`: one entry per place kind (`hospital`, `pharmacy`, `gp`, `clinic`, `fuel`, `water-works`, `reservoir`, `spring`, `rail-station`, `airport`, `military`, `nuclear`, `chemical`, `flood-zone`, `footpath`, `access-land`), each with `title`, `expect` (Markdown, 40 to 120 words, at least one guide link, citations where a figure appears) and `link` (the guide to open). It is validated by `sos validate-playbooks` (links, sources) and served as `GET /api/map/places` (rendered HTML per kind) so the frontend never parses Markdown. The frontend's describer maps a feature to a kind (`amenity=hospital` → `hospital`, `emergency=yes` also → `hospital`, `man_made=water_works` → `water-works`, `military=*` → `military`, and so on).

## 7. Nearby

The Nearby panel's rows link to the same place card (tap a row → card), and the card's "Nearby from here" reuses the panel with the place as origin.

## 8. Tests

- Build: the property allow-list per overlay; the split ids; `verify` requires both new files and rejects the old one.
- API: `/api/map/places` returns every kind with HTML; the validator checks `places.yaml` links.
- Web: chips render one per overlay in order with pressed state, toggle layers, show disabled with the coverage note, and the two terrain chips; no Layers button, no base radio; the card opens on tap with the type line, the distance line, the rows the fixture carries, the expect paragraph and the three actions; the hover tooltip is name and type only; a feature with no name shows its type as the name; `describe.ts` maps every overlay to a kind, including the split; scenario opening with `overlays` still switches chips on.
- Content: `validate-playbooks` passes with the split ids and the new YAML; the three scenarios' overlay lists resolve.

## 9. Risks

- The overlay rebuild runs over the whole extract (osmium filters and tippecanoe); allow for it and keep the old files until the new ones verify.
- Property completeness in OSM varies; the card must read well with only a name and a type.
- Two chips more than fit a 390 px width: the chip row scrolls and shows its edge fade as the tools strip already does.

## 10. Survival content in the tooltip (added 2026-09-07, after the owner's review: "insights, useful info for people looking to survive: resources likely, use case", and "all the existing tooltip hover-over of places expanded, not more overlays")

### 10.1 Every kind says more

Every kind in `playbooks/map/places.yaml` carries, besides `title`, `expect` and `link`, four lists of short bullets:

| Key | Heading | Content | Count |
|---|---|---|---|
| `have` | Usually here | the resources a place of this kind normally holds and whether they survive an outage: water, food, fuel, power, heat, shelter, tools, medical, comms, people with skills | 3 to 7 |
| `useful` | Worth going when | the situations in which this place helps, by scenario (blackout, flood, cold, no water, evacuation, injury, war) | 2 to 5 |
| `avoid` | Stay away when | when it is dangerous, pointless or a target; crowds, looting, contamination, closure | 2 to 5 |
| `approach` | How to go about it | what to bring, when in the day, who to ask, how to behave, what to offer, the law | 2 to 6 |

Each bullet is 6 to 30 words, plain UK English, present tense, imperative where it is an instruction, inline Markdown allowed (a guide link where a guide carries the point), a figure only where a guide already carries it. `expect` stays the 40 to 120 word framing paragraph. The schema requires all four lists with those counts; `sos validate-playbooks` checks every link in them.

`GET /api/map/places` returns per kind `{title, html, sections: [{id, title, html}], link: {href, title}}`, `sections` in the order have, useful, avoid, approach, each `html` a rendered `<ul>` (the bullets as Markdown list items, links resolved).

### 10.2 The hover tooltip carries it

Section 6's "hover keeps a small tooltip with the name and type" is withdrawn. The hover popup shows the whole description: the name, the type line, the "What it has" rows from the data, then the four sections with their headings from the guidance for the feature's kind, then the guide's title as a line (the popup takes no pointer events, so it holds no links). It is no longer a MapLibre popup anchored to the point (a popup this tall was cut off by the map's edge): it is a panel docked inside the map, top and bottom margins of 8 px, on the side of the map away from the pointer (right when the pointer is in the left half, left otherwise), up to 420 px wide and never more than 48 % of the map's width, scrolling when the content is taller than the map. It takes pointer events, so the pointer can move into it and read it; it hides when the pointer leaves both the feature and the panel, and a tap anywhere still opens the card or closes it. Its text stays at the app's reading size and the sections' bullets are tight lists. A kind with no guidance (an unknown overlay) shows the name, the type and the rows as before. The tap still opens the card, which shows the same content with the `expect` paragraph and the actions; the card is the touch path to the same words.

The feature's own values are still text nodes; the guidance HTML is the box's own rendered content and is inserted as HTML.
