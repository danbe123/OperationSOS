import { describe, it, expect, vi } from 'vitest';
import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderRoute } from '../render';
import { api, ApiError } from '../../src/api/client';
import { countLines, parseImport } from '../../src/situation/SituationExport';
import { exportChunks, importSummary, playbooks, view } from '../fixtures/api';

function mockSheet() {
  vi.spyOn(api, 'situationView').mockResolvedValue(view);
  vi.spyOn(api, 'playbooks').mockResolvedValue(playbooks);
  vi.spyOn(api, 'sensors').mockRejectedValue(new ApiError(404, 'Not Found'));
}

describe('carrying the situation to another box', () => {
  it('shows the chunks one at a time, with Previous, Next and a text fallback', async () => {
    mockSheet();
    const chunks = vi.spyOn(api, 'exportChunks').mockResolvedValue(exportChunks);
    const user = userEvent.setup();
    renderRoute('/situation');
    const section = await screen.findByRole('region', { name: 'Carry the situation' });
    await user.click(within(section).getByRole('button', { name: /Export as codes/ }));
    expect(chunks).toHaveBeenCalled();

    const codes = await within(section).findByRole('group', { name: 'Situation codes' });
    expect(codes).toHaveTextContent('Code 1 of 2');
    expect(await within(codes).findByRole('img', { name: /Situation code 1 of 2/ })).toBeInTheDocument();
    expect(within(codes).getByRole('button', { name: /Previous/ })).toBeDisabled();

    await user.click(within(codes).getByRole('button', { name: /Next/ }));
    expect(codes).toHaveTextContent('Code 2 of 2');
    expect(within(codes).getByRole('button', { name: /Next/ })).toBeDisabled();

    await user.click(within(section).getByRole('button', { name: 'Copy as text instead' }));
    expect(within(section).getByRole('textbox', { name: /Situation code 2 as text/ })).toHaveValue(exportChunks.chunks[1]);
  });

  it('brings a situation in and says what changed', async () => {
    mockSheet();
    const bring = vi.spyOn(api, 'importSituation').mockResolvedValue(importSummary);
    const user = userEvent.setup();
    renderRoute('/situation');
    const section = await screen.findByRole('region', { name: 'Carry the situation' });
    const box = within(section).getByRole('textbox', { name: 'Situation to bring in' });
    expect(within(section).getByRole('button', { name: /Bring it in/ })).toBeDisabled();
    await user.type(box, '{{"i":0,"n":1,"d":"x"}');
    await user.click(within(section).getByRole('button', { name: /Bring it in/ }));
    expect(bring).toHaveBeenCalledWith({ i: 0, n: 1, d: 'x' });
    const result = await within(section).findByRole('status');
    expect(result).toHaveTextContent('Brought in from the other box.');
    expect(result).toHaveTextContent('conditions: 2 updated, 8 kept');
    expect(result).toHaveTextContent('events: 3 added, 1 skipped');
    expect(result).toHaveTextContent('Home kept · Situation started: grid-collapse');
    expect(result).toHaveTextContent('Mains power set to off');
  });

  it('says what the box said when the import is refused', async () => {
    mockSheet();
    vi.spyOn(api, 'importSituation').mockRejectedValue(new ApiError(422, 'Chunk 2 of 3 is missing'));
    const user = userEvent.setup();
    renderRoute('/situation');
    const section = await screen.findByRole('region', { name: 'Carry the situation' });
    await user.type(within(section).getByRole('textbox', { name: 'Situation to bring in' }), 'nonsense');
    await user.click(within(section).getByRole('button', { name: /Bring it in/ }));
    expect(await within(section).findByText('Chunk 2 of 3 is missing')).toBeInTheDocument();
  });
});

describe('reading what came in', () => {
  it('turns the box\'s nested counts into one line per kind of row', () => {
    expect(countLines(importSummary)).toEqual([
      'conditions: 2 updated, 8 kept',
      'household: 1 added, 2 kept',
      'neighbours: 2 added',
      'events: 3 added, 1 skipped',
    ]);
    expect(countLines({ ok: true, counts: { stock: { added: 0, kept: 0 } } })).toEqual(['stock: nothing to do']);
    expect(countLines({ ok: true })).toEqual([]);
  });

  it('sends the export document itself when one is pasted, and the chunk lines otherwise', () => {
    expect(parseImport(' {"kind":"sos-situation-export"} ')).toEqual({ kind: 'sos-situation-export' });
    expect(parseImport('one\ntwo\n\nthree')).toEqual(['one', 'two', 'three']);
    expect(parseImport('  only-one  ')).toEqual(['only-one']);
  });
});
