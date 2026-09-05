import { describe, it, expect } from 'vitest';
import { describeNearby, describeRoute, nearbyGap, nearbyIcon } from '../../src/map/nearby';
import { nearby } from '../fixtures/api';

describe('nearby', () => {
  it('reads a place as distance, walking time and the box\'s own compass point', () => {
    const pharmacy = nearby.facilities.find((f) => f.id === 'pharmacy')!;
    expect(describeNearby(pharmacy.nearest!)).toBe('620 m · 8 min on foot · 092° E');
    expect(describeNearby({ distance_m: 4300, walk_minutes: 52, bearing_deg: 270, compass: 'W' })).toBe('4.30 km · 52 min on foot · 270° W');
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

  it('describes a straight line, naming where it starts', () => {
    const r = describeRoute({ lat: 50.93, lon: -1.43 }, { lat: 50.9331, lon: -1.4342 }, 'Southampton General Hospital');
    expect(r.text).toMatch(/^Southampton General Hospital: \d+ m from home, bearing \d{3}° [NEWS]+, about \d+ min on foot$/);
    expect(r.minutes).toBe(Math.round(r.km * 12));
    const fromCentre = describeRoute({ lat: 50.93, lon: -1.43 }, { lat: 51.93, lon: -1.43 }, 'Far away', 'the centre');
    expect(fromCentre.text).toContain('from the centre');
    expect(Math.round(fromCentre.bearing)).toBe(0);
  });
});
