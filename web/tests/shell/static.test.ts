import { describe, it, expect } from 'vitest';
import { readFileSync, statSync } from 'node:fs';

const pub = (name: string) => new URL(`../../public/${name}`, import.meta.url);

describe('static pages', () => {
  it('welcome.html is under 20 KB, has no app JavaScript, lists the IP first and shows a QR code', () => {
    const html = readFileSync(pub('welcome.html'), 'utf8');
    expect(statSync(pub('welcome.html')).size).toBeLessThan(20 * 1024);
    expect(html).not.toMatch(/<script[^>]+src=/);
    expect(html).not.toContain('/assets/');
    expect(html).toContain('Open http://10.42.0.1 in your browser (or http://sos.box)');
    expect(html.indexOf('10.42.0.1')).toBeLessThan(html.indexOf('sos.box'));
    expect(html).toContain('<svg');
    expect(html).toContain('If the page will not load, turn mobile data off');
    expect(html).toContain('Tap Done or Cancel to leave this screen; the WiFi stays connected');
    expect(html).toContain('id="ssid"');
  });

  it('starting.html polls /api/status and then replaces itself with /?kiosk=1', () => {
    const html = readFileSync(pub('starting.html'), 'utf8');
    expect(html).not.toMatch(/<script[^>]+src=/);
    expect(html).toContain("fetch('/api/status'");
    expect(html).toContain("location.replace('/?kiosk=1')");
  });

  it('manifest names the app and ships two icons', () => {
    const manifest = JSON.parse(readFileSync(pub('manifest.webmanifest'), 'utf8')) as { name: string; short_name: string; icons: { src: string }[] };
    expect(manifest.name).toBe('Operation SOS');
    expect(manifest.short_name).toBe('SOS');
    expect(manifest.icons.map((i) => i.src)).toEqual(['/icons/icon-192.png', '/icons/icon-512.png']);
    expect(statSync(pub('icons/icon-192.png')).size).toBeGreaterThan(500);
    expect(statSync(pub('icons/icon-512.png')).size).toBeGreaterThan(500);
  });
});
