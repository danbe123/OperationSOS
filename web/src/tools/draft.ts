/** What somebody was in the middle of writing, kept in the browser until it is saved or given up, so a
 * browser that restarts, a screen that throws or a box that stops answering does not take it with it.
 * Storage may be unavailable (private mode, a full disk): every access is guarded and the form works
 * without it. A draft older than a week is forgotten. */
const WEEK_MS = 7 * 24 * 3600 * 1000;

type Stored = { at: number; value: Record<string, string> };

export function loadDraft(name: string, now: number = Date.now()): Record<string, string> | null {
  try {
    const raw = localStorage.getItem(`sos.draft.${name}`);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Stored;
    if (typeof parsed.at !== 'number' || now - parsed.at > WEEK_MS || typeof parsed.value !== 'object' || parsed.value === null) return null;
    return parsed.value;
  } catch {
    return null;
  }
}

export function saveDraft(name: string, value: Record<string, string>, now: number = Date.now()): void {
  try {
    if (Object.values(value).every((v) => v.trim() === '')) {
      localStorage.removeItem(`sos.draft.${name}`);
      return;
    }
    localStorage.setItem(`sos.draft.${name}`, JSON.stringify({ at: now, value } satisfies Stored));
  } catch {
    // no storage: the text is still on the screen
  }
}

export function clearDraft(name: string): void {
  try {
    localStorage.removeItem(`sos.draft.${name}`);
  } catch {
    // no storage
  }
}
