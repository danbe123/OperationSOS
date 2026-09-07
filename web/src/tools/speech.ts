// Reading aloud: the visible words of a screen, cut into chunks Piper can voice, played one after
// the other. One reader at a time for the whole app, and the buttons take themselves away as soon
// as the box answers 503 (no voice installed).
import { useSyncExternalStore } from 'react';
import { api, ApiError } from '../api/client';
import { errorMessage } from '../api/useQuery';
import { notify } from '../components/Notice';

export const CHUNK_CHARS = 600;
const AVAILABLE_KEY = 'sos.speech';

/** Cut text into chunks of about 600 characters, on sentence ends where it can and words where it must. */
export function chunkText(text: string, max = CHUNK_CHARS): string[] {
  const clean = text.replace(/\s+/g, ' ').trim();
  if (!clean) return [];
  const pieces: string[] = [];
  for (const sentence of clean.split(/(?<=[.!?;:])\s+/)) {
    if (sentence.length <= max) {
      pieces.push(sentence);
      continue;
    }
    let line = '';
    for (const word of sentence.split(' ')) {
      if (line && line.length + 1 + word.length > max) {
        pieces.push(line);
        line = word;
      } else {
        line = line ? `${line} ${word}` : word;
      }
    }
    if (line) pieces.push(line);
  }
  const chunks: string[] = [];
  for (const piece of pieces) {
    const last = chunks[chunks.length - 1];
    if (last && last.length + 1 + piece.length <= max) chunks[chunks.length - 1] = `${last} ${piece}`;
    else chunks.push(piece);
  }
  return chunks;
}

const BLOCK = new Set([
  'P', 'DIV', 'SECTION', 'ARTICLE', 'HEADER', 'FOOTER', 'ASIDE', 'MAIN', 'BLOCKQUOTE', 'FIGCAPTION',
  'H1', 'H2', 'H3', 'H4', 'H5', 'H6', 'UL', 'OL', 'LI', 'DL', 'DT', 'DD', 'TABLE', 'TR', 'TD', 'TH', 'BR', 'HR',
]);

function collect(node: Node, out: string[]): void {
  if (node.nodeType === Node.TEXT_NODE) {
    out.push(node.nodeValue ?? '');
    return;
  }
  if (node.nodeType !== Node.ELEMENT_NODE) return;
  const el = node as Element;
  const block = BLOCK.has(el.tagName);
  if (block) out.push(' ');
  for (const child of Array.from(el.childNodes)) collect(child, out);
  if (block) out.push(' ');
}

/** The words a reader would say: what is on the screen, without the buttons, the icons or the print-only
 * parts, with a gap wherever the layout has one so two paragraphs never run into one word. */
/** A parenthesis holding nothing but links — "(Survival and Austere Medicine, p. 96; Wikipedia)" — is a
 * citation: it belongs on the page and in print, not in the reader's mouth between two instructions. */
const CITATION = /\s*\(\s*(?:<a\b[^>]*>[^<]*<\/a>\s*[;,]?\s*)+\)/g;

export function visibleText(root: Element): string {
  const clone = root.cloneNode(true) as Element;
  clone.innerHTML = clone.innerHTML.replace(CITATION, '');
  for (const el of clone.querySelectorAll('button, [aria-hidden="true"], .no-print, .read-aloud, .card-source, .scenario-sources, .sources, .doc-sources, script, style, select, input, svg')) el.remove();
  const out: string[] = [];
  collect(clone, out);
  return out.join('').replace(/\s+/g, ' ').trim();
}

let speaking: string | null = null;
let available = true;
let stopped = false;
let current: HTMLAudioElement | null = null;
let listeners: (() => void)[] = [];
export type SpeechState = { speaking: string | null; available: boolean };
let snapshot: SpeechState = { speaking, available };

function emit(): void {
  snapshot = { speaking, available };
  listeners.forEach((l) => l());
}

try {
  if (typeof sessionStorage !== 'undefined' && sessionStorage.getItem(AVAILABLE_KEY) === 'off') available = false;
} catch {
  // storage is optional
}
snapshot = { speaking, available };

async function play(blob: Blob): Promise<void> {
  const url = URL.createObjectURL(blob);
  try {
    const el = new Audio(url);
    current = el;
    await new Promise<void>((resolve) => {
      el.onended = () => resolve();
      el.onerror = () => resolve();
      // The kiosk browser only lets audio start from a gesture; this always runs from the button's click.
      const started = el.play() as unknown as Promise<void> | undefined;
      if (started && typeof started.catch === 'function') started.catch(() => resolve());
      else if (!started) resolve(); // no media support (a test environment): the fetch still happened
    });
  } finally {
    current = null;
    URL.revokeObjectURL?.(url);
  }
}

/** Read `text` aloud under the id of the button that asked, chunk by chunk. Stops whatever was reading. */
export async function speak(id: string, text: string): Promise<void> {
  stopSpeaking();
  const chunks = chunkText(text);
  if (chunks.length === 0) return;
  speaking = id;
  stopped = false;
  emit();
  try {
    for (const chunk of chunks) {
      if (stopped) break;
      const blob = await api.speak(chunk);
      if (stopped) break;
      await play(blob);
    }
  } catch (e) {
    // 503: no voice installed. 404: a box built before it had one. Either way, stop offering it.
    if (e instanceof ApiError && (e.status === 503 || e.status === 404)) {
      available = false;
      try { sessionStorage.setItem(AVAILABLE_KEY, 'off'); } catch { /* storage is optional */ }
      notify('This box has no voice installed, so it cannot read pages aloud.');
    } else {
      notify(`Could not read that aloud: ${errorMessage(e)}`);
    }
  } finally {
    speaking = null;
    stopped = false;
    emit();
  }
}

export function stopSpeaking(): void {
  stopped = true;
  current?.pause();
  current = null;
  if (speaking !== null) {
    speaking = null;
    emit();
  }
}

/** Tests start from silence and a box that still has its voice. */
export function resetSpeech(): void {
  stopSpeaking();
  available = true;
  emit();
}

export function useSpeech(): SpeechState {
  return useSyncExternalStore(
    (l) => {
      listeners = [...listeners, l];
      return () => { listeners = listeners.filter((x) => x !== l); };
    },
    () => snapshot,
  );
}
