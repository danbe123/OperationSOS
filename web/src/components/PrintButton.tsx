import { Icon } from '../icons';
import { useKiosk } from '../kiosk/KioskProvider';

/** Print, everywhere it is offered. The kiosk has no printer, so it never shows the button. */
export function PrintButton({ label = 'Print', onPrint }: { label?: string; onPrint?: () => void } = {}) {
  const kiosk = useKiosk();
  if (kiosk) return null;
  return (
    <button type="button" className="btn btn-small no-print" onClick={() => (onPrint ? onPrint() : window.print())}>
      <Icon name="print" size={18} /><span>{label}</span>
    </button>
  );
}
