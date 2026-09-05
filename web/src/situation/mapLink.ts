/** The overlay a scenario wants drawn the moment the map is reached for. */
export const SCENARIO_OVERLAYS: Record<string, string> = { 'storms-flooding': 'flood-zones' };

/** Where "Open the map" goes for a scenario: the map, with that scenario's overlay already on. */
export function scenarioMapHref(slug: string | null | undefined): string {
  const overlay = slug ? SCENARIO_OVERLAYS[slug] : undefined;
  return overlay ? `/map?overlay=${overlay}` : '/map';
}
