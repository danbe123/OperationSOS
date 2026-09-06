import { describe, it, expect, vi } from 'vitest';
import { screen, within } from '@testing-library/react';
import { renderRoute } from '../render';
import { api, ApiError } from '../../src/api/client';
import { readingText, readingTone, sensorTitle } from '../../src/situation/sensors';
import { makeView, playbooks, powerOffView, sensors, view } from '../fixtures/api';

describe('sensor readings in words', () => {
  it('reads flags as yes or no and quantities with their unit', () => {
    expect(readingText({ value: 1, unit: 'up', at: '' })).toBe('up');
    expect(readingText({ value: 0, unit: 'up', at: '' })).toBe('down');
    expect(readingText({ value: 0, unit: 'on', at: '' })).toBe('off');
    expect(readingText({ value: 14.53, unit: '°C', at: '' })).toBe('14.5 °C');
    expect(readingText({ value: 3, unit: 'ppm', at: '' })).toBe('3 ppm');
  });

  it('marks a reading that says something is wrong', () => {
    expect(readingTone('internet', { value: 0, unit: 'up', at: '' })).toBe('danger');
    expect(readingTone('internet', { value: 1, unit: 'up', at: '' })).toBe('ok');
    expect(readingTone('co_ppm', { value: 60, unit: 'ppm', at: '' })).toBe('danger');
    expect(readingTone('co_ppm', { value: 12, unit: 'ppm', at: '' })).toBe('warn');
    expect(readingTone('temp_in', { value: 12, unit: '°C', at: '' })).toBe('warn');
    expect(readingTone('pressure_hpa', { value: 1012, unit: 'hPa', at: '' })).toBe('default');
    expect(sensorTitle('temp_out')).toBe('Temperature outside');
    expect(sensorTitle('mystery_probe')).toBe('Mystery probe');
  });
});

describe('the sheet: what the box detects', () => {
  it('lists every reading with its age', async () => {
    vi.spyOn(api, 'playbooks').mockResolvedValue(playbooks);
    vi.spyOn(api, 'situationView').mockResolvedValue(view);
    vi.spyOn(api, 'sensors').mockResolvedValue(sensors);
    renderRoute('/situation');
    const panel = await screen.findByRole('region', { name: 'Detected' });
    const rows = within(panel).getAllByRole('listitem');
    expect(rows).toHaveLength(4);
    expect(rows[0]).toHaveTextContent('Internet probe');
    expect(rows[0]).toHaveTextContent('down');
    expect(within(rows[0]).getByText('down')).toHaveClass('badge-danger');
    expect(rows[2]).toHaveTextContent('14.5 °C');
    expect(rows[0].textContent).toMatch(/ago|just now/);
  });

  it('says nothing at all on a box with no sensors', async () => {
    vi.spyOn(api, 'playbooks').mockResolvedValue(playbooks);
    vi.spyOn(api, 'situationView').mockResolvedValue(view);
    vi.spyOn(api, 'sensors').mockRejectedValue(new ApiError(404, 'Not Found'));
    renderRoute('/situation');
    await screen.findByRole('region', { name: 'Conditions' });
    expect(screen.queryByRole('region', { name: 'Detected' })).toBeNull();
  });
});

describe('the briefing: a proposal the sensors raised', () => {
  it('says the box detected it', async () => {
    vi.spyOn(api, 'playbooks').mockResolvedValue(playbooks);
    vi.spyOn(api, 'situationView').mockResolvedValue(makeView({
      ...powerOffView,
      inferred: [{ ...powerOffView.inferred[0], condition: 'internet', state: 'off', detected: true, rule: 'sensor:internet', why: 'The box has not reached the internet for 10 minutes.' }],
    }));
    renderRoute('/');
    const block = await screen.findByRole('region', { name: 'The box thinks' });
    expect(block).toHaveTextContent('detected by the box');
    expect(block).toHaveTextContent('Internet — probably off');
  });
});
