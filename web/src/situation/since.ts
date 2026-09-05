/** The since picker: four sensible answers to "when did this start?" plus a typed-in time. */
export type SinceChoice = 'now' | 'hour' | 'morning' | 'yesterday' | 'custom';

export const SINCE_OPTIONS: { value: SinceChoice; label: string }[] = [
  { value: 'now', label: 'Just now' },
  { value: 'hour', label: '1 hour ago' },
  { value: 'morning', label: 'This morning (07:00)' },
  { value: 'yesterday', label: 'Yesterday, this time' },
  { value: 'custom', label: 'Choose a time…' },
];

/** Turn a choice into an instant. `custom` is a datetime-local value, read in the box's own time zone. */
export function sinceIso(choice: SinceChoice, custom = '', now: number = Date.now()): string | undefined {
  const at = new Date(now);
  switch (choice) {
    case 'now':
      return at.toISOString();
    case 'hour':
      return new Date(now - 3_600_000).toISOString();
    case 'morning': {
      const morning = new Date(at.getFullYear(), at.getMonth(), at.getDate(), 7, 0, 0, 0);
      // before 07:00 the morning has not happened yet: mean yesterday morning
      if (morning.getTime() > now) morning.setDate(morning.getDate() - 1);
      return morning.toISOString();
    }
    case 'yesterday':
      return new Date(now - 86_400_000).toISOString();
    case 'custom': {
      const t = Date.parse(custom);
      return Number.isNaN(t) ? undefined : new Date(t).toISOString();
    }
  }
}
