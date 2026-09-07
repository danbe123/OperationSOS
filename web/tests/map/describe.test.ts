import { describe, it, expect, vi } from 'vitest';
import { describeFeature, humanise, openingHours, OVERLAY_TITLES } from '../../src/map/describe';

vi.mock('maplibre-gl', () => ({ default: { addProtocol: vi.fn() }, addProtocol: vi.fn() }));
vi.mock('pmtiles', () => ({ Protocol: class { tile = () => undefined; }, EtagMismatch: class extends Error {} }));

// The overlay ids in manifest/overlays.json (the source of truth lives outside web/; this list is asserted against it by hand).
const MANIFEST_IDS = ['footpaths', 'access-land', 'flood-zones', 'health', 'fuel', 'water', 'rail', 'nuclear-sites', 'chemical-sites', 'airports', 'military'];

const RAW_KEY = /^(amenity|operator|opening_hours|prow_ref|sac_scale|trail_visibility|man_made|aeroway|railway|industrial|designation|highway|Descrip|addr:)/;

describe('describeFeature', () => {
  it('knows every overlay in the manifest and falls back to a generic title with no properties', () => {
    expect(Object.keys(OVERLAY_TITLES).sort()).toEqual([...MANIFEST_IDS].sort());
    const generic: Record<string, string> = {
      footpaths: 'Path', 'access-land': 'Open access land', 'flood-zones': 'Flood risk area', health: 'Health service', fuel: 'Fuel station',
      water: 'Water body', rail: 'Railway station', 'nuclear-sites': 'Nuclear site', 'chemical-sites': 'Chemical (COMAH) site',
      airports: 'Airport or airfield', military: 'Military land',
    };
    for (const id of MANIFEST_IDS) {
      const d = describeFeature(id, {});
      expect(d.title, id).toBe(generic[id]);
      expect(d.overlay, id).toBe(OVERLAY_TITLES[id]);
      for (const [label, value] of d.rows) {
        expect(label, id).not.toMatch(RAW_KEY);
        expect(value, id).not.toMatch(/_/);
      }
    }
    expect(describeFeature('health', null).title).toBe('Health service');
    expect(describeFeature('health', undefined).overlay).toBe('Hospitals, pharmacies and GP surgeries');
  });

  it('airports: type line from the aerodrome type, codes and operator as rows, kind airport', () => {
    const d = describeFeature('airports', { name: 'Southampton Airport', aeroway: 'aerodrome', 'aerodrome:type': 'international', iata: 'SOU', icao: 'EGHI', operator: 'AGS Airports' });
    expect(d.title).toBe('Southampton Airport');
    expect(d.typeLine).toBe('International airport');
    expect(d.kind).toBe('airport');
    expect(d.rows).toEqual([['Type', 'International airport'], ['Code', 'SOU / EGHI'], ['Run by', 'AGS Airports']]);
    expect(describeFeature('airports', { aeroway: 'aerodrome', military: 'airfield', name: 'RAF Brize Norton' }).typeLine).toBe('Military airfield');
    expect(describeFeature('airports', { aeroway: 'aerodrome' }).title).toBe('Airport or airfield');
  });

  it('military: barracks, naval bases and danger areas, kind military', () => {
    expect(describeFeature('military', { military: 'barracks', name: 'Marchwood', operator: 'British Army', access: 'no' })).toMatchObject({
      title: 'Marchwood', typeLine: 'Barracks', kind: 'military', rows: [['Type', 'Barracks'], ['Run by', 'British Army'], ['Access', 'No public access']],
    });
    expect(describeFeature('military', { military: 'naval_base' }).typeLine).toBe('Naval base');
    expect(describeFeature('military', { military: 'danger_area' }).typeLine).toBe('Military danger area');
    expect(describeFeature('military', { landuse: 'military' }).typeLine).toBe('Military land');
    expect(describeFeature('military', { military: 'radar_station' }).typeLine).toBe('Military land (radar station)');
  });

  it('health: A&E, beds, dispensing, wheelchair and website; kinds per amenity', () => {
    const d = describeFeature('health', { name: 'Southampton General Hospital', amenity: 'hospital', emergency: 'yes', beds: '1200', wheelchair: 'yes', website: 'https://uhs.nhs.uk', operator: 'UHS NHS FT' });
    expect(d.typeLine).toBe('Hospital · emergency department');
    expect(d.kind).toBe('hospital');
    expect(d.rows).toEqual([['Type', 'Hospital'], ['Emergency department', 'Yes'], ['Run by', 'UHS NHS FT'], ['Beds', '1200'], ['Wheelchair access', 'Yes'], ['Website', 'https://uhs.nhs.uk']]);
    expect(describeFeature('health', { amenity: 'pharmacy', dispensing: 'yes' })).toMatchObject({ kind: 'pharmacy', rows: [['Type', 'Pharmacy'], ['Dispenses prescriptions', 'Yes']] });
    expect(describeFeature('health', { amenity: 'doctors' }).kind).toBe('gp');
    expect(describeFeature('health', { amenity: 'clinic' }).kind).toBe('clinic');
    expect(describeFeature('health', { healthcare: 'hospital', emergency: 'yes' }).kind).toBe('hospital');
    expect(describeFeature('health', { amenity: 'pharmacy', phone: null }).title).toBe('Pharmacy');
    expect(describeFeature('health', { name: 'Totton Health Centre', amenity: 'doctors' }).rows).toEqual([['Type', 'GP surgery']]);
  });

  it('fuel: brand in the type line, what it sells and whether it has a shop', () => {
    const d = describeFeature('fuel', { name: 'Tesco Bursledon', brand: 'Tesco', 'fuel:diesel': 'yes', 'fuel:lpg': 'no', 'fuel:electricity': 'yes', shop: 'convenience', opening_hours: '24/7' });
    expect(d.typeLine).toBe('Fuel station · Tesco');
    expect(d.kind).toBe('fuel');
    expect(d.rows).toEqual([['Type', 'Fuel station'], ['Brand', 'Tesco'], ['Diesel', 'Yes'], ['LPG', 'No'], ['Electric charging', 'Yes'], ['Shop', 'Convenience'], ['Opening hours', 'Open 24 hours a day, every day']]);
    expect(describeFeature('fuel', { name: null, brand: null }).title).toBe('Fuel station');
  });

  it('water: works, reservoirs and springs are three kinds', () => {
    expect(describeFeature('water', { man_made: 'water_works', operator: 'Southern Water' })).toMatchObject({ kind: 'water-works', typeLine: 'Water treatment works', rows: [['Type', 'Water treatment works'], ['Run by', 'Southern Water']] });
    expect(describeFeature('water', { water: 'reservoir', name: 'Bewl Water' })).toMatchObject({ kind: 'reservoir', typeLine: 'Reservoir' });
    expect(describeFeature('water', { natural: 'spring', description: 'Chalk spring' })).toMatchObject({ kind: 'spring', typeLine: 'Spring', rows: [['Type', 'Spring'], ['Note', 'Chalk spring']] });
    expect(describeFeature('water', { landuse: 'reservoir' }).title).toBe('Reservoir');
  });

  it('rail: operator in the type line, platforms and step-free access', () => {
    const d = describeFeature('rail', { name: 'Eastleigh', railway: 'station', operator: 'South Western Railway', network: 'National Rail', platforms: '4', wheelchair: 'limited' });
    expect(d.typeLine).toBe('Railway station · South Western Railway');
    expect(d.kind).toBe('rail-station');
    expect(d.rows).toEqual([['Type', 'Railway station'], ['Network', 'National Rail'], ['Train operator', 'South Western Railway'], ['Platforms', '4'], ['Wheelchair access', 'Limited']]);
    expect(describeFeature('rail', { name: 'Rio Grande Train Station', network: null, operator: null, railway: 'station' }).rows).toEqual([['Type', 'Railway station']]);
    expect(describeFeature('rail', { railway: 'station', station: 'subway' }).title).toBe('Underground station');
  });

  it('nuclear sites: type, status and the note', () => {
    expect(describeFeature('nuclear-sites', { name: 'Heysham 1', type: 'power-station', status: 'operating', note: 'AGR, EDF; two reactors, scheduled to close 2027' })).toMatchObject({
      title: 'Heysham 1', rows: [['Type', 'Nuclear power station'], ['Status', 'Operating'], ['Detail', 'AGR, EDF; two reactors, scheduled to close 2027']],
    });
    expect(describeFeature('nuclear-sites', { name: 'Sellafield', type: 'reprocessing', status: 'decommissioning' }).rows).toEqual([['Type', 'Nuclear reprocessing plant'], ['Status', 'Being decommissioned']]);
    expect(describeFeature('nuclear-sites', { type: 'naval', status: 'defuelling' }).rows).toEqual([['Type', 'Naval nuclear base'], ['Status', 'Closed, fuel being removed']]);
    expect(describeFeature('nuclear-sites', { name: 'AWE Aldermaston', type: 'weapons' }).rows[0]).toEqual(['Type', 'Atomic weapons establishment']);
    expect(describeFeature('nuclear-sites', { type: 'fuel' }).title).toBe('Nuclear fuel plant');
    expect(describeFeature('nuclear-sites', { type: 'research', status: 'construction' }).rows).toEqual([['Type', 'Nuclear research site'], ['Status', 'Under construction']]);
  });

  it('chemical sites: refinery, chemical works and the hand-authored marker', () => {
    expect(describeFeature('chemical-sites', { name: 'Fawley refinery and petrochemicals', industrial: 'refinery', source: 'hand-authored' })).toMatchObject({
      title: 'Fawley refinery and petrochemicals',
      rows: [['Type', 'Oil refinery'], ['Listed as', 'Major hazard site from the Operation SOS list']],
    });
    expect(describeFeature('chemical-sites', { industrial: 'chemical', operator: 'INEOS' }).rows).toEqual([['Type', 'Chemical works'], ['Run by', 'INEOS']]);
    expect(describeFeature('chemical-sites', { industrial: 'oil' }).title).toBe('Oil terminal or depot');
  });

  it('footpaths: rights of way by designation, other paths by highway type, with access, surface and difficulty', () => {
    expect(describeFeature('footpaths', { highway: 'footway', designation: 'public_footpath', prow_ref: 'Copythorne FP 14', foot: 'designated', surface: 'grass' })).toMatchObject({
      title: 'Public footpath',
      rows: [['Type', 'Public footpath'], ['Who may use it', 'On foot'], ['Right of way number', 'Copythorne FP 14'], ['On foot', 'Signed for this use'], ['Surface', 'Grass']],
    });
    expect(describeFeature('footpaths', { highway: 'bridleway', designation: 'public_bridleway', name: 'Denny Lodge BR 1' }).rows).toEqual([['Type', 'Public bridleway'], ['Who may use it', 'On foot, on horseback and by bicycle']]);
    expect(describeFeature('footpaths', { designation: 'restricted_byway' }).rows[1][1]).toContain('no motor vehicles');
    expect(describeFeature('footpaths', { designation: 'byway_open_to_all_traffic' }).title).toBe('Byway open to all traffic');
    expect(describeFeature('footpaths', { designation: 'core_path' }).title).toBe('Scottish core path');
    expect(describeFeature('footpaths', { highway: 'path', designation: 'none', access: 'private', surface: 'compacted', sac_scale: 'mountain_hiking', trail_visibility: 'bad' })).toMatchObject({
      title: 'Path',
      rows: [['Type', 'Path'], ['Access', 'Private, no public access'], ['Surface', 'Compacted'], ['Difficulty', 'Mountain walking, some steep ground'], ['Visibility', 'Path hard to follow']],
    });
    expect(describeFeature('footpaths', { highway: 'track', name: 'Beechdale Walk', access: 'permissive' }).title).toBe('Beechdale Walk');
    expect(describeFeature('footpaths', { highway: 'cycleway' }).title).toBe('Cycle path');
    expect(describeFeature('footpaths', { highway: 'steps' }).title).toBe('Steps');
  });

  it('access land: CROW open country and common land with the region', () => {
    expect(describeFeature('access-land', { Descrip: 'Open Country', source: 'fixture sample', region: 'england' })).toMatchObject({
      title: 'Open access land',
      rows: [['Designation', 'Open country (CROW Act)'], ['What it means', 'Mountain, moor, heath or down you may walk on freely under the Countryside and Rights of Way Act 2000'], ['Region', 'England']],
    });
    expect(describeFeature('access-land', { Descrip: 'Registered Common Land', region: 'wales' }).rows).toEqual([
      ['Designation', 'Registered common land'], ['What it means', 'Open to walk on under the Countryside and Rights of Way Act 2000'], ['Region', 'Wales'],
    ]);
    expect(describeFeature('access-land', { Descrip: 'Section 16 Dedicated Land' }).rows[0]).toEqual(['Designation', 'Dedicated access land']);
    expect(describeFeature('access-land', { name: 'Dartmoor' }, { sourceLayer: 'access-land' }).title).toBe('Dartmoor');
  });

  it('access land from a tagged Welsh source reads its designation', () => {
    expect(describeFeature('access-land', { region: 'wales', designation: 'open_country' })).toMatchObject({ kind: 'access-land', rows: expect.arrayContaining([['Designation', 'Open country (CROW Act)'], ['Region', 'Wales']]) });
    expect(describeFeature('access-land', { region: 'wales', designation: 'common_land' }).rows[0]).toEqual(['Designation', 'Registered common land']);
  });

  it('flood zones: zone 2 and 3 with what they mean and the region from the vector layer', () => {
    expect(describeFeature('flood-zones', { zone: '3', source: 'fixture sample' }, { sourceLayer: 'flood_england' })).toMatchObject({
      title: 'Flood zone 3',
      rows: [
        ['Flood zone', '3'],
        ['Chance of flooding', 'High: a 1 in 100 or greater chance of river flooding, or 1 in 200 or greater of sea flooding, in any year'],
        ['Region', 'England'],
        ['Definition', 'Flood Map for Planning zones: undefended river and sea flooding, ignoring flood defences'],
      ],
    });
    const two = describeFeature('flood-zones', { zone: '2' }, { sourceLayer: 'flood_wales' });
    expect(two.title).toBe('Flood zone 2');
    expect(two.rows[1][1]).toMatch(/^Medium/);
    expect(two.rows[2]).toEqual(['Region', 'Wales']);
    expect(describeFeature('flood-zones', { FLOOD_ZONE: 'Flood Zone 3' }).title).toBe('Flood zone 3');
    const sepa = describeFeature('flood-zones', { type: 'river' }, { sourceLayer: 'flood_scotland' });
    expect(sepa.title).toBe('Flood risk area');
    expect(sepa.rows).toEqual([['Chance of flooding', 'River flooding area'], ['Region', 'Scotland']]);
    expect(describeFeature('flood-zones', {}, { sourceLayer: 'flood_ni' }).rows).toEqual([['Chance of flooding', 'Area shown on the official flood map as at risk of flooding'], ['Region', 'Northern Ireland']]);
  });

  it('flood layers carry the region and the zone or the extent kind in their name', () => {
    expect(describeFeature('flood-zones', {}, { sourceLayer: 'flood_wales_z3' })).toMatchObject({ title: 'Flood zone 3', kind: 'flood-zone', rows: expect.arrayContaining([['Flood zone', '3'], ['Region', 'Wales']]) });
    expect(describeFeature('flood-zones', {}, { sourceLayer: 'flood_scotland_river' })).toMatchObject({ title: 'River flood risk area', rows: expect.arrayContaining([['Chance of flooding', 'Medium: a 1 in 200 or greater chance of river flooding in any year (SEPA)'], ['Region', 'Scotland']]) });
    expect(describeFeature('flood-zones', {}, { sourceLayer: 'flood_roi_coastal' })).toMatchObject({ title: 'Coastal flood risk area', rows: expect.arrayContaining([['Chance of flooding', 'A 1 in 200 or greater chance of sea flooding in any year (OPW)'], ['Region', 'Republic of Ireland']]) });
    expect(describeFeature('flood-zones', { layer: 'Flood Zone 2' }, { sourceLayer: 'flood_england' }).title).toBe('Flood zone 2');
  });

  it('every overlay maps to a kind; an unknown overlay has none', () => {
    expect(describeFeature('nuclear-sites', { type: 'power-station', status: 'operating' })).toMatchObject({ kind: 'nuclear', typeLine: 'Nuclear power station · Operating' });
    expect(describeFeature('chemical-sites', { industrial: 'refinery' }).kind).toBe('chemical');
    expect(describeFeature('footpaths', { designation: 'public_footpath' })).toMatchObject({ kind: 'footpath', typeLine: 'Public footpath' });
    expect(describeFeature('whatever', {}).kind).toBeNull();
  });

  it('an unknown overlay still gets a name, a humanised overlay title and the shared rows', () => {
    expect(describeFeature('shelters', { name: 'Village hall', phone: '01onalone' })).toMatchObject({ title: 'Village hall', overlay: 'Shelters', rows: [['Phone', '01onalone']] });
    expect(describeFeature('rest-centres', {}).title).toBe('Rest centres');
  });
});

describe('helpers', () => {
  it('humanise turns OSM values into words', () => {
    expect(humanise('water_works')).toBe('Water works');
    expect(humanise('public-footpath')).toBe('Public footpath');
    expect(humanise('')).toBe('');
  });
  it('openingHours spells out day codes', () => {
    expect(openingHours('Mo-Fr 09:00-17:30; Sa 09:00-13:00; Su off')).toBe('Mon to Fri 09:00-17:30; Sat 09:00-13:00; Sun closed');
    expect(openingHours('PH off')).toBe('bank holidays closed');
  });
});
