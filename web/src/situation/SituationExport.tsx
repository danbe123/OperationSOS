import { useState } from 'react';
import { api } from '../api/client';
import { errorMessage } from '../api/useQuery';
import { QrCode } from '../components/QrCode';
import { Icon } from '../icons';
import type { ExportChunks, ImportSummary } from '../api/types';

/** "notes: 2 added, 1 kept" — the box's own counts, read out in its own words. */
export function countLines(summary: ImportSummary): string[] {
  return Object.entries(summary.counts ?? {}).map(([what, how]) => {
    const parts = Object.entries(how ?? {}).filter(([, n]) => n > 0).map(([verb, n]) => `${n} ${verb}`);
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

/** The box's own words for a refused import are written for whoever wrote the transfer format, and
 * the first one on this list is what a household actually meets: paste anything that is not a code
 * and the screen used to answer `a scanned chunk is not a QR chunk: expected {"i", "n", "d"}`. Say
 * what to do instead, and keep the box's own sentence underneath for the ones nothing here covers. */
const TROUBLE: { when: RegExp; say: string }[] = [
  { when: /not a QR chunk|not a situation export|do not decode/i,
    say: 'That is not one of this box\u2019s codes. Type the line printed under the code, starting with {' },
  { when: /missing/i, say: 'The box has not got all the codes yet. Type the text of each one, one per line, in order.' },
  { when: /two different exports/i, say: 'Those codes came from two different sets. Make the codes again on the other box and use one set.' },
  { when: /no chunks were given|nothing to bring in/i, say: 'There is nothing to bring in yet. Type or paste the text of a code first.' },
];

/** A refusal in household words, with the box's own sentence kept for anything not on the list. */
export function importTrouble(raw: string): { say: string; detail?: string } {
  const known = TROUBLE.find((t) => t.when.test(raw));
  return known ? { say: known.say, detail: raw } : { say: raw };
}

/** How far the reader has got. Every code says which one it is and how many there are, so the box
 * can count them as they are typed in rather than leaving a household to guess whether the paste
 * that is 800 characters long was the whole of it. */
export function importProgress(text: string): string | null {
  const seen = new Set<number>();
  let total = 0;
  for (const line of text.split(/\r?\n/)) {
    let parsed: unknown;
    try {
      parsed = JSON.parse(line.trim());
    } catch {
      continue;
    }
    const code = parsed as { i?: unknown; n?: unknown; d?: unknown } | null;
    if (typeof code?.i !== 'number' || typeof code.n !== 'number' || typeof code.d !== 'string') continue;
    seen.add(code.i);
    total = Math.max(total, code.n);
  }
  if (total === 0 || seen.size === 0) return null;
  if (seen.size >= total) return total === 1 ? 'That is the only code. Bring it in.' : `All ${total} codes read. Bring it in.`;
  return `Code ${seen.size} of ${total} read. Type the next one on a new line.`;
}

/** Carrying the household's situation between boxes without a network: the box turns it into a set of
 * codes, and takes the text of the same codes back in on the other side. Nothing here scans or
 * photographs anything — there is no camera in the box — so the words say typing and pasting. */
export function SituationExport() {
  const [chunks, setChunks] = useState<ExportChunks | null>(null);
  const [at, setAt] = useState(0);
  const [showText, setShowText] = useState(false);
  const [busy, setBusy] = useState(false);
  // Two troubles, told in two places. Making the codes fails beside the button that makes them;
  // bringing one in fails under the button that brings it in — which on a 480 px kiosk is the only
  // place the person who pressed it can see, the old single line being some 500 px up the screen.
  const [madeTrouble, setMadeTrouble] = useState<string | null>(null);
  const [broughtTrouble, setBroughtTrouble] = useState<{ say: string; detail?: string } | null>(null);
  const [payload, setPayload] = useState('');
  const [summary, setSummary] = useState<ImportSummary | null>(null);

  const load = async () => {
    setBusy(true);
    setMadeTrouble(null);
    try {
      const got = await api.exportChunks();
      setChunks(got);
      setAt(0);
    } catch (e) {
      setMadeTrouble(errorMessage(e));
    } finally {
      setBusy(false);
    }
  };

  const bringIn = async () => {
    setBusy(true);
    setBroughtTrouble(null);
    setSummary(null);
    try {
      setSummary(await api.importSituation(parseImport(payload)));
    } catch (e) {
      setBroughtTrouble(importTrouble(errorMessage(e)));
    } finally {
      setBusy(false);
    }
  };

  const total = chunks?.total ?? chunks?.chunks.length ?? 0;
  const current = chunks?.chunks[at] ?? null;
  const progress = importProgress(payload);

  return (
    <section className="panel" id="carry" aria-label="Carry it to another box">
      <h2>Carry it to another box</h2>
      <p className="muted">No network needed. The box turns this situation into a set of codes. On the other
        box, type or paste each code&rsquo;s text in order, and it says when it has them all.</p>

      <div className="row">
        <button type="button" className="btn" disabled={busy} onClick={() => void load()}>
          <Icon name="share" size={18} /><span>{chunks ? 'Make the codes again' : 'Export as codes'}</span>
        </button>
        {chunks && (
          <button type="button" className="btn btn-small" onClick={() => setShowText((v) => !v)} aria-expanded={showText}>
            {showText ? 'Hide the text' : 'Copy the codes as text'}
          </button>
        )}
      </div>
      {madeTrouble && <p className="warning">{madeTrouble}</p>}

      {chunks && total > 0 && (
        <div className="export-codes" role="group" aria-label="Situation codes">
          <p className="muted" role="status">Code {at + 1} of {total}. Work through them in order; the other box says how many it has.</p>
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
              <span>Code {at + 1} of {total}, as text</span>
              <textarea aria-label={`Situation code ${at + 1} as text`} readOnly rows={4} value={current ?? ''} onFocus={(e) => e.target.select()} />
            </label>
          )}
        </div>
      )}
      {chunks && total === 0 && <p className="muted">There is nothing to carry yet.</p>}

      <h3>Bring one in</h3>
      <label className="field">
        <span>The text of each code, one per line, in order</span>
        <textarea aria-label="Situation to bring in" rows={4} value={payload} onChange={(e) => setPayload(e.target.value)} placeholder={'{"i":0,"n":3,"d":"H4sIAAAA…'} />
      </label>
      {progress && <p className="muted" role="status">{progress}</p>}
      <div className="row">
        {/* Bringing a situation in is not adding a row to a list, and the "+" said it was. */}
        <button type="button" className="btn btn-primary" disabled={busy || !payload.trim()} onClick={() => void bringIn()}>
          Bring it in
        </button>
      </div>
      {broughtTrouble && (
        <p className="warning cond-trouble" role="alert">
          {broughtTrouble.say}
          {broughtTrouble.detail && <span className="muted"> The box said: {broughtTrouble.detail}</span>}
        </p>
      )}
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
