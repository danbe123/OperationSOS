import { describe, it, expect } from 'vitest';
import { describeNearby, describeRoute, NEARBY_TITLE } from '../../src/map/nearby';
import { nearby } from '../fixtures/api';

describe('nearby', () => {
  it('reads a facility as distance, walking time and bearing', () => {
    expect(describeNearby(nearby.items[0])).toBe('620 m · 8 min on foot · 092° E');
    expect(describeNearby({ distance_m: 4300, walk_min: 52, bearing_deg: 270 })).toBe('4.30 km · 52 min on foot · 270° W');
    expect(NEARBY_TITLE['emergency-department']).toBe('A&E');
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
