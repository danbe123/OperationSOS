import type { PlaceGuidance, PlaceSection } from '../api/types';

/**
 * The four survival sections — what is usually here, when it is worth going, when to stay away and
 * how to go about it — as the place card draws them. The hover label says only the name, the type
 * and "Click for more", so this is now one reading rather than two; the class names, the icons and
 * the words still live here so the card's markup and the CSS that bands it cannot drift apart.
 *
 * Each section is a band the eye can find in a second: a rule down its left edge in the section's own
 * tone, a small icon beside the heading, and bullets marked with a short rule rather than the
 * browser's disc. The tone is a colour in the field theme and a line style — solid, dashed, dotted —
 * in the black-and-white one, so none of it depends on colour to be read; both live in map.css.
 */

/** 16 px, `currentColor`, in the same stroke as the icon set in icons.tsx. */
export const SECTION_ICON_SIZE = 16;

/** The geometry only: the card wraps it in the same <svg> the React `Icon` draws. A box of things, a
 * tick, a warning triangle and a compass — what is here, when to come, when not to, and which way. */
export const SECTION_ICON_PATHS: Record<PlaceSection['id'], string> = {
  have: '<path d="M3 7.5l9-4.5 9 4.5v9l-9 4.5-9-4.5z" /><path d="M3 7.5l9 4.5 9-4.5M12 12v9" />',
  useful: '<path d="M4 12.5l5 5L20 6.5" />',
  avoid: '<path d="M12 3.5l9.5 17h-19z" /><path d="M12 10v4M12 17.5v.5" />',
  approach: '<circle cx="12" cy="12" r="9" /><path d="M15.5 8.5l-2 5-5 2 2-5z" />',
};

/** `map-tip-section map-tip-section-have`: the band every section wears, then the one that says
 * which section it is — the tone, the rule style and the icon colour hang off the second. */
export function sectionClassName(id: PlaceSection['id']): string {
  return `map-tip-section map-tip-section-${id}`;
}

/** The foot of the card, named for the guide it opens rather than labelled "Guide:": somebody
 * reading in a bad moment should be able to see what tapping it does. */
export function guideLinkLabel(guidance: PlaceGuidance): string {
  return `Open the ${guidance.link.title} guide`;
}
