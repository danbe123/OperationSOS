/* Dates the way a British household writes them. A native date input takes its order from the
 * browser's own locale, not from the page, so on a box shipped with an American Chrome the "use by"
 * field asked for mm/dd/yyyy. The box asks for dd/mm/yyyy and does the conversion itself. */

/** "06/09/2026" → "2026-09-06". Null when it is not a real date in that order. */
export function ukDateToIso(text: string): string | null {
  const m = /^(\d{1,2})\/(\d{1,2})\/(\d{4})$/.exec(text.trim());
  if (!m) return null;
  const day = Number(m[1]);
  const month = Number(m[2]);
  const year = Number(m[3]);
  if (month < 1 || month > 12 || day < 1 || day > 31) return null;
  const iso = `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
  const parsed = new Date(`${iso}T00:00:00Z`);
  if (Number.isNaN(parsed.getTime()) || parsed.getUTCDate() !== day || parsed.getUTCMonth() + 1 !== month) return null;
  return iso;
}

/** "2026-09-06" → "06/09/2026". Anything else comes back as it arrived. */
export function isoToUkDate(iso: string): string {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec((iso ?? '').trim());
  return m ? `${m[3]}/${m[2]}/${m[1]}` : iso;
}
