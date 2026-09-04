import { writeFileSync } from 'node:fs';
import QRCode from 'qrcode';

const url = 'http://10.42.0.1/';
const svg = (await QRCode.toString(url, { type: 'svg', margin: 1, width: 240, color: { dark: '#000000', light: '#ffffff' } })).replace(/<\?xml[^>]*>\s*/, '');

const html = `<!doctype html>
<html lang="en-GB">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Welcome to Operation SOS</title>
<style>
html,body{margin:0;background:#f4efe4;color:#1a1a1a;font-family:system-ui,-apple-system,sans-serif}
main{max-width:560px;margin:0 auto;padding:24px 16px;display:flex;flex-direction:column;gap:16px;align-items:center;text-align:center}
h1{font-size:28px;margin:0}
.big{font-size:24px;font-weight:700;margin:0}
.ssid{font-size:20px;margin:0}
.qr{width:240px;height:240px;background:#fff;padding:8px;border:1px solid #b8ae94}
.help{font-size:17px;margin:0}
</style>
</head>
<body>
<main>
<h1>Operation SOS</h1>
<p class="ssid">You are connected to WiFi <strong id="ssid">SOS</strong></p>
<p class="big">Open http://10.42.0.1 in your browser (or http://sos.box)</p>
<div class="qr">${svg}</div>
<p class="help">If the page will not load, turn mobile data off.</p>
<p class="help">Tap Done or Cancel to leave this screen; the WiFi stays connected.</p>
</main>
<script>
fetch('/api/status').then(function (r) { return r.json(); }).then(function (s) {
  if (s && s.hotspot && s.hotspot.ssid) { document.getElementById('ssid').textContent = s.hotspot.ssid; }
}).catch(function () {});
</script>
</body>
</html>
`;

const out = new URL('../public/welcome.html', import.meta.url);
writeFileSync(out, html);
console.log(`wrote public/welcome.html (${Buffer.byteLength(html)} bytes)`);
