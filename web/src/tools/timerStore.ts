// Running timers live here, outside any screen, so they keep counting while someone reads a playbook.
import { useSyncExternalStore } from 'react';
import { notify } from '../components/Notice';
import { alarm } from './audio';
import { remainingSeconds, type RunningTimer } from './timers';

let timers: RunningTimer[] = [];
let listeners: (() => void)[] = [];
let ticker: number | null = null;
let seq = 1;

function emit() {
  listeners.forEach((l) => l());
}

function tick() {
  const now = Date.now();
  const done = timers.filter((t) => remainingSeconds(t, now) === 0);
  if (done.length) {
    timers = timers.filter((t) => !done.includes(t));
    alarm();
    done.forEach((t) => notify(`Timer finished: ${t.label}`));
  }
  emit();
  if (timers.length === 0 && ticker !== null) {
    window.clearInterval(ticker);
    ticker = null;
  }
}

export function startTimer(label: string, seconds: number): RunningTimer {
  const t: RunningTimer = { id: `t${seq++}`, label, seconds, endsAt: Date.now() + seconds * 1000 };
  timers = [...timers, t];
  if (ticker === null) ticker = window.setInterval(tick, 500);
  emit();
  return t;
}

export function cancelTimer(id: string): void {
  timers = timers.filter((t) => t.id !== id);
  emit();
}

export function resetTimers(): void {
  timers = [];
  if (ticker !== null) window.clearInterval(ticker);
  ticker = null;
  emit();
}

export function useTimers(): RunningTimer[] {
  return useSyncExternalStore((l) => {
    listeners = [...listeners, l];
    return () => { listeners = listeners.filter((x) => x !== l); };
  }, () => timers);
}
