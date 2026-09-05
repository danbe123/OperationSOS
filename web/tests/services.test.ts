import { describe, it, expect } from 'vitest';
import { offServices, tagPhoneNumbers, ALL_ON } from '../src/services';

describe('services', () => {
  it('lists what is off in a fixed order', () => {
    expect(offServices(ALL_ON)).toEqual([]);
    expect(offServices({ ...ALL_ON, phones: false, power: false })).toEqual(['power', 'phones']);
    expect(offServices(null)).toEqual([]);
  });
  it('tags emergency numbers in text nodes only, once each, leaving links and code alone', () => {
    const root = document.createElement('div');
    root.innerHTML = '<p>If the street is dark, call <strong>105</strong> or 999. Ring 0800 999 999 for gas.</p><p><a href="/p/uk-numbers">999 and 111</a> <code>999</code></p>';
    expect(tagPhoneNumbers(root)).toBe(2);
    const tags = root.querySelectorAll('.no-phone');
    expect(tags).toHaveLength(2);
    expect(tags[0].textContent).toBe('105 phones down');
    expect(tags[1].querySelector('a')?.getAttribute('href')).toBe('/p/no-phones');
    expect(root.querySelector('a[href="/p/uk-numbers"]')?.querySelector('.no-phone')).toBeNull();
    expect(root.querySelector('code')?.textContent).toBe('999');
    expect(tagPhoneNumbers(root)).toBe(0);    // idempotent
  });
});
