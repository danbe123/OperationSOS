/** How the box should sound, kept in this browser: which of the installed voices, and how fast. It applies
 * to everything read aloud — a briefing, a page, a book. Empty voice means the box's own default. */
export const VOICE_KEY = 'sos.voice.id';
export const SPEED_KEY = 'sos.voice.speed';

export const SPEEDS: { value: number; label: string }[] = [
  { value: 0.85, label: 'Slower' },
  { value: 1, label: 'Normal' },
  { value: 1.2, label: 'Faster' },
];

export type VoicePrefs = { voice: string; speed: number };

function read(key: string): string | null {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

export function voicePrefs(): VoicePrefs {
  const speed = Number(read(SPEED_KEY));
  return { voice: read(VOICE_KEY) ?? '', speed: SPEEDS.some((s) => s.value === speed) ? speed : 1 };
}

export function setVoicePrefs(prefs: Partial<VoicePrefs>): void {
  try {
    if (prefs.voice !== undefined) localStorage.setItem(VOICE_KEY, prefs.voice);
    if (prefs.speed !== undefined) localStorage.setItem(SPEED_KEY, String(prefs.speed));
  } catch {
    // storage is optional
  }
}
