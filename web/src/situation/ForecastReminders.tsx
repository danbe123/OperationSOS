import { useEffect, useRef } from 'react';
import { notify } from '../components/Notice';
import { alarm } from '../tools/audio';
import { dueNow, pendingIds, readSeen, reminderKey, reminderText, writeSeen } from './reminders';
import { useSituation } from './SituationProvider';

/** Mounted once for the whole app: when a countdown runs out while the box is open, it says so on
 * whatever screen is showing and makes the timer's noise. Whatever was already past when the app
 * opened is taken as read, so nobody is greeted by a week of old alarms. */
export function ForecastReminders() {
  const { view } = useSituation();
  const primed = useRef(false);
  // Countdowns this screen has watched run: only those earn a toast and the noise when they fall due.
  const pending = useRef(new Set<string>());

  useEffect(() => {
    if (!view) return;
    const now = Date.parse(view.meta.now) || Date.now();
    const seen = readSeen(localStorage);
    const first = !primed.current;
    primed.current = true;
    // The first view takes everything already past as read; after that only a watched countdown counts.
    const due = first ? dueNow(view, seen, now) : dueNow(view, seen, now, pending.current);
    if (due.length > 0) writeSeen(localStorage, [...seen, ...due.map(reminderKey)]);
    for (const id of pendingIds(view, now)) pending.current.add(id);
    if (first || due.length === 0) return;
    for (const item of due) notify(reminderText(item));
    alarm();
  }, [view]);

  return null;
}
