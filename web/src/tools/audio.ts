// Clicks and alarms through the Web Audio API. Silent when the browser has no AudioContext (tests, old phones).
let ctx: AudioContext | null | undefined;

function context(): AudioContext | null {
  if (ctx !== undefined) return ctx;
  const Ctor = (globalThis as { AudioContext?: typeof AudioContext; webkitAudioContext?: typeof AudioContext }).AudioContext
    ?? (globalThis as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
  ctx = Ctor ? new Ctor() : null;
  return ctx;
}

function tone(frequency: number, seconds: number, at = 0): void {
  const c = context();
  if (!c) return;
  if (c.state === 'suspended') void c.resume();
  const osc = c.createOscillator();
  const gain = c.createGain();
  osc.type = 'square';
  osc.frequency.value = frequency;
  gain.gain.value = 0.2;
  osc.connect(gain).connect(c.destination);
  osc.start(c.currentTime + at);
  osc.stop(c.currentTime + at + seconds);
}

export function click(): void {
  tone(1000, 0.04);
}

export function alarm(): void {
  for (let i = 0; i < 6; i++) tone(i % 2 ? 660 : 880, 0.18, i * 0.25);
}
