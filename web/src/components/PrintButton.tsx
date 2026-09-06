import { Icon } from '../icons';
import { useKiosk } from '../kiosk/KioskProvider';

/** Print, everywhere it is offered. The kiosk has no printer, so it never shows the button.
 * `disabled` is for a sheet that is not on the page yet: a button that does nothing when tapped is
 * worse than one that says it cannot be tapped. */
export function PrintButton({ label = 'Print', onPrint, disabled = false }: { label?: string; onPrint?: () => void; disabled?: boolean } = {}) {
  const kiosk = useKiosk();
  if (kiosk) return null;
  return (
    <button
      type="button" className="btn btn-small no-print" disabled={disabled} aria-disabled={disabled}
      onClick={() => (onPrint ? onPrint() : window.print())}
    >
      <Icon name="print" size={18} /><span>{label}</span>
    </button>
  );
}
