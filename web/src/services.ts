// What is working: shared toggles for the services that fail, and the advice that changes when they do.
import type { ServiceId, Services } from './api/types';

export const SERVICE_IDS: ServiceId[] = ['power', 'water', 'gas', 'internet', 'phones'];
export const ALL_ON: Services = { power: true, water: true, gas: true, internet: true, phones: true };

export const SERVICE_INFO: Record<ServiceId, { title: string; icon: string; offLabel: string; links: { to: string; title: string }[] }> = {
  power: { title: 'Power', icon: 'bolt', offLabel: 'Power is off', links: [
    { to: '/s/grid-collapse', title: 'Grid collapse playbook' }, { to: '/m/power', title: 'Power module' }, { to: '/p/what-still-works', title: 'What still works in an outage' }, { to: '/p/solar-islanding', title: 'Solar panels in a power cut' }] },
  water: { title: 'Water', icon: 'drop', offLabel: 'Water is off', links: [
    { to: '/m/water', title: 'Water module' }, { to: '/p/water-disinfection', title: 'Water disinfection' }, { to: '/p/fieldcraft-water', title: 'Water outdoors' }, { to: '/m/sanitation', title: 'Sanitation module' }] },
  gas: { title: 'Gas', icon: 'fire', offLabel: 'Gas is off', links: [
    { to: '/m/shelter-heat', title: 'Shelter and heat module' }, { to: '/m/food', title: 'Food module' }, { to: '/p/fieldcraft-fire', title: 'Fire in a wet country' }, { to: '/medical/card/carbon-monoxide', title: 'Carbon monoxide card' }] },
  internet: { title: 'Internet', icon: 'globe', offLabel: 'Internet is off', links: [
    { to: '/p/what-still-works', title: 'What still works in an outage' }, { to: '/m/comms', title: 'Comms module' }, { to: '/s/cyber-attack', title: 'Cyber attack playbook' }] },
  phones: { title: 'Phones', icon: 'phone', offLabel: 'Phones are down', links: [
    { to: '/p/no-phones', title: 'Getting help without phones' }, { to: '/p/pmr446', title: 'PMR446 radio channels' }, { to: '/m/comms', title: 'Comms module' }, { to: '/p/fieldcraft-rescue', title: 'Getting found' }] },
};

export function offServices(services: Services | null | undefined): ServiceId[] {
  if (!services) return [];
  return SERVICE_IDS.filter((id) => services[id] === false);
}

// the short emergency numbers on their own, not digits inside a longer number such as 0800 999 999
const PHONE_NUMBERS = /(?<!\d[\s-]?)\b(999|112|111|105|101)\b(?![\s-]?\d)/;
const PHONE_NUMBERS_ALL = new RegExp(PHONE_NUMBERS.source, 'g');

/** Tag the emergency numbers in rendered content when the phones are down. Only text nodes are touched. */
export function tagPhoneNumbers(root: HTMLElement, link = '/p/no-phones'): number {
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
    acceptNode: (node) => {
      const parent = node.parentElement;
      if (!parent || parent.closest('a, code, pre, .no-phone, script, style')) return NodeFilter.FILTER_REJECT;
      return PHONE_NUMBERS.test(node.nodeValue ?? '') ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_SKIP;
    },
  });
  const nodes: Text[] = [];
  while (walker.nextNode()) nodes.push(walker.currentNode as Text);
  let count = 0;
  for (const node of nodes) {
    const text = node.nodeValue ?? '';
    const frag = document.createDocumentFragment();
    let last = 0;
    for (const m of text.matchAll(PHONE_NUMBERS_ALL)) {
      const at = m.index ?? 0;
      if (at > last) frag.append(text.slice(last, at));
      const tag = document.createElement('span');
      tag.className = 'no-phone';
      tag.append(m[0]);
      const note = document.createElement('a');
      note.href = link;
      note.className = 'no-phone-note';
      note.textContent = 'phones down';
      tag.append(' ', note);
      frag.append(tag);
      last = at + m[0].length;
      count += 1;
    }
    if (last < text.length) frag.append(text.slice(last));
    node.replaceWith(frag);
  }
  return count;
}
