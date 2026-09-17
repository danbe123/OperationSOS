import { describe, it, expect, vi, afterEach } from 'vitest';
import { chunkText, CHUNK_CHARS, resetSpeech, speakFrom, visibleText } from '../../src/tools/speech';
import { api } from '../../src/api/client';

describe('chunkText', () => {
  it('keeps short text in one chunk and collapses whitespace', () => {
    expect(chunkText('  Fill the bath.\n\nThen shut the freezer.  ')).toEqual(['Fill the bath. Then shut the freezer.']);
    expect(chunkText('   ')).toEqual([]);
  });

  it('cuts long text at sentence ends, under the chunk size', () => {
    const sentence = `${'word '.repeat(40).trim()}. `;
    const chunks = chunkText(sentence.repeat(12));
    expect(chunks.length).toBeGreaterThan(1);
    for (const c of chunks) expect(c.length).toBeLessThanOrEqual(CHUNK_CHARS);
    expect(chunks.join(' ').replace(/\s+/g, ' ')).toBe(sentence.repeat(12).replace(/\s+/g, ' ').trim());
  });

  it('splits a sentence with no full stop on word boundaries', () => {
    const chunks = chunkText('word '.repeat(400).trim());
    expect(chunks.length).toBeGreaterThan(1);
    for (const c of chunks) {
      expect(c.length).toBeLessThanOrEqual(CHUNK_CHARS);
      expect(c.startsWith('word')).toBe(true);
    }
  });
});

describe('visibleText', () => {
  it('reads what is on the screen, without buttons, icons or print-only parts', () => {
    const el = document.createElement('div');
    el.innerHTML = `
      <h2>Power</h2>
      <p>Keep the freezer <span aria-hidden="true">✕</span> shut.</p>
      <button class="read-aloud">Read aloud</button>
      <p class="no-print">Printed only</p>
      <select><option>Sam</option></select>`;
    expect(visibleText(el)).toBe('Power Keep the freezer shut.');
  });

  it('leaves the citations and the source line on the page rather than reading them out', () => {
    const el = document.createElement('div');
    el.innerHTML = `
      <p>Keep going for thirty minutes (<a href="/doc/austere#page=96">Survival and Austere Medicine, p. 96</a>; <a href="/read/w/CPR">CPR (Wikipedia)</a>).</p>
      <p>Send someone (<a href="/p/no-phones">getting help without phones</a>). Read <a href="/m/water">the water guide</a> first.</p>
      <div class="card-source"><p><a href="/doc/austere">Survival and Austere Medicine</a></p></div>`;
    expect(visibleText(el)).toBe('Keep going for thirty minutes. Send someone. Read the water guide first.');
  });
});

describe('speakFrom', () => {
  afterEach(() => { resetSpeech(); vi.restoreAllMocks(); });

  it('asks the box for the next piece while this one plays, and turns to each piece as it is read', async () => {
    const plays: string[] = [];
    let endPlay: () => void = () => undefined;
    vi.spyOn(HTMLMediaElement.prototype, 'play').mockImplementation(function play(this: HTMLMediaElement) {
      plays.push(this.src);
      new Promise<void>((r) => { endPlay = r; }).then(() => this.dispatchEvent(new Event('ended')));
      return Promise.resolve();
    });
    let n = 0;
    globalThis.URL.createObjectURL = () => `blob:${n++}`;
    globalThis.URL.revokeObjectURL = () => {};
    const speak = vi.spyOn(api, 'speak').mockImplementation(async (text: string) => new Blob([text]));
    const turned: string[] = [];
    async function* pieces() {
      yield { text: 'One.', before: () => turned.push('one') };
      yield { text: 'Two.', before: () => turned.push('two') };
      yield { text: 'Three.', before: () => turned.push('three') };
    }
    const done = speakFrom('book', pieces());
    // the first piece is playing; the second has already been asked for
    await vi.waitFor(() => expect(plays).toEqual(['blob:0']));
    expect(speak.mock.calls.map((c) => c[0])).toEqual(['One.', 'Two.']);
    expect(turned).toEqual(['one']);
    endPlay();
    await vi.waitFor(() => expect(plays).toEqual(['blob:0', 'blob:1']));
    expect(speak.mock.calls.map((c) => c[0])).toEqual(['One.', 'Two.', 'Three.']);
    expect(turned).toEqual(['one', 'two']);
    endPlay();
    await vi.waitFor(() => expect(plays).toHaveLength(3));
    endPlay();
    await done;
    expect(turned).toEqual(['one', 'two', 'three']);
  });

  it('cuts a piece longer than the voice can take, in order, before the next piece', async () => {
    vi.spyOn(HTMLMediaElement.prototype, 'play').mockImplementation(function play(this: HTMLMediaElement) {
      setTimeout(() => this.dispatchEvent(new Event('ended')), 0);
      return Promise.resolve();
    });
    globalThis.URL.createObjectURL = () => 'blob:x';
    globalThis.URL.revokeObjectURL = () => {};
    const speak = vi.spyOn(api, 'speak').mockImplementation(async (text: string) => new Blob([text]));
    const long = `${'word '.repeat(150).trim()}. ${'more '.repeat(150).trim()}.`;
    async function* pieces() { yield { text: long }; yield { text: 'After.' }; }
    await speakFrom('book', pieces());
    const said = speak.mock.calls.map((c) => c[0]);
    expect(said.length).toBe(5);   // two sentences of 749 characters, each cut in two, then the piece after
    expect(said[0].startsWith('word')).toBe(true);
    expect(said[1].startsWith('word')).toBe(true);
    expect(said[2].startsWith('more')).toBe(true);
    expect(said[4]).toBe('After.');
  });
});
