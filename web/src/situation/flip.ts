import { api, ApiError } from '../api/client';
import type { ConditionId, ConditionState } from '../api/types';

/** A tap on a service says "this is off" or "this is back". The request carries the timestamp the screen
 * last read so two devices cannot silently overwrite each other; when the box answers that the row moved
 * on since (another device, a sensor, or the screen's own last tap still settling), the tap is re-read
 * against what the box has now and sent once more. A tap that finds the service already in the state
 * it meant is simply done: nobody should see an alert for a race they did not cause. */
export async function flipCondition(id: ConditionId, current: { state: ConditionState; updated_at: string | null }): Promise<'changed' | 'already'> {
  const next: ConditionState = current.state === 'working' ? 'off' : 'working';
  const since = new Date().toISOString();
  try {
    await api.setCondition(id, { state: next, since, expected_updated_at: current.updated_at ?? undefined });
    return 'changed';
  } catch (e) {
    if (!(e instanceof ApiError) || e.status !== 409) throw e;
    const fresh = (await api.situationView()).conditions[id];
    if (fresh.state === next) return 'already';
    await api.setCondition(id, { state: next, since, expected_updated_at: fresh.updated_at ?? undefined });
    return 'changed';
  }
}
