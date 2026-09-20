import { WIKI } from '../../tests/fixtures/api';

const page = (title: string, body: string) => `<!doctype html><html><head><meta charset="utf-8"><title>${title}</title></head><body><h1>${title}</h1>${body}</body></html>`;

/** Article chain used by the reader specs: Main_Page -> Water -> Ice -> Electrical_grid. */
export const KIWIX_PAGES: Record<string, string> = {
  [`/kiwix/content/${WIKI}/A/Main_Page`]: page('Main Page', `<p>Welcome. Read about <a href="/kiwix/content/${WIKI}/A/Water">Water</a>.</p><form action="/kiwix/search"><input type="search" name="pattern" aria-label="Search this book"></form>`),
  [`/kiwix/content/${WIKI}/A/Water`]: page('Water', `<p>Water is an inorganic compound. See <a href="../A/Ice">Ice</a> or <a href="https://en.wikipedia.org/wiki/Water">the live article</a>.</p>`),
  [`/kiwix/content/${WIKI}/A/Ice`]: page('Ice', `<p>Ice is frozen water. Related: <a href="/kiwix/content/${WIKI}/A/Electrical_grid">Electrical grid</a>.</p>`),
  /* A page whose own script adds a link to the internet after it has loaded, which is the one kind the
     reader cannot unlink up front: the click handler is what still says so. */
  [`/kiwix/content/${WIKI}/A/Late_link`]: page('Late link', `<p>This page adds a link of its own.</p><button type="button" onclick="var a=document.createElement('a');a.href='https://example.org/late';a.textContent='a late link';document.body.appendChild(a)">Add a link</button>`),
  [`/kiwix/content/${WIKI}/A/Electrical_grid`]: page('Electrical grid', `<p>An electrical grid delivers electricity from producers to consumers.</p>`),
  '/kiwix/content/nhs_uk/www.nhs.uk/index.html': page('NHS', `<p><a href="/kiwix/content/nhs_uk/www.nhs.uk/conditions/">Conditions A to Z</a></p>`),
  '/kiwix/content/nhs_uk/www.nhs.uk/conditions/': page('Health A to Z', `<p>Conditions.</p>`),
  '/kiwix/content/nhs_uk/www.nhs.uk/conditions/dehydration/': page('Dehydration', `<p>Dehydration means your body loses more fluids than you take in.</p>`),
};
