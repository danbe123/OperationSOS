// Supply arithmetic. Every function returns null for inputs that make no sense rather than NaN or Infinity.

export function generatorHours(tankLitres: number, litresPerHour: number): number | null {
  if (!(tankLitres > 0) || !(litresPerHour > 0)) return null;
  return tankLitres / litresPerHour;
}

/** Usable hours from a battery: capacity × inverter efficiency ÷ load. LiFePO4 solar generators quote watt-hours directly. */
export function batteryHours(wattHours: number, loadWatts: number, efficiency = 0.85): number | null {
  if (!(wattHours > 0) || !(loadWatts > 0) || !(efficiency > 0)) return null;
  return (wattHours * efficiency) / loadWatts;
}

/** Watt-hours per day a panel gives in the UK for a calendar month (1 to 12), low and high, from the solar page's band:
 * roughly 0.5 to 1 kWh per kWp a day in December and 4 to 5 in June, interpolated linearly between. */
export function solarDailyWh(panelWatts: number, month: number): { low: number; high: number } | null {
  if (!(panelWatts > 0) || !(month >= 1 && month <= 12)) return null;
  const fromJune = Math.min(Math.abs(month - 6), 12 - Math.abs(month - 6));   // 0 in June, 6 in December
  const low = 4 - ((4 - 0.5) * fromJune) / 6;
  const high = 5 - ((5 - 1) * fromJune) / 6;
  return { low: Math.round(panelWatts * low), high: Math.round(panelWatts * high) };
}

export function rationDays(quantity: number, people: number, perPersonDay: number): number | null {
  if (!(quantity >= 0) || !(people > 0) || !(perPersonDay > 0)) return null;
  return quantity / (people * perPersonDay);
}

export function formatHours(hours: number): string {
  if (hours >= 48) return `${(hours / 24).toFixed(1)} days`;
  if (hours >= 10) return `${Math.round(hours)} h`;
  const h = Math.floor(hours);
  const m = Math.round((hours - h) * 60);
  return h ? `${h} h ${m} min` : `${m} min`;
}
