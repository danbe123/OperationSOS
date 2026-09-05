// What the box can sense, in words: a title per sensor and a reading a household can read.
import type { SensorReading } from '../api/types';

export const SENSOR_INFO: Record<string, { title: string; icon: string }> = {
  internet: { title: 'Internet probe', icon: 'globe' },
  mains: { title: 'Mains power at the box', icon: 'bolt' },
  temp_in: { title: 'Temperature inside', icon: 'thermometer' },
  temp_out: { title: 'Temperature outside', icon: 'thermometer' },
  humidity: { title: 'Humidity', icon: 'drop' },
  pressure_hpa: { title: 'Air pressure', icon: 'wave' },
  co_ppm: { title: 'Carbon monoxide', icon: 'alert' },
  radiation_usvh: { title: 'Radiation', icon: 'radiation' },
  leak: { title: 'Water leak', icon: 'drop' },
  broadcast: { title: 'Radio bands', icon: 'radio' },
  hotspot_clients: { title: 'Phones on the hotspot', icon: 'wifi' },
  cpu_temp: { title: 'Box temperature', icon: 'thermometer' },
};

/** Units that mean yes or no rather than a quantity, and the word for the other answer. */
const FLAGS: Record<string, string> = { up: 'down', on: 'off', present: 'absent', ok: 'not ok', open: 'shut', dry: 'wet' };

export function sensorTitle(id: string): string {
  if (SENSOR_INFO[id]) return SENSOR_INFO[id].title;
  const words = id.replace(/[_-]+/g, ' ').trim();
  return words ? words[0].toUpperCase() + words.slice(1) : id;
}

export function sensorIcon(id: string): string {
  return SENSOR_INFO[id]?.icon ?? 'help';
}

/** "up", "down", "14.5 °C", "3 ppm": the reading as the sheet says it. */
export function readingText(reading: SensorReading): string {
  const opposite = FLAGS[reading.unit];
  if (opposite !== undefined) return reading.value >= 1 ? reading.unit : opposite;
  const value = Number.isInteger(reading.value) ? String(reading.value) : String(Math.round(reading.value * 10) / 10);
  return reading.unit ? `${value} ${reading.unit}` : value;
}

/** A reading is worth a second look when it says something is wrong, not merely something is. */
export function readingTone(id: string, reading: SensorReading): 'ok' | 'warn' | 'danger' | 'default' {
  const opposite = FLAGS[reading.unit];
  if (opposite !== undefined) return reading.value >= 1 ? 'ok' : 'danger';
  if (id === 'co_ppm') return reading.value >= 50 ? 'danger' : reading.value >= 10 ? 'warn' : 'ok';
  if (id === 'temp_in') return reading.value < 16 ? 'warn' : 'ok';
  return 'default';
}
