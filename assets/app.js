'use strict';
const jobs = JSON.parse(document.getElementById('jobs-data').textContent);
const filters = document.getElementById('filters');
const list = document.getElementById('jobs');
const more = document.getElementById('load-more');
let limit = 30; // = PAGE
const field = id => document.getElementById(id);
const dateFormat = new Intl.DateTimeFormat('de-DE');
function node(tag, text, className) {
  const element = document.createElement(tag);
  if (text !== undefined) element.textContent = text;
  if (className) element.className = className;
  return element;
}
const ATS_LABELS = {personio: 'Personio', greenhouse: 'Greenhouse', lever: 'Lever', smartrecruiters: 'SmartRecruiters', ashby: 'Ashby', recruitee: 'Recruitee', workable: 'Workable', successfactors: 'SAP SuccessFactors'};
const PAGE = 30, PER_COMPANY = 3;
// Erste Seite: höchstens 3 Stellen pro Firma; weitere Stellen derselben Firma rücken nach hinten.
function diversify(items) {
  const first = [], rest = [], count = new Map();
  for (const job of items) {
    const n = count.get(job.company) || 0;
    if (first.length < PAGE && n < PER_COMPANY) { first.push(job); count.set(job.company, n + 1); }
    else rest.push(job);
  }
  return first.concat(rest);
}
function render() {
  const search = field('search').value.trim().toLocaleLowerCase('de');
  const now = new Date();
  const cutoff = new Date(now);
  cutoff.setDate(cutoff.getDate() - 14);
  const words = search.split(/\s+/).filter(Boolean);
  const matches = jobs.filter(job => (!field('type').value || job.type === field('type').value)
    && (!field('city').value || job.city === field('city').value)
    && (!field('region').value || job.region === field('region').value)
    && (!field('field').value || (job.fields || []).includes(field('field').value))
    && (!field('remote').checked || job.remote)
    && (!field('recent').checked || (new Date(job.date) >= cutoff && new Date(job.date) <= now))
    && (!words.length || words.every(w => [job.title, job.company, job.city, job.region, ...(job.ai_terms || [])].join(' ').toLocaleLowerCase('de').includes(w))));
  syncUrl();
  const ordered = diversify(matches);
  list.replaceChildren();
  for (const job of ordered.slice(0, limit)) {
    const card = node('article', undefined, job.featured === true ? 'card featured' : 'card');
    const badges = node('div', undefined, 'badges');
    badges.append(node('span', job.type, 'badge'));
    if (job.featured === true) badges.append(node('span', 'Anzeige', 'ad-label'));
    if (['AT', 'CH'].includes(job.country)) badges.append(node('span', job.country, 'badge'));
    if (job.remote) badges.append(node('span', 'Homeoffice', 'badge remote'));
    const heading = node('h3');
    if (job.page) { const detail = node('a', job.title); detail.href = job.page; heading.append(detail); } else heading.textContent = job.title;
    card.append(badges, heading, node('p', job.company, 'company'), node('p', [job.city, job.region].filter(Boolean).join(' · ') || 'Ort nicht angegeben'));
    const parsed = new Date(job.date);
    const time = node('time', Number.isNaN(parsed.getTime()) ? 'Datum unbekannt' : dateFormat.format(parsed));
    if (!Number.isNaN(parsed.getTime())) time.dateTime = job.date;
    const retrieved = job.retrieved || new Intl.DateTimeFormat('sv-SE', {timeZone: 'Europe/Berlin'}).format(new Date());
    const retrievalDate = new Date(retrieved + 'T12:00:00');
    const note = node('p', `Quelle: Karriereseite von ${job.company} via ${ATS_LABELS[job.ats] || job.ats || 'Karriere-Feed'} · abgerufen am ${dateFormat.format(retrievalDate)} · Angaben ohne Gewähr`, 'source-note');
    const link = node('a', 'Zur Originalanzeige ↗', 'button');
    link.href = job.url;
    link.target = '_blank';
    link.rel = 'noopener noreferrer';
    card.append(time, note, link);
    list.append(card);
  }
  if (!matches.length) list.append(node('p', 'Keine passenden Stellen gefunden. Bitte passe die Filter an.'));
  field('result-count').textContent = `${matches.length} Stellen gefunden · ${Math.min(limit, matches.length)} angezeigt`;
  more.hidden = matches.length <= limit;
}
// Filterzustand in der URL (teilbar, kein Tracking): ?typ=&stadt=&region=&feld=&q=&remote=1&neu=1
const KEYS = {type: 'typ', city: 'stadt', region: 'region', field: 'feld', search: 'q'};
function syncUrl() {
  const p = new URLSearchParams();
  for (const [id, key] of Object.entries(KEYS)) if (field(id).value.trim()) p.set(key, field(id).value.trim());
  if (field('remote').checked) p.set('remote', '1');
  if (field('recent').checked) p.set('neu', '1');
  history.replaceState(null, '', (p.toString() ? `?${p}` : location.pathname) + location.hash);
}
(() => {
  const p = new URLSearchParams(location.search);
  for (const [id, key] of Object.entries(KEYS)) if (p.has(key)) field(id).value = p.get(key);
  field('remote').checked = p.get('remote') === '1';
  field('recent').checked = p.get('neu') === '1';
})();
filters.addEventListener('submit', event => event.preventDefault());
filters.addEventListener('input', () => { limit = 30; render(); });
more.addEventListener('click', () => { limit += 30; render(); });
render();
