import { useEffect, useState } from 'react';
import QRCode from 'qrcode';

export function QrCode({ text, size, label }: { text: string; size: number; label: string }) {
  const [src, setSrc] = useState<string | null>(null);
  useEffect(() => {
    let alive = true;
    QRCode.toDataURL(text, { width: size, margin: 1, color: { dark: '#000000', light: '#ffffff' } })
      .then((url) => { if (alive) setSrc(url); })
      .catch(() => { if (alive) setSrc(null); });
    return () => { alive = false; };
  }, [text, size]);
  return (
    <figure className="qr" style={{ width: size }}>
      {src ? <img src={src} width={size} height={size} alt={`QR code: ${label}`} /> : <div className="qr-blank" style={{ width: size, height: size }} />}
      <figcaption>{label}</figcaption>
    </figure>
  );
}
