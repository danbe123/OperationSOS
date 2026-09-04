import type { ReactNode } from 'react';

export function Section({ title, id, open, children }: { title: string; id?: string; open?: boolean; children: ReactNode }) {
  return (
    <details className="section" id={id} open={open}>
      <summary>{title}</summary>
      {children}
    </details>
  );
}
