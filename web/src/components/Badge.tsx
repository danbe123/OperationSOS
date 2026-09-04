import type { ReactNode } from 'react';

export function Badge({ children, tone = 'default' }: { children: ReactNode; tone?: 'default' | 'warn' | 'danger' | 'ok' }) {
  return <span className={tone === 'default' ? 'badge' : `badge badge-${tone}`}>{children}</span>;
}
