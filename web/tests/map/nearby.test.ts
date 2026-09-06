import { describe, it, expect } from 'vitest';
import { describeNearby, describeRoute, leadFacility, nearbyGap, nearbyIcon } from '../../src/map/nearby';
import { nearby } from '../fixtures/api';

describe('nearby', () => {
  it('reads a place as distance, walking time and the box\'s own compass point', () => {
    const pharmacy = nearby.facilities.find((f) => f.id === 'pharmacy')!;
    expect(describeNearby(pharmacy.nearest!)).toBe('620 m to the east, about 8 min on foot');
    expect(describeNearby({ distance_m: 4300, walk_minutes: 52, bearing_deg: 270, compass: 'W' })).toBe('4.30 km to the west, about 52 min on foot');
    expect(describeNearby({ distance_m: 800, walk_minutes: 10, bearing_deg: 45, compass: 'NE' })).toBe('800 m to the north-east, about 10 min on foot');
  });

  it('gives every facility an icon, known or not', () => {
    expect(nearbyIcon('emergency-department')).toBe('medical');
    expect(nearbyIcon('something-new')).toBe('pin');
  });

  it('says why a facility came back empty', () => {
    const rest = nearby.facilities.find((f) => f.id === 'rest-centre')!;
    expect(nearbyGap(rest)).toBe(rest.why);
    expect(nearbyGap({ id: 'x', title: 'X', found: false, nearest: null, also: [] })).toContain('Nothing matching');
  });

  it('leads with the kind you chose, or with the first kind it found anything for', () => {
    const empty = { id: 'rest-centre', title: 'Rest centre', found: false, nearest: null, also: [] };
    expect(leadFacility(nearby.facilities, null)!.id).toBe('pharmacy');
    expect(leadFacility(nearby.facilities, 'emergency-department')!.id).toBe('emergency-department');
    // a kind chosen before a search from a new centre that no longer carries it falls back rather than blanking
    expect(leadFacility(nearby.facilities, 'gone')!.id).toBe('pharmacy');
    // nothing found anywhere still leads with a kind, so the head can say why it is empty
    expect(leadFacility([empty], null)).toBe(empty);
    expect(leadFacility([], null)).toBeNull();
  });

  it('describes a straight line, naming where it starts', () => {
    const r = describeRoute({ lat: 50.93, lon: -1.43 }, { lat: 50.9331, lon: -1.4342 }, 'Southampton General Hospital');
    expect(r.text).toMatch(/^Southampton General Hospital: \d+ m from home, bearing \d{3}° [NEWS]+, about \d+ min on foot$/);
    expect(r.minutes).toBe(Math.round(r.km * 12));
    const fromCentre = describeRoute({ lat: 50.93, lon: -1.43 }, { lat: 51.93, lon: -1.43 }, 'Far away', 'the centre');
    expect(fromCentre.text).toContain('from the centre');
    expect(Math.round(fromCentre.bearing)).toBe(0);
  });
});
