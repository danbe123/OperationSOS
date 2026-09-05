import { describe, it, expect, vi } from 'vitest';
import { describeFeature, humanise, openingHours, OVERLAY_TITLES } from '../../src/map/describe';

vi.mock('maplibre-gl', () => ({ default: { addProtocol: vi.fn() }, addProtocol: vi.fn() }));
vi.mock('pmtiles', () => ({ Protocol: class { tile = () => undefined; }, EtagMismatch: class extends Error {} }));

// The overlay ids in manifest/overlays.json (the source of truth lives outside web/; this list is asserted against it by hand).
const MANIFEST_IDS = ['footpaths', 'access-land', 'flood-zones', 'health', 'fuel', 'water', 'rail', 'nuclear-sites', 'chemical-sites', 'airports-military'];

const RAW_KEY = /^(amenity|operator|opening_hours|prow_ref|sac_scale|trail_visibility|man_made|aeroway|railway|industrial|designation|highway|Descrip|addr:)/;

describe('describeFeature', () => {
  it('knows every overlay in the manifest and falls back to a generic title with no properties', () => {
    expect(Object.keys(OVERLAY_TITLES).sort()).toEqual([...MANIFEST_IDS].sort());
    const generic: Record<string, string> = {
      footpaths: 'Path', 'access-land': 'Open access land', 'flood-zones': 'Flood risk area', health: 'Health service', fuel: 'Fuel station',
      water: 'Water body', rail: 'Railway station', 'nuclear-sites': 'Nuclear site', 'chemical-sites': 'Chemical (COMAH) site', 'airports-military': 'Airport or military land',
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

  it('health: hospital, pharmacy and GP surgery with phone, hours, A&E and address', () => {
    const d = describeFeature('health', { name: 'Southampton General Hospital', amenity: 'hospital', phone: '+44 23 8077 7222', opening_hours: '24/7', emergency: 'yes', operator: 'University Hospital Southampton NHS Foundation Trust', 'addr:street': 'Tremona Road', 'addr:city': 'Southampton', 'addr:postcode': 'SO16 6YD' });
    expect(d.title).toBe('Southampton General Hospital');
    expect(d.overlay).toBe('Hospitals, pharmacies and GP surgeries');
    expect(d.rows).toEqual([
      ['Type', 'Hospital'],
      ['Emergency department', 'Yes'],
      ['Run by', 'University Hospital Southampton NHS Foundation Trust'],
      ['Address', 'Tremona Road, Southampton, SO16 6YD'],
      ['Phone', '+44 23 8077 7222'],
      ['Opening hours', 'Open 24 hours a day, every day'],
    ]);
    expect(describeFeature('health', { amenity: 'pharmacy', phone: null }).title).toBe('Pharmacy');
    expect(describeFeature('health', { name: 'Totton Health Centre', amenity: 'doctors' }).rows).toEqual([['Type', 'GP surgery']]);
  });

  it('fuel: station with operator, hours and fuel types; config title wins when given', () => {
    const d = describeFeature('fuel', { amenity: 'fuel', name: 'Morrisons', operator: 'WM Morrison Supermarkets Ltd', opening_hours: 'Mo-Sa 06:00-21:00; Su 06:00-22:00', 'fuel:diesel': 'yes', 'fuel:octane_95': 'yes', 'fuel:lpg': 'no', landuse: 'retail' }, { overlayTitle: 'Petrol stations' });
    expect(d.title).toBe('Morrisons');
    expect(d.overlay).toBe('Petrol stations');
    expect(d.rows).toEqual([
      ['Type', 'Fuel station'],
      ['Fuel sold', 'diesel, petrol (95)'],
      ['Run by', 'WM Morrison Supermarkets Ltd'],
      ['Opening hours', 'Mon to Sat 06:00-21:00; Sun 06:00-22:00'],
    ]);
    expect(describeFeature('fuel', { amenity: 'fuel', name: null, operator: null }).title).toBe('Fuel station');
  });

  it('water: reservoirs and treatment works', () => {
    expect(describeFeature('water', { name: 'Little Testwood Lake', natural: 'water', water: 'reservoir', operator: 'Southern Water' })).toEqual({
      title: 'Little Testwood Lake', overlay: 'Reservoirs and water works', rows: [['Type', 'Reservoir'], ['Run by', 'Southern Water']],
    });
    expect(describeFeature('water', { natural: 'water', water: 'reservoir' }).title).toBe('Reservoir');
    expect(describeFeature('water', { man_made: 'water_works', name: 'Testwood Water Supply Works' }).rows[0]).toEqual(['Type', 'Water treatment works']);
    expect(describeFeature('water', { landuse: 'reservoir' }).title).toBe('Reservoir');
  });

  it('rail: station with network and train operator', () => {
    expect(describeFeature('rail', { name: 'Totton', network: 'National Rail', operator: 'South Western Railway', railway: 'station' })).toEqual({
      title: 'Totton', overlay: 'Railway stations', rows: [['Type', 'Railway station'], ['Network', 'National Rail'], ['Train operator', 'South Western Railway']],
    });
    expect(describeFeature('rail', { name: 'Rio Grande Train Station', network: null, operator: null, railway: 'station' }).rows).toEqual([['Type', 'Railway station']]);
    expect(describeFeature('rail', { railway: 'station', station: 'subway' }).title).toBe('Underground station');
  });

  it('nuclear sites: type, status and the note', () => {
    expect(describeFeature('nuclear-sites', { name: 'Heysham 1', type: 'power-station', status: 'operating', note: 'AGR, EDF; two reactors, scheduled to close 2027' })).toEqual({
      title: 'Heysham 1', overlay: 'Nuclear sites', rows: [['Type', 'Nuclear power station'], ['Status', 'Operating'], ['Detail', 'AGR, EDF; two reactors, scheduled to close 2027']],
    });
    expect(describeFeature('nuclear-sites', { name: 'Sellafield', type: 'reprocessing', status: 'decommissioning' }).rows).toEqual([['Type', 'Nuclear reprocessing plant'], ['Status', 'Being decommissioned']]);
    expect(describeFeature('nuclear-sites', { type: 'naval', status: 'defuelling' }).rows).toEqual([['Type', 'Naval nuclear base'], ['Status', 'Closed, fuel being removed']]);
    expect(describeFeature('nuclear-sites', { name: 'AWE Aldermaston', type: 'weapons' }).rows[0]).toEqual(['Type', 'Atomic weapons establishment']);
    expect(describeFeature('nuclear-sites', { type: 'fuel' }).title).toBe('Nuclear fuel plant');
    expect(describeFeature('nuclear-sites', { type: 'research', status: 'construction' }).rows).toEqual([['Type', 'Nuclear research site'], ['Status', 'Under construction']]);
  });

  it('chemical sites: refinery, chemical works and the hand-authored marker', () => {
    expect(describeFeature('chemical-sites', { name: 'Fawley refinery and petrochemicals', industrial: 'refinery', source: 'hand-authored' })).toEqual({
      title: 'Fawley refinery and petrochemicals', overlay: 'Major chemical and fuel sites',
      rows: [['Type', 'Oil refinery'], ['Listed as', 'Major hazard site from the Operation SOS list']],
    });
    expect(describeFeature('chemical-sites', { industrial: 'chemical', operator: 'INEOS' }).rows).toEqual([['Type', 'Chemical works'], ['Run by', 'INEOS']]);
    expect(describeFeature('chemical-sites', { industrial: 'oil' }).title).toBe('Oil terminal or depot');
  });

  it('airports and military: aerodromes, military airfields and other military land', () => {
    expect(describeFeature('airports-military', { name: 'Southampton Airport', aeroway: 'aerodrome', operator: 'AGS Airports', iata: 'SOU', icao: 'EGHI' }).rows).toEqual([
      ['Type', 'Airport or airfield'], ['Code', 'SOU / EGHI'], ['Run by', 'AGS Airports'],
    ]);
    expect(describeFeature('airports-military', { name: 'RAF Brize Norton', aeroway: 'aerodrome', military: 'airfield' }).rows[0]).toEqual(['Type', 'Military airfield']);
    expect(describeFeature('airports-military', { aeroway: 'aerodrome', 'aerodrome:type': 'international' }).title).toBe('International airport');
    expect(describeFeature('airports-military', { military: 'barracks', name: 'Marchwood' }).rows).toEqual([['Type', 'Barracks']]);
    expect(describeFeature('airports-military', { military: 'naval_base' }).title).toBe('Naval base');
    expect(describeFeature('airports-military', { military: 'danger_area' }).title).toBe('Military danger area');
    expect(describeFeature('airports-military', { military: 'yes' }).title).toBe('Military land');
    expect(describeFeature('airports-military', { military: 'radar_station' }).title).toBe('Military land (radar station)');
  });

  it('footpaths: rights of way by designation, other paths by highway type, with access, surface and difficulty', () => {
    expect(describeFeature('footpaths', { highway: 'footway', designation: 'public_footpath', prow_ref: 'Copythorne FP 14', foot: 'designated', surface: 'grass' })).toEqual({
      title: 'Public footpath', overlay: 'Footpaths and rights of way',
      rows: [['Type', 'Public footpath'], ['Who may use it', 'On foot'], ['Right of way number', 'Copythorne FP 14'], ['On foot', 'Signed for this use'], ['Surface', 'Grass']],
    });
    expect(describeFeature('footpaths', { highway: 'bridleway', designation: 'public_bridleway', name: 'Denny Lodge BR 1' }).rows).toEqual([['Type', 'Public bridleway'], ['Who may use it', 'On foot, on horseback and by bicycle']]);
    expect(describeFeature('footpaths', { designation: 'restricted_byway' }).rows[1][1]).toContain('no motor vehicles');
    expect(describeFeature('footpaths', { designation: 'byway_open_to_all_traffic' }).title).toBe('Byway open to all traffic');
    expect(describeFeature('footpaths', { designation: 'core_path' }).title).toBe('Scottish core path');
    expect(describeFeature('footpaths', { highway: 'path', designation: 'none', access: 'private', surface: 'compacted', sac_scale: 'mountain_hiking', trail_visibility: 'bad' })).toEqual({
      title: 'Path', overlay: 'Footpaths and rights of way',
      rows: [['Type', 'Path'], ['Access', 'Private, no public access'], ['Surface', 'Compacted'], ['Difficulty', 'Mountain walking, some steep ground'], ['Visibility', 'Path hard to follow']],
    });
    expect(describeFeature('footpaths', { highway: 'track', name: 'Beechdale Walk', access: 'permissive' }).title).toBe('Beechdale Walk');
    expect(describeFeature('footpaths', { highway: 'cycleway' }).title).toBe('Cycle path');
    expect(describeFeature('footpaths', { highway: 'steps' }).title).toBe('Steps');
  });

  it('access land: CROW open country and common land with the region', () => {
    expect(describeFeature('access-land', { Descrip: 'Open Country', source: 'fixture sample', region: 'england' })).toEqual({
      title: 'Open access land', overlay: 'Open access land',
      rows: [['Designation', 'Open country (CROW Act)'], ['What it means', 'Mountain, moor, heath or down you may walk on freely under the Countryside and Rights of Way Act 2000'], ['Region', 'England']],
    });
    expect(describeFeature('access-land', { Descrip: 'Registered Common Land', region: 'wales' }).rows).toEqual([
      ['Designation', 'Registered common land'], ['What it means', 'Open to walk on under the Countryside and Rights of Way Act 2000'], ['Region', 'Wales'],
    ]);
    expect(describeFeature('access-land', { Descrip: 'Section 16 Dedicated Land' }).rows[0]).toEqual(['Designation', 'Dedicated access land']);
    expect(describeFeature('access-land', { name: 'Dartmoor' }, { sourceLayer: 'access-land' }).title).toBe('Dartmoor');
  });

  it('flood zones: zone 2 and 3 with what they mean and the region from the vector layer', () => {
    expect(describeFeature('flood-zones', { zone: '3', source: 'fixture sample' }, { sourceLayer: 'flood_england' })).toEqual({
      title: 'Flood zone 3', overlay: 'Flood zones',
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

  it('an unknown overlay still gets a name, a humanised overlay title and the shared rows', () => {
    expect(describeFeature('shelters', { name: 'Village hall', phone: '01onalone' })).toEqual({ title: 'Village hall', overlay: 'Shelters', rows: [['Phone', '01onalone']] });
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
