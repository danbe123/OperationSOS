import type { PlaceGuidance, PlaceSection } from '../api/types';

/**
 * The four survival sections — what is usually here, when it is worth going, when to stay away and
 * how to go about it — drawn the same way wherever they are read. The docked hover panel builds them
 * as plain DOM (there is no React inside the map container) and the place card renders the same
 * structure through React; both take their class names, their icons and their words from this file,
 * so the two readings of the same four lists cannot drift apart.
 *
 * Each section is a band the eye can find in a second: a rule down its left edge in the section's own
 * tone, a small icon beside the heading, and bullets marked with a short rule rather than the
 * browser's disc. The tone is a colour in the field theme and a line style — solid, dashed, dotted —
 * in the black-and-white one, so none of it depends on colour to be read; both live in map.css.
 */

/** 16 px, `currentColor`, in the same stroke as the icon set in icons.tsx. */
export const SECTION_ICON_SIZE = 16;

/** The geometry only: the DOM side and the React side wrap it in the same <svg>. A box of things, a
 * tick, a warning triangle and a compass — what is here, when to come, when not to, and which way. */
export const SECTION_ICON_PATHS: Record<PlaceSection['id'], string> = {
  have: '<path d="M3 7.5l9-4.5 9 4.5v9l-9 4.5-9-4.5z" /><path d="M3 7.5l9 4.5 9-4.5M12 12v9" />',
  useful: '<path d="M4 12.5l5 5L20 6.5" />',
  avoid: '<path d="M12 3.5l9.5 17h-19z" /><path d="M12 10v4M12 17.5v.5" />',
  approach: '<circle cx="12" cy="12" r="9" /><path d="M15.5 8.5l-2 5-5 2 2-5z" />',
};

/** The same wrapper the React `Icon` draws, as a string, because the panel is plain DOM. */
function iconSvg(body: string, size: number): string {
  return `<svg class="map-tip-icon" width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">${body}</svg>`;
}

/** The `book` icon from icons.tsx, for the panel's foot; the card renders the React one beside it. */
const GUIDE_ICON = '<path d="M4 4h6a3 3 0 0 1 3 3v13a2 2 0 0 0-2-2H4zM20 4h-6a3 3 0 0 0-3 3v13a2 2 0 0 1 2-2h7z" />';

export function sectionIconSvg(id: PlaceSection['id']): string {
  return iconSvg(SECTION_ICON_PATHS[id], SECTION_ICON_SIZE);
}

/** `map-tip-section map-tip-section-have`: the band every section wears, then the one that says
 * which section it is — the tone, the rule style and the icon colour hang off the second. */
export function sectionClassName(id: PlaceSection['id']): string {
  return `map-tip-section map-tip-section-${id}`;
}

/** The foot of both the panel and the card, named for the guide it opens rather than labelled
 * "Guide:": somebody reading in a bad moment should be able to see what tapping it does. */
export function guideLinkLabel(guidance: PlaceGuidance): string {
  return `Open the ${guidance.link.title} guide`;
}

/** One section as DOM, for the panel. The heading is an h4 there and an h3 on the card, because the
 * card's other sections are h3s and a heading level is an outline, not a size. */
export function buildSection(part: PlaceSection, headingTag: 'h3' | 'h4' = 'h4'): HTMLElement {
  const section = document.createElement('section');
  section.className = sectionClassName(part.id);
  const heading = document.createElement(headingTag);
  heading.className = 'map-tip-section-head';
  heading.insertAdjacentHTML('beforeend', sectionIconSvg(part.id));
  const text = document.createElement('span');
  text.textContent = part.title;
  heading.appendChild(text);
  section.appendChild(heading);
  // The box's own rendered guidance, so its markup is markup — unlike the feature's own OSM values,
  // which are text nodes wherever they are written out.
  section.insertAdjacentHTML('beforeend', part.html);
  return section;
}

/** The guide link at the foot of the panel: an in-app href, which the dock's click handler sends
 * through the router rather than reloading the whole box on a dead network. */
export function buildGuideLink(guidance: PlaceGuidance): HTMLAnchorElement {
  const link = document.createElement('a');
  link.className = 'btn map-tip-guide';
  link.setAttribute('href', guidance.link.href);
  link.insertAdjacentHTML('beforeend', iconSvg(GUIDE_ICON, 18));
  const label = document.createElement('span');
  label.textContent = guideLinkLabel(guidance);
  link.appendChild(label);
  return link;
}
