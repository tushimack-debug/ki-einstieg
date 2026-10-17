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
  const matches = jobs.filter(job => (!field('type').value || job.type === field('type').value)
    && (!field('region').value || job.region === field('region').value)
    && (!field('remote').checked || job.remote)
    && (!field('recent').checked || (new Date(job.date) >= cutoff && new Date(job.date) <= now))
    && (!search || [job.title, job.company, job.city, job.region].join(' ').toLocaleLowerCase('de').includes(search)));
  const ordered = diversify(matches);
  list.replaceChildren();
  for (const job of ordered.slice(0, limit)) {
    const card = node('article', undefined, 'card');
    const badges = node('div', undefined, 'badges');
    badges.append(node('span', job.type, 'badge'));
    if (['AT', 'CH'].includes(job.country)) badges.append(node('span', job.country, 'badge'));
    if (job.remote) badges.append(node('span', 'Homeoffice', 'badge remote'));
    const heading = node('h3');
    if (job.page) { const detail = node('a', job.title); detail.href = job.page; heading.append(detail); } else heading.textContent = job.title;
    card.append(badges, heading, node('p', job.company, 'company'), node('p', [job.city, job.region].filter(Boolean).join(' · ') || 'Ort nicht angegeben'));
    const parsed = new Date(job.date);
    const time = node('time', Number.isNaN(parsed.getTime()) ? 'Datum unbekannt' : dateFormat.format(parsed));
    if (!Number.isNaN(parsed.getTime())) time.dateTime = job.date;
    const link = node('a', `${job.source_label || 'Zur Stelle bei ' + job.company} ↗`);
    link.href = job.url;
    link.target = '_blank';
    link.rel = 'noopener noreferrer';
    card.append(time, link);
    list.append(card);
  }
  if (!matches.length) list.append(node('p', 'Keine passenden Stellen gefunden. Bitte passe die Filter an.'));
  field('result-count').textContent = `${matches.length} Stellen gefunden · ${Math.min(limit, matches.length)} angezeigt`;
  more.hidden = matches.length <= limit;
}
filters.addEventListener('submit', event => event.preventDefault());
filters.addEventListener('input', () => { limit = 30; render(); });
more.addEventListener('click', () => { limit += 30; render(); });
if (field('newsletter')) field('newsletter').addEventListener('submit', event => {
  event.preventDefault();
  field('newsletter-message').textContent = 'Newsletter startet bald – Anmeldung noch nicht aktiv.';
});
render();
