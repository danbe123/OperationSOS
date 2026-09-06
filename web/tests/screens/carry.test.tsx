import { describe, it, expect, vi } from 'vitest';
import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderRoute } from '../render';
import { api, ApiError } from '../../src/api/client';
import { countLines, importProgress, importTrouble, parseImport } from '../../src/situation/SituationExport';
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

    await user.click(within(section).getByRole('button', { name: 'Copy the codes as text' }));
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
    const result = await within(section).findByRole('status', { name: 'What came in' });
    expect(result).toHaveTextContent('Brought in from the other box.');
    expect(result).toHaveTextContent('conditions: 2 updated, 8 kept');
    expect(result).toHaveTextContent('events: 3 added, 1 skipped');
    expect(result).toHaveTextContent('Home kept · Situation started: grid-collapse');
    expect(result).toHaveTextContent('Mains power set to off');
  });

  it('says a refusal in household words, under the button that caused it', async () => {
    mockSheet();
    vi.spyOn(api, 'importSituation').mockRejectedValue(new ApiError(422, 'a scanned chunk is not a QR chunk: expected {"i", "n", "d"}'));
    const user = userEvent.setup();
    renderRoute('/situation');
    const section = await screen.findByRole('region', { name: 'Carry the situation' });
    await user.type(within(section).getByRole('textbox', { name: 'Situation to bring in' }), 'nonsense');
    const button = within(section).getByRole('button', { name: 'Bring it in' });
    await user.click(button);
    const said = await within(section).findByRole('alert');
    expect(said).toHaveTextContent('That is not one of this box’s codes. Type the line printed under the code, starting with {');
    // The box's own sentence is kept, but never leads.
    expect(said.textContent?.indexOf('The box said:')).toBeGreaterThan(0);
    // and it is said where the person who pressed the button is looking, not 500 px above it
    expect(button.compareDocumentPosition(said) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it('counts the codes as they are typed in', async () => {
    mockSheet();
    const user = userEvent.setup();
    renderRoute('/situation');
    const section = await screen.findByRole('region', { name: 'Carry the situation' });
    const box = within(section).getByRole('textbox', { name: 'Situation to bring in' });
    await user.click(box);
    await user.paste('{"i":0,"n":3,"d":"one"}');
    expect(await within(section).findByText('Code 1 of 3 read. Type the next one on a new line.')).toBeInTheDocument();
    await user.paste('\n{"i":1,"n":3,"d":"two"}\n{"i":2,"n":3,"d":"three"}');
    expect(await within(section).findByText('All 3 codes read. Bring it in.')).toBeInTheDocument();
  });

  it('describes the paste it offers, and never a scan or a photograph', async () => {
    mockSheet();
    renderRoute('/situation');
    const section = await screen.findByRole('region', { name: 'Carry the situation' });
    expect(section).toHaveTextContent('type or paste each code’s text in order');
    expect(section.textContent).not.toMatch(/scan|photograph|JSON/i);
    expect(within(section).getByLabelText('Situation to bring in')).toHaveAttribute('placeholder', '{"i":0,"n":3,"d":"H4sIAAAA…');
    // "Bring it in" is not an add, and wears no "+".
    expect(within(section).getByRole('button', { name: 'Bring it in' }).querySelector('svg')).toBeNull();
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

  it('turns the box\'s own refusals into something a household can act on', () => {
    expect(importTrouble('a scanned chunk is not a QR chunk: expected {"i", "n", "d"}')).toEqual({
      say: 'That is not one of this box’s codes. Type the line printed under the code, starting with {',
      detail: 'a scanned chunk is not a QR chunk: expected {"i", "n", "d"}',
    });
    expect(importTrouble('chunks 2, 3 of 3 missing: scan the rest').say).toBe('The box has not got all the codes yet. Type the text of each one, one per line, in order.');
    // Anything the box says that is not on the list is passed through rather than guessed at.
    expect(importTrouble('the box is out of room')).toEqual({ say: 'the box is out of room' });
  });

  it('counts the codes it has been given, and says nothing when it cannot tell', () => {
    expect(importProgress('')).toBeNull();
    expect(importProgress('nonsense')).toBeNull();
    expect(importProgress('{"kind":"sos-situation-export"}')).toBeNull();
    expect(importProgress('{"i":1,"n":3,"d":"b"}')).toBe('Code 1 of 3 read. Type the next one on a new line.');
    expect(importProgress('{"i":0,"n":2,"d":"a"}\n{"i":1,"n":2,"d":"b"}')).toBe('All 2 codes read. Bring it in.');
    expect(importProgress('{"i":0,"n":1,"d":"a"}')).toBe('That is the only code. Bring it in.');
  });

  it('sends the export document itself when one is pasted, and the chunk lines otherwise', () => {
    expect(parseImport(' {"kind":"sos-situation-export"} ')).toEqual({ kind: 'sos-situation-export' });
    expect(parseImport('one\ntwo\n\nthree')).toEqual(['one', 'two', 'three']);
    expect(parseImport('  only-one  ')).toEqual(['only-one']);
  });
});
