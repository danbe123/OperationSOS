// Sunrise, sunset and civil twilight from the NOAA solar calculator equations. Pure arithmetic, no data files.
// Times come back as UTC Date objects; callers format them in the viewer's zone.

export type SunTimes =
  | { polar: null; sunrise: Date; sunset: Date; civilDawn: Date | null; civilDusk: Date | null; dayLengthMin: number; solarNoon: Date }
  | { polar: 'day' | 'night'; solarNoon: Date; dayLengthMin: number };

const RAD = Math.PI / 180;

function julianDay(date: Date): number {
  return date.getTime() / 86_400_000 + 2_440_587.5;
}

/** Equation of time (minutes) and solar declination (degrees) for a Julian day. */
function solarParams(jd: number): { eqTime: number; declination: number } {
  const t = (jd - 2_451_545) / 36_525;
  const l0 = (280.46646 + t * (36_000.76983 + t * 0.0003032)) % 360;
  const m = 357.52911 + t * (35_999.05029 - 0.0001537 * t);
  const e = 0.016708634 - t * (0.000042037 + 0.0000001267 * t);
  const c = Math.sin(m * RAD) * (1.914602 - t * (0.004817 + 0.000014 * t)) + Math.sin(2 * m * RAD) * (0.019993 - 0.000101 * t) + Math.sin(3 * m * RAD) * 0.000289;
  const trueLong = l0 + c;
  const omega = 125.04 - 1934.136 * t;
  const apparentLong = trueLong - 0.00569 - 0.00478 * Math.sin(omega * RAD);
  const obliq0 = 23 + (26 + (21.448 - t * (46.815 + t * (0.00059 - t * 0.001813))) / 60) / 60;
  const obliq = obliq0 + 0.00256 * Math.cos(omega * RAD);
  const declination = Math.asin(Math.sin(obliq * RAD) * Math.sin(apparentLong * RAD)) / RAD;
  const y = Math.tan((obliq / 2) * RAD) ** 2;
  const eqTime = 4 / RAD * (
    y * Math.sin(2 * l0 * RAD) - 2 * e * Math.sin(m * RAD) + 4 * e * y * Math.sin(m * RAD) * Math.cos(2 * l0 * RAD)
    - 0.5 * y * y * Math.sin(4 * l0 * RAD) - 1.25 * e * e * Math.sin(2 * m * RAD));
  return { eqTime, declination };
}

/** Hour angle (degrees) at which the sun's centre reaches the given zenith, or null when it never does that day. */
function hourAngle(lat: number, declination: number, zenith: number): number | null {
  const cosH = (Math.cos(zenith * RAD) / (Math.cos(lat * RAD) * Math.cos(declination * RAD))) - Math.tan(lat * RAD) * Math.tan(declination * RAD);
  if (cosH > 1 || cosH < -1) return null;
  return Math.acos(cosH) / RAD;
}

function utcDate(dayStartUtc: Date, minutes: number): Date {
  return new Date(dayStartUtc.getTime() + minutes * 60_000);
}

/** Sun events for the civil date `date` (its UTC calendar day is used) at a location. */
export function sunTimes(lat: number, lon: number, date: Date): SunTimes {
  const dayStart = new Date(Date.UTC(date.getUTCFullYear(), date.getUTCMonth(), date.getUTCDate()));
  // iterate once from noon so the declination matches the actual event times
  const noonGuess = julianDay(dayStart) + 0.5 - lon / 360;
  const p0 = solarParams(noonGuess);
  const noonMin = 720 - 4 * lon - p0.eqTime;
  const solarNoon = utcDate(dayStart, noonMin);
  const p = solarParams(julianDay(solarNoon));
  const ha = hourAngle(lat, p.declination, 90.833);
  if (ha === null) {
    const up = lat * p.declination > 0;   // same hemisphere as the sun: it never sets
    return { polar: up ? 'day' : 'night', solarNoon, dayLengthMin: up ? 1440 : 0 };
  }
  const rise = solarParams(julianDay(utcDate(dayStart, noonMin - ha * 4)));
  const set = solarParams(julianDay(utcDate(dayStart, noonMin + ha * 4)));
  const haRise = hourAngle(lat, rise.declination, 90.833) ?? ha;
  const haSet = hourAngle(lat, set.declination, 90.833) ?? ha;
  const sunriseMin = 720 - 4 * (lon + haRise) - rise.eqTime;
  const sunsetMin = 720 - 4 * (lon - haSet) - set.eqTime;
  const civil = hourAngle(lat, p.declination, 96);
  return {
    polar: null,
    sunrise: utcDate(dayStart, sunriseMin),
    sunset: utcDate(dayStart, sunsetMin),
    civilDawn: civil === null ? null : utcDate(dayStart, 720 - 4 * (lon + civil) - p.eqTime),
    civilDusk: civil === null ? null : utcDate(dayStart, 720 - 4 * (lon - civil) - p.eqTime),
    dayLengthMin: Math.round(sunsetMin - sunriseMin),
    solarNoon,
  };
}

export function formatDayLength(minutes: number): string {
  const h = Math.floor(minutes / 60);
  const m = Math.round(minutes % 60);
  return `${h} h ${m.toString().padStart(2, '0')} min`;
}
