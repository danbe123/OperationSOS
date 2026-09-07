import { describe, it, expect } from 'vitest';
import { chipIcon } from '../../src/map/LayerChips';
import { isIconName } from '../../src/icons';

describe('chipIcon', () => {
  it('uses this app\'s own icon for an overlay it knows, whatever the manifest asked for', () => {
    expect(chipIcon('airports', 'airport')).toBe('plane');
    expect(chipIcon('health', null)).toBe('medical');
  });
  it('falls back to the manifest icon only when the box has one drawn by that name', () => {
    expect(chipIcon('rest-centres', 'bed')).toBe('bed');
    // `airport` is a category, not an icon: the manifest can name one that was never drawn, and a chip
    // is no place for the question mark `Icon` puts up for a name it does not know.
    expect(isIconName('airport')).toBe(false);
    expect(chipIcon('rest-centres', 'airport')).toBe('layers');
    expect(chipIcon('rest-centres', null)).toBe('layers');
  });
});
