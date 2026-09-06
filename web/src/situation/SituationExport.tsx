import { useState } from 'react';
import { api } from '../api/client';
import { errorMessage } from '../api/useQuery';
import { QrCode } from '../components/QrCode';
import { Icon } from '../icons';
import type { ExportChunks, ImportSummary } from '../api/types';

/** "household: 2 added, 1 kept" — the box's own counts, read out in its own words. */
export function countLines(summary: ImportSummary): string[] {
  return Object.entries(summary.counts ?? {}).map(([what, how]) => {
    const parts = Object.entries(how).filter(([, n]) => n > 0).map(([verb, n]) => `${n} ${verb}`);
    return `${what}: ${parts.length ? parts.join(', ') : 'nothing to do'}`;
  });
}

/** What the reader pasted: the export document itself, or the chunk strings one per line, in any
 * order. Anything that is not JSON is sent as the list of lines and the box decides. */
export function parseImport(text: string): unknown {
  const trimmed = text.trim();
  try {
    return JSON.parse(trimmed) as unknown;
  } catch {
    const lines = trimmed.split(/\r?\n/).map((l) => l.trim()).filter(Boolean);
    return lines.length === 1 ? [lines[0]] : lines;
  }
}

/** Carrying the household's situation between boxes without a network: the box turns it into a row of
 * QR codes to photograph one at a time, and takes the same text back in from another box. */
export function SituationExport() {
  const [chunks, setChunks] = useState<ExportChunks | null>(null);
  const [at, setAt] = useState(0);
  const [showText, setShowText] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [payload, setPayload] = useState('');
  const [summary, setSummary] = useState<ImportSummary | null>(null);

  const load = async () => {
    setBusy(true);
    setError(null);
    try {
      const got = await api.exportChunks();
      setChunks(got);
      setAt(0);
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  };

  const bringIn = async () => {
    setBusy(true);
    setError(null);
    setSummary(null);
    try {
      setSummary(await api.importSituation(parseImport(payload)));
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  };

  const total = chunks?.total ?? chunks?.chunks.length ?? 0;
  const current = chunks?.chunks[at] ?? null;

  return (
    <section className="panel" id="carry" aria-label="Carry the situation">
      <h2>Carry it to another box</h2>
      <p className="muted">No network needed. The box turns the situation into a set of codes to photograph
        in order, and reads the same set back in on the other side.</p>

      <div className="row">
        <button type="button" className="btn" disabled={busy} onClick={() => void load()}>
          <Icon name="share" size={18} /><span>{chunks ? 'Make the codes again' : 'Export as codes'}</span>
        </button>
        {chunks && (
          <button type="button" className="btn btn-small" onClick={() => setShowText((v) => !v)} aria-expanded={showText}>
            {showText ? 'Hide the text' : 'Copy as text instead'}
          </button>
        )}
      </div>
      {error && <p className="warning">{error}</p>}

      {chunks && total > 0 && (
        <div className="export-codes" role="group" aria-label="Situation codes">
          <p className="muted" role="status">Code {at + 1} of {total}. Scan them in order; the other box asks for the next one.</p>
          {current && <QrCode text={current} size={260} label={`Situation code ${at + 1} of ${total}`} />}
          <div className="row">
            <button type="button" className="btn" disabled={at === 0} onClick={() => setAt((n) => Math.max(0, n - 1))}>
              <Icon name="back" size={18} /><span>Previous</span>
            </button>
            <button type="button" className="btn" disabled={at >= total - 1} onClick={() => setAt((n) => Math.min(total - 1, n + 1))}>
              <span>Next</span><Icon name="forward" size={18} />
            </button>
          </div>
          {showText && (
            <label className="field">
              <span>Chunk {at + 1} of {total}, as text</span>
              <textarea aria-label={`Situation code ${at + 1} as text`} readOnly rows={4} value={current ?? ''} onFocus={(e) => e.target.select()} />
            </label>
          )}
        </div>
      )}
      {chunks && total === 0 && <p className="muted">There is nothing to carry yet.</p>}

      <h3>Bring one in</h3>
      <label className="field">
        <span>Paste the JSON, or the text of each code in order</span>
        <textarea aria-label="Situation to bring in" rows={4} value={payload} onChange={(e) => setPayload(e.target.value)} placeholder={'{"i":0,"n":2,"d":"…"}'} />
      </label>
      <div className="row">
        <button type="button" className="btn btn-primary" disabled={busy || !payload.trim()} onClick={() => void bringIn()}>
          <Icon name="plus" size={18} /><span>Bring it in</span>
        </button>
      </div>
      {summary && (
        <div className="panel panel-signal" role="status" aria-label="What came in">
          <p><strong>{summary.ok === false ? 'Nothing was brought in.' : 'Brought in from the other box.'}</strong>
            {summary.exported_at && <span className="muted"> Written {summary.exported_at}.</span>}</p>
          {countLines(summary).length > 0 && (
            <ul className="list">{countLines(summary).map((line) => <li key={line}>{line}</li>)}</ul>
          )}
          {(summary.home || summary.scenario) && (
            <p className="muted">{[summary.home && `Home ${summary.home}`, summary.scenario && `Situation ${summary.scenario}`].filter(Boolean).join(' · ')}.</p>
          )}
          {summary.changes && summary.changes.length > 0 && (
            <>
              <h3>What changed</h3>
              <ul className="list">{summary.changes.map((c) => <li key={c}>{c}</li>)}</ul>
            </>
          )}
        </div>
      )}
    </section>
  );
}
