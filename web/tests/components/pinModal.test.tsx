import { describe, it, expect, vi } from 'vitest';
import { render, screen, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { api, ApiError, getToken, setToken } from '../../src/api/client';
import { usePinGate } from '../../src/components/PinModal';

function Host({ action }: { action: () => Promise<string> }) {
  const { run, dialog } = usePinGate();
  return (
    <div>
      <button onClick={() => void run(action).then((r) => { document.title = String(r); })}>Go</button>
      {dialog}
    </div>
  );
}

describe('usePinGate', () => {
  it('runs the call directly when it succeeds', async () => {
    const user = userEvent.setup();
    render(<Host action={async () => 'ok'} />);
    await user.click(screen.getByText('Go'));
    await act(async () => {});
    expect(document.title).toBe('ok');
    expect(screen.queryByRole('dialog')).toBeNull();
  });

  it('on 401 asks for the PIN with a numeric pad, stores the token and retries', async () => {
    setToken(null);
    const user = userEvent.setup();
    const action = vi.fn<() => Promise<string>>().mockRejectedValueOnce(new ApiError(401, 'PIN required')).mockResolvedValueOnce('done');
    const pin = vi.spyOn(api, 'pin').mockResolvedValue({ token: 'tok-1', expires_in: 600 });
    render(<Host action={action} />);
    await user.click(screen.getByText('Go'));
    const dialog = await screen.findByRole('dialog', { name: 'Admin PIN' });
    const input = screen.getByLabelText('PIN');
    expect(input).toHaveAttribute('inputmode', 'numeric');
    expect(input).toHaveAttribute('type', 'password');
    await user.type(input, '1234{Enter}');
    expect(pin).toHaveBeenCalledWith('1234');
    await act(async () => {});
    expect(getToken()).toBe('tok-1');
    expect(action).toHaveBeenCalledTimes(2);
    expect(document.title).toBe('done');
    expect(dialog).not.toBeInTheDocument();
  });

  it('shows Wrong PIN on 401 and the rate-limit message on 429, and Cancel resolves undefined', async () => {
    const user = userEvent.setup();
    const action = vi.fn<() => Promise<string>>().mockRejectedValue(new ApiError(401, 'PIN required'));
    vi.spyOn(api, 'pin').mockRejectedValueOnce(new ApiError(401, 'wrong')).mockRejectedValueOnce(new ApiError(429, 'slow down'));
    render(<Host action={action} />);
    await user.click(screen.getByText('Go'));
    await user.type(await screen.findByLabelText('PIN'), '0000{Enter}');
    expect(await screen.findByText('Wrong PIN')).toBeInTheDocument();
    await user.clear(screen.getByLabelText('PIN'));
    await user.type(screen.getByLabelText('PIN'), '0000{Enter}');
    expect(await screen.findByText('Too many attempts; wait a minute')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Cancel' }));
    expect(screen.queryByRole('dialog')).toBeNull();
  });
});
