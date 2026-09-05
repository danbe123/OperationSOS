import { describe, it, expect } from 'vitest';
import { batteryHours, formatHours, generatorHours, rationDays, solarDailyWh } from '../../src/tools/calc';

describe('calculators', () => {
  it('generator runtime is tank over consumption and refuses nonsense', () => {
    expect(generatorHours(20, 1.5)).toBeCloseTo(13.33, 1);
    expect(generatorHours(0, 1)).toBeNull();
    expect(generatorHours(5, 0)).toBeNull();
  });
  it('battery hours allow for inverter losses', () => {
    expect(batteryHours(1000, 100)).toBeCloseTo(8.5, 2);
    expect(batteryHours(1280, 40, 1)).toBe(32);
    expect(batteryHours(1000, 0)).toBeNull();
  });
  it('solar output follows the UK seasonal band from the solar page', () => {
    expect(solarDailyWh(1000, 6)).toEqual({ low: 4000, high: 5000 });
    expect(solarDailyWh(1000, 12)).toEqual({ low: 500, high: 1000 });
    expect(solarDailyWh(100, 3)).toEqual({ low: 225, high: 300 });
    expect(solarDailyWh(100, 9)).toEqual(solarDailyWh(100, 3));
    expect(solarDailyWh(100, 13)).toBeNull();
  });
  it('rationing days and hour formatting', () => {
    expect(rationDays(36, 3, 3)).toBe(4);
    expect(rationDays(36, 0, 3)).toBeNull();
    expect(formatHours(0.5)).toBe('30 min');
    expect(formatHours(2.25)).toBe('2 h 15 min');
    expect(formatHours(13.3)).toBe('13 h');
    expect(formatHours(72)).toBe('3.0 days');
  });
});
