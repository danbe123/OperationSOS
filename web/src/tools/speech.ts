// Reading aloud: the visible words of a screen, cut into chunks Piper can voice, played one after
// the other. One reader at a time for the whole app, and the buttons take themselves away as soon
// as the box answers 503 (no voice installed).
import { useSyncExternalStore } from 'react';
import { api, ApiError } from '../api/client';
import { errorMessage } from '../api/useQuery';
import { notify } from '../components/Notice';
import { voicePrefs } from './voice';

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
let paused = false;
let resume: (() => void) | null = null;   // wakes the reading when it was paused between two pieces
/* One player for the whole app, made on the tap that starts a reading and reused for every piece after:
   Safari on the iPad plays only what a touch started, and a new element per piece stopped after the first. */
let player: HTMLAudioElement | null = null;
let listeners: (() => void)[] = [];
export type SpeechState = { speaking: string | null; available: boolean; paused: boolean };
let snapshot: SpeechState = { speaking, available, paused };

function emit(): void {
  snapshot = { speaking, available, paused };
  listeners.forEach((l) => l());
}

function thePlayer(): HTMLAudioElement {
  if (!player) player = new Audio();
  return player;
}

try {
  if (typeof sessionStorage !== 'undefined' && sessionStorage.getItem(AVAILABLE_KEY) === 'off') available = false;
} catch {
  // storage is optional
}
snapshot = { speaking, available, paused };

async function play(blob: Blob): Promise<void> {
  const url = URL.createObjectURL(blob);
  const el = thePlayer();
  try {
    await new Promise<void>((resolve) => {
      el.onended = () => resolve();
      el.onerror = () => resolve();
      el.src = url;
      // The kiosk browser only lets audio start from a gesture; the first piece always runs from the
      // button's click and the same element carries the rest.
      const started = el.play() as unknown as Promise<void> | undefined;
      if (started && typeof started.catch === 'function') started.catch(() => resolve());
      else if (!started) resolve(); // no media support (a test environment): the fetch still happened
    });
  } finally {
    el.onended = null;
    el.onerror = null;
    URL.revokeObjectURL?.(url);
  }
}

/** Waits out a pause that fell between two pieces. */
function untilResumed(): Promise<void> {
  if (!paused) return Promise.resolve();
  return new Promise<void>((r) => { resume = r; });
}

/** One piece of a reading: its words, and what to do as the voice reaches it (turn the page to it). */
export type Piece = { text: string; before?: () => void };

async function* eachOf(pieces: Piece[]): AsyncGenerator<Piece> {
  for (const p of pieces) yield p;
}

/** Read `text` aloud under the id of the button that asked, chunk by chunk. Stops whatever was reading. */
export async function speak(id: string, text: string): Promise<void> {
  const chunks = chunkText(text);
  if (chunks.length === 0) return;
  await speakFrom(id, eachOf(chunks.map((text) => ({ text }))));
}

/** Read a sequence of pieces — a page's chunks, or a book from where you are — under the id of the button
 * that asked. The box is asked for the next piece while this one plays, so the voice does not pause
 * for the synthesiser between paragraphs; a piece longer than the voice's chunk is cut like any text. */
export async function speakFrom(id: string, source: AsyncIterable<Piece>): Promise<void> {
  stopSpeaking();
  speaking = id;
  stopped = false;
  emit();
  const iterator = source[Symbol.asyncIterator]();
  const nextFetch = async (): Promise<{ piece: Piece; blob: Blob } | null> => {
    const { value, done } = await iterator.next();
    if (done || !value) return null;
    const [first, ...rest] = chunkText(value.text);
    if (!first) return nextFetch();
    const blob = await api.speak(first, voicePrefs());
    // a piece the voice has to cut: the remainder is queued back in front of the source, in order
    if (rest.length) pending.unshift(...rest.map((text) => ({ text })));
    return { piece: value, blob };
  };
  const pending: Piece[] = [];
  const pull = async (): Promise<{ piece: Piece; blob: Blob } | null> => {
    const queued = pending.shift();
    if (queued) return { piece: queued, blob: await api.speak(queued.text, voicePrefs()) };
    return nextFetch();
  };
  try {
    let ahead = pull();
    for (;;) {
      const current = await ahead;
      if (!current || stopped) break;
      ahead = pull();   // the next piece is on its way while this one plays
      ahead.catch(() => undefined);
      await untilResumed();
      if (stopped) break;
      current.piece.before?.();
      await play(current.blob);
      if (stopped) break;
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
    void iterator.return?.();
    speaking = null;
    stopped = false;
    emit();
  }
}

export function stopSpeaking(): void {
  stopped = true;
  paused = false;
  player?.pause();
  resume?.();
  resume = null;
  if (speaking !== null) {
    speaking = null;
    emit();
  }
}

/** Hold the reading where it is: mid-piece the player pauses; between pieces the next waits. */
export function pauseSpeaking(): void {
  if (speaking === null || paused) return;
  paused = true;
  player?.pause();
  emit();
}

export function resumeSpeaking(): void {
  if (speaking === null || !paused) return;
  paused = false;
  const wake = resume;
  resume = null;
  if (wake) wake();
  else void player?.play()?.catch?.(() => undefined);
  emit();
}

/** Tests start from silence and a box that still has its voice. */
export function resetSpeech(): void {
  stopSpeaking();
  available = true;
  player = null;
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
