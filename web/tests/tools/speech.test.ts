import { describe, it, expect } from 'vitest';
import { chunkText, CHUNK_CHARS, visibleText } from '../../src/tools/speech';

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
});
