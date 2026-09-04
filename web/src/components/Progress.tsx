export function Progress({ label, value }: { label: string; value?: number }) {
  const pct = value === undefined ? undefined : Math.max(0, Math.min(100, Math.round(value)));
  return (
    <div className="progress" role="progressbar" aria-label={label} aria-valuemin={0} aria-valuemax={100} aria-valuenow={pct}>
      <span>{label}{pct !== undefined ? ` ${pct}%` : ''}</span>
      <div className={pct === undefined ? 'progress-bar indeterminate' : 'progress-bar'}>
        <span style={pct === undefined ? undefined : { width: `${pct}%` }} />
      </div>
    </div>
  );
}
