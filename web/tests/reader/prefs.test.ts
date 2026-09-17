import { describe, it, expect, afterEach } from 'vitest';
import { defaultSizeFor, storedSize, tapZone } from '../../src/reader/prefs';

afterEach(() => localStorage.clear());

describe('the text size a screen starts at', () => {
  it('is bigger on a bigger screen: base on the kiosk and the iPad mini, larger on an iPad Pro or a laptop', () => {
    expect(defaultSizeFor(853)).toBe(100);
    expect(defaultSizeFor(1024)).toBe(100);
    expect(defaultSizeFor(1194)).toBe(125);
    expect(defaultSizeFor(1366)).toBe(150);
    expect(defaultSizeFor(1920)).toBe(150);
  });

  it('gives way to the size you chose on this device', () => {
    expect(storedSize(1366)).toBe(150);
    localStorage.setItem('sos.reader.size', '100');
    expect(storedSize(1366)).toBe(100);
    localStorage.setItem('sos.reader.size', '999');   // not a size the reader offers
    expect(storedSize(1366)).toBe(150);
  });
});

describe('tapZone', () => {
  it('turns back on the left third, on on the right third, and the middle is for the controls', () => {
    expect(tapZone(100, 900)).toBe('previous');
    expect(tapZone(450, 900)).toBe('middle');
    expect(tapZone(800, 900)).toBe('next');
    expect(tapZone(800, 0)).toBe('middle');
  });
});
