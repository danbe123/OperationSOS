// Children's paracetamol and ibuprofen doses by age band, copied from the NHS medicines pages held in the library.
// Ages are in whole months. Nothing here extrapolates: an age outside a table is reported as unavailable.

export type Medicine = 'paracetamol' | 'ibuprofen';
export type Form = 'liquid-120' | 'liquid-250' | 'melt-250' | 'liquid-100' | 'tablet-200';

export type DoseResult =
  | { ok: true; amount: string; mg: string; maxPerDay: string; intervalHours: number; notes: string[]; source: DoseSource }
  | { ok: false; reason: string; source: DoseSource };

export type DoseSource = { title: string; path: string; as_at: string };

type Band = { fromMonths: number; toMonths: number; amount: string; mg: string; maxPerDay: string; intervalHours: number; notes?: string[] };
type Table = { medicine: Medicine; form: Form; label: string; source: DoseSource; bands: Band[]; below: string };

const Y = 12;
const PARACETAMOL: DoseSource = { title: 'Paracetamol for children (NHS)', path: 'www.nhs.uk/medicines/paracetamol-for-children/', as_at: '2025-12-14' };
const IBUPROFEN: DoseSource = { title: 'Ibuprofen for children: how and when to give it (NHS)', path: 'www.nhs.uk/medicines/ibuprofen-for-children/how-and-when-to-give-ibuprofen-for-children/', as_at: '2025-12-14' };

export const FORMS: Record<Form, { medicine: Medicine; label: string }> = {
  'liquid-120': { medicine: 'paracetamol', label: 'Infant liquid 120mg/5ml (up to 5 years)' },
  'liquid-250': { medicine: 'paracetamol', label: 'Six plus liquid 250mg/5ml (6 years and over)' },
  'melt-250': { medicine: 'paracetamol', label: '250mg melting tablets (6 years and over)' },
  'liquid-100': { medicine: 'ibuprofen', label: 'Liquid 100mg/5ml (3 months and over)' },
  'tablet-200': { medicine: 'ibuprofen', label: '200mg tablets or capsules (12 to 17 years)' },
};

const TABLES: Table[] = [
  {
    medicine: 'paracetamol', form: 'liquid-120', label: FORMS['liquid-120'].label, source: PARACETAMOL,
    below: 'Paracetamol is not given under 2 months old. Speak to a doctor, pharmacist or 111.',
    bands: [
      { fromMonths: 2, toMonths: 3, amount: '2.5ml', mg: '60mg', maxPerDay: '2 doses in 24 hours', intervalHours: 4,
        notes: ['Only if the baby weighs over 4kg and was born after 37 weeks of pregnancy.', 'Up to 3 doses after the first and second MenB vaccinations.'] },
      { fromMonths: 3, toMonths: 6, amount: '2.5ml', mg: '60mg', maxPerDay: '4 doses in 24 hours', intervalHours: 4 },
      { fromMonths: 6, toMonths: 2 * Y, amount: '5ml', mg: '120mg', maxPerDay: '4 doses in 24 hours', intervalHours: 4 },
      { fromMonths: 2 * Y, toMonths: 4 * Y, amount: '7.5ml', mg: '180mg', maxPerDay: '4 doses in 24 hours', intervalHours: 4 },
      { fromMonths: 4 * Y, toMonths: 6 * Y, amount: '10ml', mg: '240mg', maxPerDay: '4 doses in 24 hours', intervalHours: 4 },
    ],
  },
  {
    medicine: 'paracetamol', form: 'liquid-250', label: FORMS['liquid-250'].label, source: PARACETAMOL,
    below: 'Six plus liquid is for children aged 6 years and over. Use the infant liquid for younger children.',
    bands: [
      { fromMonths: 6 * Y, toMonths: 8 * Y, amount: '5ml', mg: '250mg', maxPerDay: '4 doses in 24 hours', intervalHours: 4 },
      { fromMonths: 8 * Y, toMonths: 10 * Y, amount: '7.5ml', mg: '375mg', maxPerDay: '4 doses in 24 hours', intervalHours: 4 },
      { fromMonths: 10 * Y, toMonths: 12 * Y, amount: '10ml', mg: '500mg', maxPerDay: '4 doses in 24 hours', intervalHours: 4 },
      { fromMonths: 12 * Y, toMonths: 16 * Y, amount: '10ml to 15ml', mg: '500mg to 750mg', maxPerDay: '4 doses in 24 hours', intervalHours: 4 },
      { fromMonths: 16 * Y, toMonths: 18 * Y, amount: '10ml to 20ml', mg: '500mg to 1g', maxPerDay: '4 doses in 24 hours', intervalHours: 4 },
    ],
  },
  {
    medicine: 'paracetamol', form: 'melt-250', label: FORMS['melt-250'].label, source: PARACETAMOL,
    below: 'Melting tablets are for children aged 6 years and over.',
    bands: [
      { fromMonths: 6 * Y, toMonths: 9 * Y, amount: '1 tablet', mg: '250mg', maxPerDay: '4 doses in 24 hours', intervalHours: 4 },
      { fromMonths: 9 * Y, toMonths: 12 * Y, amount: '2 tablets', mg: '500mg', maxPerDay: '4 doses in 24 hours', intervalHours: 4 },
      { fromMonths: 12 * Y, toMonths: 16 * Y, amount: '2 or 3 tablets', mg: '500mg to 750mg', maxPerDay: '4 doses in 24 hours', intervalHours: 4 },
      { fromMonths: 16 * Y, toMonths: 18 * Y, amount: '2 to 4 tablets', mg: '500mg to 1g', maxPerDay: '4 doses in 24 hours', intervalHours: 4 },
    ],
  },
  {
    medicine: 'ibuprofen', form: 'liquid-100', label: FORMS['liquid-100'].label, source: IBUPROFEN,
    below: 'Ibuprofen is not given under 3 months old. Speak to a doctor, pharmacist or 111.',
    bands: [
      { fromMonths: 3, toMonths: 6, amount: '2.5ml', mg: '50mg', maxPerDay: '3 doses in 24 hours', intervalHours: 6, notes: ['Only if the baby weighs more than 5kg.'] },
      { fromMonths: 6, toMonths: 1 * Y, amount: '2.5ml', mg: '50mg', maxPerDay: '3 to 4 doses in 24 hours', intervalHours: 6, notes: ['If giving 4 doses in 24 hours, leave at least 4 hours between them.'] },
      { fromMonths: 1 * Y, toMonths: 4 * Y, amount: '5ml', mg: '100mg', maxPerDay: '3 doses in 24 hours', intervalHours: 6 },
      { fromMonths: 4 * Y, toMonths: 7 * Y, amount: '7.5ml', mg: '150mg', maxPerDay: '3 doses in 24 hours', intervalHours: 6 },
      { fromMonths: 7 * Y, toMonths: 10 * Y, amount: '10ml', mg: '200mg', maxPerDay: '3 doses in 24 hours', intervalHours: 6 },
      { fromMonths: 10 * Y, toMonths: 12 * Y, amount: '15ml', mg: '300mg', maxPerDay: '3 doses in 24 hours', intervalHours: 6 },
    ],
  },
  {
    medicine: 'ibuprofen', form: 'tablet-200', label: FORMS['tablet-200'].label, source: IBUPROFEN,
    below: 'Tablets and capsules are for children aged 12 and over; a doctor works out tablet doses for younger children from age and weight.',
    bands: [
      { fromMonths: 12 * Y, toMonths: 18 * Y, amount: '1 or 2 tablets', mg: '200mg to 400mg', maxPerDay: '3 doses in 24 hours', intervalHours: 6 },
    ],
  },
];

export const COMMON_NOTES = [
  'Always check the packet or leaflet, and use the syringe or spoon that comes with the medicine.',
  'Do not give more than the maximum number of doses without speaking to a doctor or pharmacist.',
];

export function doseFor(form: Form, ageMonths: number): DoseResult {
  const table = TABLES.find((t) => t.form === form);
  if (!table) throw new Error(`unknown form ${form}`);
  if (!Number.isFinite(ageMonths) || ageMonths < 0) return { ok: false, reason: 'Enter the child\'s age.', source: table.source };
  const first = table.bands[0];
  if (ageMonths < first.fromMonths) return { ok: false, reason: table.below, source: table.source };
  const band = table.bands.find((b) => ageMonths >= b.fromMonths && ageMonths < b.toMonths);
  if (!band) return { ok: false, reason: 'Aged 18 or over: use the adult page for this medicine.', source: table.source };
  return { ok: true, amount: band.amount, mg: band.mg, maxPerDay: band.maxPerDay, intervalHours: band.intervalHours,
           notes: [...(band.notes ?? []), ...COMMON_NOTES], source: table.source };
}

/** The library URL for a dose source: the full NHS site when it is installed, else the medicines-only build. */
export function sourceUrl(source: DoseSource, book: 'nhs_uk' | 'nhs_medicines' = 'nhs_medicines'): string {
  return `/read/${book}/${source.path}`;
}
