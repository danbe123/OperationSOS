import { useEffect, useMemo, useReducer, useRef, useState, type FormEvent, type ReactNode } from 'react';
import { Link } from 'react-router';
import { api } from '../api/client';
import { useStatus } from '../api/status';
import type { AiAskRequest, AiEvent, Passage } from '../api/types';
import { errorMessage } from '../api/useQuery';
import { AppBar } from '../components/AppBar';
import { Progress } from '../components/Progress';
import { Icon } from '../icons';
import { useAppLink } from '../links';

export const MAX_QUESTION = 400;
export const MAX_TURNS = 4;
export const WARNING_LINE = 'AI can be wrong. The library pages linked below are the source of truth.';

type Verbatim = Extract<AiEvent, { event: 'verbatim' }>['data'];
type Done = Extract<AiEvent, { event: 'done' }>['data'];
type AiError = Extract<AiEvent, { event: 'error' }>['data'];
type Phase = 'searching' | 'thinking' | 'answering' | 'done' | 'error';
type Turn = { id: number; question: string; verbatim: Verbatim | null; passages: Passage[]; answer: string; phase: Phase; done: Done | null; error: AiError | null; startedAt: number; firstTokenAt: number | null };

function errorText(e: AiError): string {
  switch (e.code) {
    case 'busy': return `The AI is answering another question. Try again in ${e.retry_after ?? 30} s.`;
    case 'timeout': return 'The AI took too long (3 minutes) and gave up. Ask a shorter question.';
    case 'unavailable': return `The AI is not available: ${e.message}`;
    case 'internal': return `The AI hit a problem: ${e.message}`;
  }
}

function ContentLink({ href, children }: { href: string; children: ReactNode }) {
  const follow = useAppLink();
  return <a href={href} onClick={(e) => { if (follow(href)) e.preventDefault(); }}>{children}</a>;
}

function TurnView({ turn, now }: { turn: Turn; now: number }) {
  const elapsed = Math.round(((turn.phase === 'done' || turn.phase === 'error' ? (turn.firstTokenAt ?? now) : now) - turn.startedAt) / 1000);
  return (
    <article className="turn">
      <p className="question"><strong>You:</strong> {turn.question}</p>
      {turn.verbatim && (
        <section className="verbatim" role="region" aria-label="From the library, word for word">
          <p className="verbatim-head"><Icon name="book" /> From the library, word for word: <ContentLink href={turn.verbatim.url}>{turn.verbatim.title}</ContentLink>{turn.verbatim.as_at && <span className="muted"> (as at {turn.verbatim.as_at})</span>}</p>
          {turn.verbatim.paragraphs.map((p, i) => <p key={i}>{p}</p>)}
        </section>
      )}
      {turn.phase === 'searching' && <p className="muted">Searching the library…</p>}
      {turn.phase === 'thinking' && <Progress label={`Reading ${turn.passages.length} passages and processing the prompt (about a minute on the box, ${elapsed} s so far)`} />}
      {turn.phase === 'answering' && <Progress label="Answering" />}
      {(turn.phase === 'answering' || turn.phase === 'done') && turn.answer && <p className="answer">{turn.answer}</p>}
      {turn.phase === 'done' && turn.done && (
        turn.done.grounded ? (
          turn.done.citations.length > 0 && (
            <ul className="list citations" aria-label="Sources">
              {turn.done.citations.map((c) => (
                <li key={c.n}><ContentLink href={c.url}>[{c.n}] {c.title} ({c.source})</ContentLink></li>
              ))}
            </ul>
          )
        ) : (
          <>
            <p className="warning">This answer is not backed by a library passage.</p>
            {turn.passages.length > 0 && (
              <ul className="list passages" aria-label="Passages found">
                {turn.passages.map((p) => (
                  <li key={p.n}><ContentLink href={p.url}>[{p.n}] {p.title} ({p.source})</ContentLink><p className="muted">{p.text}</p></li>
                ))}
              </ul>
            )}
          </>
        )
      )}
      {turn.phase === 'error' && turn.error && <p className="warning">{errorText(turn.error)}</p>}
    </article>
  );
}

export function Ai() {
  const { status } = useStatus();
  const [question, setQuestion] = useState('');
  const [turns, setTurns] = useState<Turn[]>([]);
  const [, tick] = useReducer((n: number) => n + 1, 0);
  const nextId = useRef(1);
  const busy = turns.some((t) => t.phase !== 'done' && t.phase !== 'error');

  useEffect(() => {
    if (!busy) return;
    const id = window.setInterval(tick, 1000);
    return () => window.clearInterval(id);
  }, [busy]);

  const history = useMemo<AiAskRequest['history']>(
    () => turns.filter((t) => t.phase === 'done' && t.done).slice(-MAX_TURNS).flatMap((t) => [
      { role: 'user' as const, content: t.question },
      { role: 'assistant' as const, content: t.done!.answer },
    ]),
    [turns],
  );

  const ask = async (e: FormEvent) => {
    e.preventDefault();
    const q = question.trim().slice(0, MAX_QUESTION);
    if (!q || busy) return;
    const id = nextId.current++;
    const patch = (fn: (t: Turn) => Turn) => setTurns((ts) => ts.map((t) => (t.id === id ? fn(t) : t)));
    setTurns((ts) => [...ts, { id, question: q, verbatim: null, passages: [], answer: '', phase: 'searching', done: null, error: null, startedAt: Date.now(), firstTokenAt: null }]);
    setQuestion('');
    try {
      for await (const ev of api.askAi({ question: q, history })) {
        switch (ev.event) {
          case 'verbatim': patch((t) => ({ ...t, verbatim: ev.data })); break;
          case 'retrieving': patch((t) => ({ ...t, passages: ev.data.passages, phase: 'thinking' })); break;
          case 'token': patch((t) => ({ ...t, answer: t.answer + ev.data.text, phase: 'answering', firstTokenAt: t.firstTokenAt ?? Date.now() })); break;
          case 'done': patch((t) => ({ ...t, answer: ev.data.answer, done: ev.data, phase: 'done' })); break;
          case 'error': patch((t) => ({ ...t, error: ev.data, phase: 'error' })); break;
        }
      }
      patch((t) => (t.phase === 'done' || t.phase === 'error' ? t : { ...t, phase: 'error', error: { code: 'internal', message: 'the stream ended early' } }));
    } catch (err) {
      patch((t) => ({ ...t, phase: 'error', error: { code: 'unavailable', message: errorMessage(err) } }));
    }
  };

  if (!status) return <div className="screen"><AppBar title="AI assistant" /><p className="pad muted">Checking the box…</p></div>;
  const ai = status.ai;
  if (ai.state !== 'ready') {
    return (
      <div className="screen">
        <AppBar title="AI assistant" />
        <div className="pad stack ai-off">
          {ai.state === 'off' && <p>The assistant is off. It answers only from the library and needs about 3.5 GB of memory while on.</p>}
          {ai.state === 'starting' && <p>The assistant is starting (about a minute).</p>}
          {ai.state === 'busy' && <p>The assistant is answering another question. Try again shortly.</p>}
          {ai.state === 'off-thermal' && <p className="warning">The assistant switched off because the box got too hot. Let it cool, then turn it on again.</p>}
          {ai.state === 'error' && <p className="warning">The assistant failed to start.</p>}
          {ai.message && <p className="muted">{ai.message}</p>}
          <Link className="btn btn-primary" to="/system"><Icon name="settings" /><span>Turn it on in System</span></Link>
        </div>
      </div>
    );
  }

  return (
    <div className="screen ai">
      <AppBar title="AI assistant" />
      <p className="pad warning">{WARNING_LINE}</p>
      <div className="turns">
        {turns.map((t) => <TurnView key={t.id} turn={t} now={Date.now()} />)}
      </div>
      <form className="ask pad no-print" onSubmit={(e) => void ask(e)}>
        <input type="text" aria-label="Your question" placeholder="Ask about anything in the library" value={question} onChange={(e) => setQuestion(e.target.value)} maxLength={MAX_QUESTION} disabled={busy} enterKeyHint="send" autoComplete="off" />
        <button type="submit" className="btn btn-primary" disabled={busy || !question.trim()}><Icon name="ai" /><span>Ask</span></button>
        <span className="muted count">{question.length}/{MAX_QUESTION}</span>
      </form>
    </div>
  );
}
