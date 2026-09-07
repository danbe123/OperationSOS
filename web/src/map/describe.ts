import { REGIONS } from './overlays';

/** The kind of real-world place a feature is, for the place card: null when the overlay has no fixed kind. */
export type PlaceKind =
  | 'hospital' | 'pharmacy' | 'gp' | 'clinic' | 'fuel' | 'water-works' | 'reservoir' | 'spring' | 'rail-station'
  | 'airport' | 'military' | 'nuclear' | 'chemical' | 'flood-zone' | 'footpath' | 'access-land';

/** What the map tooltip says about one overlay feature: a title, the overlay it belongs to, a one-line type and plain-English rows. */
export type FeatureDescription = { title: string; overlay: string; typeLine: string; kind: PlaceKind | null; rows: [string, string][] };

export type FeatureProperties = Record<string, unknown>;

export type DescribeOptions = {
  /** The vector layer the feature came from (pmtiles overlays), e.g. `flood_england`. */
  sourceLayer?: string;
  /** The overlay title from the map config; falls back to the built-in title for the id. */
  overlayTitle?: string;
};

/** What a describe* helper produces before the overlay title is attached. */
type Described = { title: string; typeLine: string; kind: PlaceKind | null; rows: [string, string][] };

/** Titles from manifest/overlays.json, for when the caller has no config to hand. */
export const OVERLAY_TITLES: Record<string, string> = {
  footpaths: 'Footpaths and rights of way',
  'access-land': 'Open access land',
  'flood-zones': 'Flood zones',
  health: 'Hospitals, pharmacies and GP surgeries',
  fuel: 'Fuel stations',
  water: 'Reservoirs and water works',
  rail: 'Railway stations',
  'nuclear-sites': 'Nuclear sites',
  'chemical-sites': 'Major chemical and fuel sites',
  airports: 'Airports and airfields',
  military: 'Military bases and land',
};

const HEALTH_TYPES: Record<string, string> = {
  hospital: 'Hospital', pharmacy: 'Pharmacy', doctors: 'GP surgery', clinic: 'Clinic', dentist: 'Dentist',
};

const NUCLEAR_TYPES: Record<string, string> = {
  'power-station': 'Nuclear power station', naval: 'Naval nuclear base', research: 'Nuclear research site',
  fuel: 'Nuclear fuel plant', weapons: 'Atomic weapons establishment', reprocessing: 'Nuclear reprocessing plant',
};
const NUCLEAR_STATUS: Record<string, string> = {
  operating: 'Operating', decommissioning: 'Being decommissioned', defuelling: 'Closed, fuel being removed',
  construction: 'Under construction', closed: 'Closed',
};

const INDUSTRIAL_TYPES: Record<string, string> = {
  refinery: 'Oil refinery', chemical: 'Chemical works', oil: 'Oil terminal or depot', gas: 'Gas terminal or works',
};

const MILITARY_TYPES: Record<string, string> = {
  airfield: 'Military airfield', barracks: 'Barracks', naval_base: 'Naval base', base: 'Military base',
  range: 'Firing range', danger_area: 'Military danger area', training_area: 'Military training area',
  depot: 'Military depot', bunker: 'Military bunker', office: 'Military office', checkpoint: 'Military checkpoint',
  nuclear_explosion_site: 'Nuclear test site', obstacle_course: 'Military training ground', school: 'Military school',
};
const AERODROME_TYPES: Record<string, string> = {
  international: 'International airport', regional: 'Regional airport', public: 'Public airfield',
  private: 'Private airfield', military: 'Military airfield', airfield: 'Airfield', gliding: 'Gliding site',
};

const DESIGNATIONS: Record<string, { title: string; users: string }> = {
  public_footpath: { title: 'Public footpath', users: 'On foot' },
  public_bridleway: { title: 'Public bridleway', users: 'On foot, on horseback and by bicycle' },
  restricted_byway: { title: 'Restricted byway', users: 'On foot, on horseback, by bicycle and horse-drawn vehicle; no motor vehicles' },
  byway_open_to_all_traffic: { title: 'Byway open to all traffic', users: 'All traffic, including motor vehicles' },
  core_path: { title: 'Scottish core path', users: 'On foot, on horseback and by bicycle (right of responsible access)' },
  permissive_footpath: { title: 'Permissive footpath', users: 'On foot, with the landowner’s permission (can be withdrawn)' },
  permissive_bridleway: { title: 'Permissive bridleway', users: 'On foot, on horseback and by bicycle, with the landowner’s permission' },
  national_trail: { title: 'National Trail', users: 'On foot' },
};
const HIGHWAY_TYPES: Record<string, string> = {
  footway: 'Footway', path: 'Path', bridleway: 'Bridleway', track: 'Track', cycleway: 'Cycle path', steps: 'Steps', pedestrian: 'Pedestrian street',
};
const ACCESS_VALUES: Record<string, string> = {
  yes: 'Open to the public', designated: 'Signed for this use', permissive: 'Allowed by the landowner (can be withdrawn)',
  private: 'Private, no public access', no: 'No public access', customers: 'Customers only', destination: 'Access to reach a destination only',
  unknown: 'Not known', discouraged: 'Use discouraged',
};
const SAC_SCALE: Record<string, string> = {
  hiking: 'Easy walking', mountain_hiking: 'Mountain walking, some steep ground', demanding_mountain_hiking: 'Demanding mountain walking, sure-footedness needed',
  alpine_hiking: 'Alpine walking, hands needed in places', demanding_alpine_hiking: 'Demanding alpine route, scrambling', difficult_alpine_hiking: 'Difficult alpine route, climbing',
};
const TRAIL_VISIBILITY: Record<string, string> = {
  excellent: 'Path clear to see', good: 'Path mostly clear', intermediate: 'Path faint in places', bad: 'Path hard to follow', horrible: 'Path very hard to follow', no: 'No visible path',
};

const FLOOD_ZONES: Record<string, { title: string; chance: string }> = {
  '3': { title: 'Flood zone 3', chance: 'High: a 1 in 100 or greater chance of river flooding, or 1 in 200 or greater of sea flooding, in any year' },
  '2': { title: 'Flood zone 2', chance: 'Medium: between a 1 in 100 and 1 in 1,000 chance of river flooding, or 1 in 200 to 1 in 1,000 of sea flooding, in any year' },
  '1': { title: 'Flood zone 1', chance: 'Low: less than a 1 in 1,000 chance of river or sea flooding in any year' },
};

/** SEPA (Scotland) and OPW (Ireland) publish river/coastal flood risk as bands rather than the England/Wales zone system. */
const RIVER_CHANCE: Record<string, string> = {
  Scotland: 'Medium: a 1 in 200 or greater chance of river flooding in any year (SEPA)',
  'Republic of Ireland': 'A 1 in 100 or greater chance of river flooding in any year (OPW)',
};
const COASTAL_CHANCE: Record<string, string> = {
  Scotland: 'A 1 in 200 or greater chance of sea flooding in any year (SEPA)',
  'Republic of Ireland': 'A 1 in 200 or greater chance of sea flooding in any year (OPW)',
};

function str(v: unknown): string | null {
  if (v === null || v === undefined) return null;
  const s = String(v).trim();
  return s && s.toLowerCase() !== 'null' ? s : null;
}

function first(props: FeatureProperties, ...keys: string[]): string | null {
  for (const k of keys) {
    const v = str(props[k]);
    if (v) return v;
  }
  return null;
}

/** OSM-style value to words: `water_works` becomes `Water works`. */
export function humanise(value: string): string {
  const words = value.replace(/[_-]+/g, ' ').replace(/\s+/g, ' ').trim();
  return words ? words[0].toUpperCase() + words.slice(1) : words;
}

const DAYS: Record<string, string> = { Mo: 'Mon', Tu: 'Tue', We: 'Wed', Th: 'Thu', Fr: 'Fri', Sa: 'Sat', Su: 'Sun', PH: 'bank holidays' };

/** Light touch on OSM opening_hours: day codes spelled out, ranges as "to", 24/7 in words. */
export function openingHours(value: string): string {
  if (value.trim() === '24/7') return 'Open 24 hours a day, every day';
  return value
    .replace(/\b(Mo|Tu|We|Th|Fr|Sa|Su|PH)-(Mo|Tu|We|Th|Fr|Sa|Su|PH)\b/g, (_, a: string, b: string) => `${DAYS[a]} to ${DAYS[b]}`)
    .replace(/\b(Mo|Tu|We|Th|Fr|Sa|Su|PH)\b/g, (d: string) => DAYS[d])
    .replace(/\boff\b/g, 'closed')
    .replace(/;\s*/g, '; ');
}

function yesNo(v: string): string {
  const s = v.toLowerCase();
  if (s === 'yes' || s === 'true') return 'Yes';
  if (s === 'no' || s === 'false') return 'No';
  return humanise(v);
}

/** Rows most OSM point overlays share, in a fixed order, only where the property exists. */
function commonRows(props: FeatureProperties): [string, string][] {
  const rows: [string, string][] = [];
  const operator = first(props, 'operator');
  if (operator) rows.push(['Run by', operator]);
  const phone = first(props, 'phone', 'contact:phone');
  if (phone) rows.push(['Phone', phone]);
  const hours = first(props, 'opening_hours');
  if (hours) rows.push(['Opening hours', openingHours(hours)]);
  return rows;
}

/** The region a flood/access layer or feature names, from the first segment after a `flood_`/`access_` prefix. */
function regionName(id: string | null): string | null {
  if (!id) return null;
  const stripped = id.toLowerCase().replace(/^flood_/, '').replace(/^access_/, '');
  const key = stripped.split('_')[0];
  return REGIONS[key] ?? null;
}

function describeHealth(props: FeatureProperties): Described {
  const amenity = first(props, 'amenity', 'healthcare');
  const amenityLower = amenity?.toLowerCase();
  const type = amenity ? HEALTH_TYPES[amenityLower as string] ?? humanise(amenity) : 'Health service';
  const emergency = first(props, 'emergency');
  const emergencyYes = emergency?.toLowerCase() === 'yes';

  let kind: PlaceKind | null = null;
  if (amenityLower === 'hospital' || emergencyYes) kind = 'hospital';
  else if (amenityLower === 'pharmacy') kind = 'pharmacy';
  else if (amenityLower === 'doctors') kind = 'gp';
  else if (amenityLower === 'clinic') kind = 'clinic';

  const rows: [string, string][] = [['Type', type]];
  if (emergency) rows.push(['Emergency department', yesNo(emergency)]);
  const dispensing = first(props, 'dispensing');
  if (dispensing) rows.push(['Dispenses prescriptions', yesNo(dispensing)]);
  rows.push(...commonRows(props));
  const beds = first(props, 'beds');
  if (beds) rows.push(['Beds', beds]);
  const wheelchair = first(props, 'wheelchair');
  if (wheelchair) rows.push(['Wheelchair access', yesNo(wheelchair)]);
  const website = first(props, 'website');
  if (website) rows.push(['Website', website]);

  return { title: first(props, 'name') ?? type, typeLine: emergency && emergencyYes ? `${type} · emergency department` : type, kind, rows };
}

function describeFuel(props: FeatureProperties): Described {
  const brand = first(props, 'brand');
  const rows: [string, string][] = [['Type', 'Fuel station']];
  if (brand) rows.push(['Brand', brand]);
  const diesel = first(props, 'fuel:diesel');
  if (diesel) rows.push(['Diesel', yesNo(diesel)]);
  const lpg = first(props, 'fuel:lpg');
  if (lpg) rows.push(['LPG', yesNo(lpg)]);
  const electric = first(props, 'fuel:electricity');
  if (electric) rows.push(['Electric charging', yesNo(electric)]);
  const shop = first(props, 'shop');
  if (shop) rows.push(['Shop', humanise(shop)]);
  rows.push(...commonRows(props).filter(([label, value]) => !(label === 'Run by' && value === brand)));
  return { title: first(props, 'name') ?? 'Fuel station', typeLine: brand ? `Fuel station · ${brand}` : 'Fuel station', kind: 'fuel', rows };
}

function describeWater(props: FeatureProperties): Described {
  const manMade = first(props, 'man_made')?.toLowerCase();
  const waterVal = first(props, 'water')?.toLowerCase();
  const landuse = first(props, 'landuse')?.toLowerCase();
  const natural = first(props, 'natural')?.toLowerCase();
  let type: string;
  let kind: PlaceKind | null;
  if (manMade === 'water_works') { type = 'Water treatment works'; kind = 'water-works'; }
  else if (manMade === 'reservoir_covered' || manMade === 'storage_tank') { type = 'Covered reservoir or water tank'; kind = 'reservoir'; }
  else if (waterVal === 'reservoir' || landuse === 'reservoir') { type = 'Reservoir'; kind = 'reservoir'; }
  else if (natural === 'spring') { type = 'Spring'; kind = 'spring'; }
  else if (manMade) { type = humanise(manMade); kind = null; }
  else { type = 'Water body'; kind = null; }

  const rows: [string, string][] = [['Type', type], ...commonRows(props)];
  const description = first(props, 'description');
  if (description) rows.push(['Note', description]);
  return { title: first(props, 'name') ?? type, typeLine: type, kind, rows };
}

function describeRail(props: FeatureProperties): Described {
  const station = first(props, 'station')?.toLowerCase();
  const type = station === 'subway' ? 'Underground station' : station === 'light_rail' ? 'Light rail station' : station === 'tram' ? 'Tram stop'
    : first(props, 'railway')?.toLowerCase() === 'halt' ? 'Railway halt' : 'Railway station';
  const rows: [string, string][] = [['Type', type]];
  const network = first(props, 'network');
  if (network) rows.push(['Network', network]);
  const operator = first(props, 'operator');
  if (operator) rows.push(['Train operator', operator]);
  const platforms = first(props, 'platforms');
  if (platforms) rows.push(['Platforms', platforms]);
  const wheelchair = first(props, 'wheelchair');
  if (wheelchair) rows.push(['Wheelchair access', yesNo(wheelchair)]);
  rows.push(...commonRows({ ...props, operator: null }));
  return { title: first(props, 'name') ?? type, typeLine: operator ? `${type} · ${operator}` : type, kind: 'rail-station', rows };
}

function describeNuclear(props: FeatureProperties): Described {
  const rawType = first(props, 'type');
  const type = rawType ? NUCLEAR_TYPES[rawType.toLowerCase()] ?? `Nuclear site (${humanise(rawType).toLowerCase()})` : 'Nuclear site';
  const rows: [string, string][] = [['Type', type]];
  const status = first(props, 'status');
  const statusLabel = status ? NUCLEAR_STATUS[status.toLowerCase()] ?? humanise(status) : null;
  if (statusLabel) rows.push(['Status', statusLabel]);
  const note = first(props, 'note');
  if (note) rows.push(['Detail', note]);
  rows.push(...commonRows(props));
  return { title: first(props, 'name') ?? type, typeLine: statusLabel ? `${type} · ${statusLabel}` : type, kind: 'nuclear', rows };
}

function describeChemical(props: FeatureProperties): Described {
  const industrial = first(props, 'industrial');
  const type = industrial ? INDUSTRIAL_TYPES[industrial.toLowerCase()] ?? humanise(industrial) : 'Chemical (COMAH) site';
  const rows: [string, string][] = [['Type', type], ...commonRows(props)];
  const hazmat = first(props, 'hazmat');
  if (hazmat) rows.push(['Hazardous materials', yesNo(hazmat)]);
  const description = first(props, 'description');
  if (description) rows.push(['Note', description]);
  if (first(props, 'source')?.toLowerCase() === 'hand-authored') rows.push(['Listed as', 'Major hazard site from the Operation SOS list']);
  return { title: first(props, 'name') ?? type, typeLine: type, kind: 'chemical', rows };
}

function describeAirport(props: FeatureProperties): Described {
  const aeroway = first(props, 'aeroway')?.toLowerCase();
  const military = first(props, 'military')?.toLowerCase();
  const aerodromeType = first(props, 'aerodrome:type', 'aerodrome')?.toLowerCase();
  let type: string;
  if (aeroway === 'aerodrome' && military) type = MILITARY_TYPES[military] ?? 'Military airfield';
  else if (aeroway === 'aerodrome' && aerodromeType === 'military') type = 'Military airfield';
  else if (aeroway === 'aerodrome') type = (aerodromeType && AERODROME_TYPES[aerodromeType]) ?? 'Airport or airfield';
  else if (aeroway === 'heliport' || aeroway === 'helipad') type = 'Heliport';
  else type = aeroway ? humanise(aeroway) : 'Airport or airfield';

  const rows: [string, string][] = [['Type', type]];
  const icao = first(props, 'icao');
  const iata = first(props, 'iata');
  if (icao || iata) rows.push(['Code', [iata, icao].filter(Boolean).join(' / ')]);
  rows.push(...commonRows(props));
  return { title: first(props, 'name') ?? type, typeLine: type, kind: 'airport', rows };
}

function describeMilitary(props: FeatureProperties): Described {
  const military = first(props, 'military')?.toLowerCase();
  let type: string;
  if (military) type = MILITARY_TYPES[military] ?? (military === 'yes' ? 'Military land' : `Military land (${humanise(military).toLowerCase()})`);
  else type = 'Military land';

  const rows: [string, string][] = [['Type', type], ...commonRows(props)];
  const access = first(props, 'access');
  if (access) rows.push(['Access', ACCESS_VALUES[access.toLowerCase()] ?? humanise(access)]);
  const description = first(props, 'description');
  if (description) rows.push(['Note', description]);
  return { title: first(props, 'name') ?? type, typeLine: type, kind: 'military', rows };
}

function describeFootpath(props: FeatureProperties): Described {
  const designation = first(props, 'designation')?.toLowerCase();
  const highway = first(props, 'highway')?.toLowerCase();
  const known = designation && designation !== 'none' ? DESIGNATIONS[designation] : undefined;
  const type = known?.title ?? (designation && designation !== 'none' ? humanise(designation) : highway ? HIGHWAY_TYPES[highway] ?? humanise(highway) : 'Path');
  const rows: [string, string][] = [['Type', type]];
  if (known) rows.push(['Who may use it', known.users]);
  else if (designation && designation !== 'none') rows.push(['Right of way', humanise(designation)]);
  const ref = first(props, 'prow_ref');
  if (ref) rows.push(['Right of way number', ref]);
  const foot = first(props, 'foot');
  const access = first(props, 'access');
  const accessValue = foot ?? access;
  if (accessValue) rows.push([foot ? 'On foot' : 'Access', ACCESS_VALUES[accessValue.toLowerCase()] ?? humanise(accessValue)]);
  const surface = first(props, 'surface');
  if (surface) rows.push(['Surface', humanise(surface)]);
  const sac = first(props, 'sac_scale');
  if (sac) rows.push(['Difficulty', SAC_SCALE[sac.toLowerCase()] ?? humanise(sac)]);
  const visibility = first(props, 'trail_visibility');
  if (visibility) rows.push(['Visibility', TRAIL_VISIBILITY[visibility.toLowerCase()] ?? humanise(visibility)]);
  return { title: first(props, 'name') ?? type, typeLine: type, kind: 'footpath', rows };
}

function accessDesignation(value: string | null): { title: string; meaning: string } {
  const v = (value ?? '').replace(/_/g, ' ').toLowerCase();
  if (v.includes('common')) return { title: 'Registered common land', meaning: 'Open to walk on under the Countryside and Rights of Way Act 2000' };
  if (v.includes('open country') || v.includes('mountain') || v.includes('moor') || v.includes('heath') || v.includes('down')) {
    return { title: 'Open country (CROW Act)', meaning: 'Mountain, moor, heath or down you may walk on freely under the Countryside and Rights of Way Act 2000' };
  }
  if (v.includes('section 16') || v.includes('dedicated')) return { title: 'Dedicated access land', meaning: 'Land the owner has dedicated for public access under section 16 of the CROW Act' };
  if (v.includes('section 15') || v.includes('coastal') || v.includes('coast')) return { title: 'Coastal margin or section 15 land', meaning: 'Land with a right of access on foot under the CROW Act' };
  if (v.includes('forest')) return { title: 'Dedicated woodland', meaning: 'Woodland the owner has opened for public access on foot' };
  return { title: value ? humanise(value) : 'Open access land', meaning: 'Land you may walk on freely under the Countryside and Rights of Way Act 2000' };
}

function describeAccessLand(props: FeatureProperties, sourceLayer?: string): Described {
  const designation = accessDesignation(first(props, 'Descrip', 'descrip', 'DESCRIP', 'Description', 'type', 'TYPE', 'designation', 'category'));
  const rows: [string, string][] = [['Designation', designation.title], ['What it means', designation.meaning]];
  const region = regionName(first(props, 'region') ?? sourceLayer ?? null);
  if (region) rows.push(['Region', region]);
  const name = first(props, 'name', 'Name', 'NAME', 'site_name');
  return { title: name ?? 'Open access land', typeLine: designation.title, kind: 'access-land', rows };
}

/** The flood zone ("1", "2" or "3") a feature's properties name, whatever the source called the field. */
export function floodZoneOf(props: FeatureProperties): string | null {
  // `risk` is Natural Resources Wales's field ("Flood Zone 3"); the rest are the Environment Agency's and older exports'.
  const raw = first(props, 'zone', 'Zone', 'ZONE', 'flood_zone', 'FLOOD_ZONE', 'fz', 'risk', 'layer', 'type', 'TYPE');
  if (!raw) return null;
  const m = /([123])\b/.exec(raw);
  return m ? m[1] : null;
}

/** The `z2`/`z3`/`river`/`coastal` tag off the end of a `flood_<region>[_<tag>]` tippecanoe layer name, if any. */
function floodLayerTag(sourceLayer?: string): string | null {
  if (!sourceLayer) return null;
  const m = /^flood_[a-z]+_(z2|z3|river|coastal)$/i.exec(sourceLayer);
  return m ? m[1].toLowerCase() : null;
}

function describeFloodZone(props: FeatureProperties, sourceLayer?: string): Described {
  const tag = floodLayerTag(sourceLayer);
  const region = regionName(sourceLayer ?? first(props, 'region'));
  const rows: [string, string][] = [];
  let title: string;
  if (tag === 'z2' || tag === 'z3') {
    const zone = tag === 'z2' ? '2' : '3';
    const known = FLOOD_ZONES[zone];
    rows.push(['Flood zone', zone], ['Chance of flooding', known.chance]);
    title = known.title;
  } else if (tag === 'river') {
    title = 'River flood risk area';
    rows.push(['Chance of flooding', (region && RIVER_CHANCE[region]) ?? 'River flooding area']);
  } else if (tag === 'coastal') {
    title = 'Coastal flood risk area';
    rows.push(['Chance of flooding', (region && COASTAL_CHANCE[region]) ?? 'Coastal flooding area']);
  } else {
    const zone = floodZoneOf(props);
    const known = zone ? FLOOD_ZONES[zone] : undefined;
    if (known) {
      rows.push(['Flood zone', zone as string], ['Chance of flooding', known.chance]);
      title = known.title;
    } else {
      const kind = first(props, 'type', 'TYPE', 'flood_type', 'category', 'source_type');
      rows.push(['Chance of flooding', kind ? `${humanise(kind)} flooding area` : 'Area shown on the official flood map as at risk of flooding']);
      title = 'Flood risk area';
    }
  }
  if (region) rows.push(['Region', region]);
  if (region === 'England' || region === 'Wales') rows.push(['Definition', 'Flood Map for Planning zones: undefended river and sea flooding, ignoring flood defences']);
  return { title, typeLine: title, kind: 'flood-zone', rows };
}

/**
 * Turn an overlay feature's properties into what the tooltip and place card show: never raw OSM keys, always a
 * title, a type line, a place kind (for the card's icon and layout), the overlay name and rows of plain English.
 */
export function describeFeature(overlayId: string, properties: FeatureProperties | null | undefined, opts: DescribeOptions = {}): FeatureDescription {
  const props: FeatureProperties = properties ?? {};
  const overlay = opts.overlayTitle ?? OVERLAY_TITLES[overlayId] ?? humanise(overlayId);
  let out: Described;
  switch (overlayId) {
    case 'health': out = describeHealth(props); break;
    case 'fuel': out = describeFuel(props); break;
    case 'water': out = describeWater(props); break;
    case 'rail': out = describeRail(props); break;
    case 'nuclear-sites': out = describeNuclear(props); break;
    case 'chemical-sites': out = describeChemical(props); break;
    case 'airports': out = describeAirport(props); break;
    case 'military': out = describeMilitary(props); break;
    case 'footpaths': out = describeFootpath(props); break;
    case 'access-land': out = describeAccessLand(props, opts.sourceLayer); break;
    case 'flood-zones': out = describeFloodZone(props, opts.sourceLayer); break;
    default: out = { title: first(props, 'name', 'title') ?? overlay, typeLine: overlay, kind: null, rows: commonRows(props) };
  }
  return { title: out.title, overlay, typeLine: out.typeLine, kind: out.kind, rows: out.rows };
}
