import { useEffect, useRef } from 'react';
import { notify } from '../components/Notice';
import { alarm } from '../tools/audio';
import { dueNow, readSeen, reminderKey, reminderText, writeSeen } from './reminders';
import { useSituation } from './SituationProvider';

/** Mounted once for the whole app: when a countdown runs out while the box is open, it says so on
 * whatever screen is showing and makes the timer's noise. Whatever was already past when the app
 * opened is taken as read, so nobody is greeted by a week of old alarms. */
export function ForecastReminders() {
  const { view } = useSituation();
  const primed = useRef(false);

  useEffect(() => {
    if (!view) return;
    const seen = readSeen(localStorage);
    const due = dueNow(view, seen, Date.parse(view.meta.now) || Date.now());
    if (due.length > 0) writeSeen(localStorage, [...seen, ...due.map(reminderKey)]);
    const first = !primed.current;
    primed.current = true;
    if (first || due.length === 0) return;
    for (const item of due) notify(reminderText(item));
    alarm();
  }, [view]);

  return null;
}
