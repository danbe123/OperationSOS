import type { ReactNode } from 'react';

const P = {
  radiation: <><circle cx="12" cy="12" r="2" /><path d="M12 4a8 8 0 0 1 6.9 4l-3.5 2A4 4 0 0 0 12 8z" /><path d="M5.1 8A8 8 0 0 1 12 4v4a4 4 0 0 0-3.4 2z" /><path d="M8.6 14l-3.5 2a8 8 0 0 0 13.8 0l-3.5-2a4 4 0 0 1-6.8 0z" /></>,
  plume: <><path d="M7 17a4 4 0 0 1 0-8 5 5 0 0 1 9.6-1.5A3.5 3.5 0 0 1 17 17z" /><path d="M4 21h3M9 21h3M15 21h3" /></>,
  virus: <><circle cx="12" cy="12" r="5" /><path d="M12 2v5M12 17v5M2 12h5M17 12h5M5 5l3.5 3.5M15.5 15.5L19 19M19 5l-3.5 3.5M8.5 15.5L5 19" /></>,
  power: <><path d="M9 2v6M15 2v6M6 8h12v3a6 6 0 0 1-12 0z" /><path d="M12 17v5" /></>,
  sun: <><circle cx="12" cy="12" r="4" /><path d="M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M19.1 4.9L17 7M7 17l-2.1 2.1" /></>,
  bolt: <path d="M13 2L4 14h7l-1 8 9-12h-7z" />,
  lock: <><rect x="5" y="11" width="14" height="10" rx="2" /><path d="M8 11V7a4 4 0 0 1 8 0v4" /></>,
  shield: <path d="M12 2l8 3v6c0 5-3.5 9-8 11-4.5-2-8-6-8-11V5z" />,
  fire: <path d="M12 22c-4 0-7-3-7-7 0-3 2-5 3-7 0 2 1 3 2 3 0-4 2-7 5-9 0 3 1 5 3 7s2 4 2 6c0 4-3 7-8 7z" />,
  coins: <><ellipse cx="9" cy="7" rx="6" ry="3" /><path d="M3 7v5c0 1.7 2.7 3 6 3s6-1.3 6-3V7" /><path d="M3 12v5c0 1.7 2.7 3 6 3s6-1.3 6-3v-5" /><path d="M15 10c3 .3 6 1.5 6 3v4c0 1.7-2.7 3-6 3" /></>,
  truck: <><path d="M1 6h13v10H1zM14 10h5l4 4v2h-9z" /><circle cx="5" cy="18" r="2" /><circle cx="18" cy="18" r="2" /></>,
  wave: <path d="M2 6c2-3 4-3 6 0s4 3 6 0 4-3 6 0M2 12c2-3 4-3 6 0s4 3 6 0 4-3 6 0M2 18c2-3 4-3 6 0s4 3 6 0 4-3 6 0" />,
  snowflake: <><path d="M12 2v20M2 12h20M5 5l14 14M19 5L5 19" /><path d="M12 2l-2 3M12 2l2 3M12 22l-2-3M12 22l2-3" /></>,
  thermometer: <><path d="M10 14V5a2 2 0 0 1 4 0v9a4 4 0 1 1-4 0z" /><path d="M12 9v6" /></>,
  volcano: <><path d="M9 8h6l6 13H3z" /><path d="M9 8c0-2 1-3 1-5M15 8c0-2-1-3-1-5M12 8V3" /></>,
  flask: <><path d="M9 2h6M10 2v6l-6 11a2 2 0 0 0 2 3h12a2 2 0 0 0 2-3l-6-11V2" /><path d="M7 15h10" /></>,
  wheat: <><path d="M12 22V8" /><path d="M12 8c-3 0-5-2-5-5 3 0 5 2 5 5zM12 12c-3 0-5-2-5-5 3 0 5 2 5 5zM12 16c-3 0-5-2-5-5 3 0 5 2 5 5zM12 8c3 0 5-2 5-5-3 0-5 2-5 5zM12 12c3 0 5-2 5-5-3 0-5 2-5 5zM12 16c3 0 5-2 5-5-3 0-5 2-5 5z" /></>,
  moon: <path d="M21 13A9 9 0 1 1 11 3a7 7 0 0 0 10 10z" />,
  alert: <><path d="M12 3l10 18H2z" /><path d="M12 10v5M12 18v.5" /></>,
  hammer: <><path d="M14 4l6 6-2 2-6-6z" /><path d="M12 6L4 14l-1 4 4-1 8-8" /></>,
  medical: <path d="M9 3h6v6h6v6h-6v6H9v-6H3V9h6z" />,
  map: <><path d="M9 4l6 2 6-2v14l-6 2-6-2-6 2V6z" /><path d="M9 4v14M15 6v14" /></>,
  library: <><path d="M4 3h5v18H4zM9 3h5v18H9z" /><path d="M14 5l5-1 3 17-5 1z" /></>,
  radio: <><rect x="3" y="8" width="18" height="12" rx="2" /><circle cx="8" cy="14" r="2.5" /><path d="M13 12h5M13 16h5M7 8l10-5" /></>,
  plan: <><rect x="5" y="4" width="14" height="17" rx="2" /><path d="M9 4V2h6v2M8 10h8M8 14h8M8 18h5" /></>,
  search: <><circle cx="10.5" cy="10.5" r="6.5" /><path d="M15.5 15.5L21 21" /></>,
  home: <><path d="M3 11l9-8 9 8" /><path d="M5 10v10h5v-6h4v6h5V10" /></>,
  back: <path d="M15 5l-7 7 7 7" />,
  forward: <path d="M9 5l7 7-7 7" />,
  settings: <><circle cx="12" cy="12" r="3" /><path d="M12 2v2M12 20v2M2 12h2M20 12h2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M19.1 4.9l-1.4 1.4M6.3 17.7l-1.4 1.4" /><circle cx="12" cy="12" r="7" /></>,
  ai: <><path d="M12 2l2 6 6 2-6 2-2 6-2-6-6-2 6-2z" /><path d="M19 15l1 3 3 1-3 1-1 3-1-3-3-1 3-1z" /></>,
  print: <><path d="M6 9V3h12v6" /><rect x="3" y="9" width="18" height="8" rx="2" /><path d="M6 14h12v7H6z" /></>,
  pin: <><path d="M12 22s7-7 7-12a7 7 0 1 0-14 0c0 5 7 12 7 12z" /><circle cx="12" cy="10" r="2.5" /></>,
  locate: <><circle cx="12" cy="12" r="7" /><circle cx="12" cy="12" r="2" /><path d="M12 2v3M12 19v3M2 12h3M19 12h3" /></>,
  layers: <><path d="M12 3l9 5-9 5-9-5z" /><path d="M3 13l9 5 9-5M3 17l9 5 9-5" /></>,
  measure: <><path d="M3 17L17 3l4 4L7 21z" /><path d="M7 13l2 2M10 10l2 2M13 7l2 2" /></>,
  share: <><circle cx="18" cy="5" r="3" /><circle cx="6" cy="12" r="3" /><circle cx="18" cy="19" r="3" /><path d="M8.6 13.5l6.8 4M15.4 6.5l-6.8 4" /></>,
  keyboard: <><rect x="2" y="6" width="20" height="12" rx="2" /><path d="M6 10h.01M10 10h.01M14 10h.01M18 10h.01M6 14h.01M18 14h.01M9 14h6" /></>,
  phone: <path d="M5 3h4l2 5-2.5 1.5a11 11 0 0 0 6 6L16 13l5 2v4a2 2 0 0 1-2 2A16 16 0 0 1 3 5a2 2 0 0 1 2-2z" />,
  drive: <><rect x="3" y="4" width="18" height="16" rx="2" /><path d="M3 14h18M7 17h.01M11 17h.01" /></>,
  check: <path d="M4 12l5 5L20 6" />,
  close: <path d="M6 6l12 12M18 6L6 18" />,
  plus: <path d="M12 5v14M5 12h14" />,
  minus: <path d="M5 12h14" />,
  external: <><path d="M14 4h6v6M20 4l-9 9" /><path d="M19 14v5a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2h5" /></>,
  book: <path d="M4 4h6a3 3 0 0 1 3 3v13a2 2 0 0 0-2-2H4zM20 4h-6a3 3 0 0 0-3 3v13a2 2 0 0 1 2-2h7z" />,
  pdf: <><path d="M6 2h8l6 6v14H6z" /><path d="M14 2v6h6M9 13h6M9 17h6" /></>,
  globe: <><circle cx="12" cy="12" r="9" /><path d="M3 12h18M12 3c3 3 3 15 0 18M12 3c-3 3-3 15 0 18" /></>,
  wifi: <><path d="M2 9c6-5 14-5 20 0M5 13c4-3.5 10-3.5 14 0M8.5 16.5c2-1.7 5-1.7 7 0" /><path d="M12 20h.01" /></>,
  help: <><circle cx="12" cy="12" r="9" /><path d="M9.5 9.5a2.5 2.5 0 1 1 3.5 2.3c-.7.3-1 .8-1 1.7M12 17h.01" /></>,
  heart: <path d="M12 21s-8-5.3-8-11a4.5 4.5 0 0 1 8-2.8A4.5 4.5 0 0 1 20 10c0 5.7-8 11-8 11z" />,
  speaker: <><path d="M4 9h4l5-4v14l-5-4H4z" /><path d="M16.5 9.5a3.5 3.5 0 0 1 0 5" /><path d="M19 6.5a7 7 0 0 1 0 11" /></>,
  drop: <path d="M12 2s6 7 6 12a6 6 0 0 1-12 0c0-5 6-12 6-12z" />,
  'text-size': <path d="M3 7h10M8 7v12M14 12h7M17.5 12v7" />,
  refresh: <><path d="M20.5 12a8.5 8.5 0 1 1-2.6-6.1" /><path d="M20.5 4v5h-5" /></>,
} satisfies Record<string, ReactNode>;

export type IconName = keyof typeof P;
export const ICON_NAMES = Object.keys(P) as IconName[];
export function isIconName(name: string): name is IconName {
  return Object.prototype.hasOwnProperty.call(P, name);
}

export function Icon({ name, size = 24, className }: { name: IconName | string; size?: number; className?: string }) {
  const body = isIconName(name) ? P[name] : P.help;
  return (
    <svg className={className ? `icon ${className}` : 'icon'} width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false">
      {body}
    </svg>
  );
}
