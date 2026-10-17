#!/usr/bin/env python3
"""Build the static KI-Einstieg site from data/jobs.json, data/events.json, data/companies.json.
Usage: python3 build/build_site.py [OUTPUT_DIR]   (or SITE_DIR env; default ./site)"""
import json, os, shutil, sys
from collections import Counter
from datetime import datetime
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = Path(sys.argv[1] if len(sys.argv) > 1 else os.environ.get('SITE_DIR', ROOT / 'site'))
ICON = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Crect width='64' height='64' rx='14' fill='%23144948'/%3E%3Ctext x='10' y='44' font-size='36' fill='white'%3EKI%3C/text%3E%3C/svg%3E"
ATS = 'Personio, Greenhouse, Lever, SmartRecruiters, Ashby, Recruitee, Workable, SAP SuccessFactors (RSS)'
TODO_LEGAL = '<div class="todo"><strong>TODO</strong><p>Diese Seite muss vor Veröffentlichung von Tom mit echten Angaben gefüllt werden (Name, Anschrift, Kontakt; § 5 DDG). Keine Angaben erfunden.</p></div>'


def load(name, default):
    path = ROOT / 'data' / name
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else default


def de(d):
    try: return datetime.strptime(d, '%Y-%m-%d').strftime('%d.%m.%Y')
    except (TypeError, ValueError): return d or ''


def page(title, body):
    return f'''<!doctype html>
<html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)} · KI-Einstieg</title><meta name="description" content="Dein Berufseinstieg in KI: Werkstudent, Praktikum, Abschlussarbeit und Ausbildung in Deutschland, Österreich und der Schweiz.">
<link rel="icon" href="{ICON}"><link rel="stylesheet" href="assets/style.css"></head>
<body><header class="wrap"><a class="brand" href="index.html">KI-Einstieg<span aria-hidden="true"> ↗</span></a><nav aria-label="Hauptnavigation"><a href="index.html#stellen">Stellen entdecken</a><a href="index.html#events">Hackathons</a><a href="stelle-veroeffentlichen.html">Stelle veröffentlichen</a></nav></header>
<main class="wrap">{body}</main><footer class="wrap"><p>Stellen aus den öffentlichen Karriere-Seiten bzw. Job-Feeds der Unternehmen ({ATS}). Alle Rechte an den Anzeigen liegen bei den jeweiligen Unternehmen. Bewerbung immer direkt beim Unternehmen.</p><nav aria-label="Rechtliches"><a href="quellen.html">Quellen</a><a href="impressum.html">Impressum</a><a href="datenschutz.html">Datenschutz</a><a href="stelle-veroeffentlichen.html">Stelle veröffentlichen</a></nav></footer></body></html>'''


def options(values):
    return ''.join(f'<option value="{escape(v)}">{escape(v)}</option>' for v in values)


def main():
    jobs = load('jobs.json', [])
    events = load('events.json', [])
    companies = load('companies.json', [])
    stats = load('stats.json', {})
    today = datetime.now().date().isoformat()
    events = sorted((e for e in events if (e.get('end') or e.get('start') or '') >= today), key=lambda e: e['start'])
    SITE.mkdir(parents=True, exist_ok=True)
    shutil.copytree(ROOT / 'assets', SITE / 'assets', dirs_exist_ok=True)
    (SITE / 'data').mkdir(exist_ok=True)
    for name, value in (('jobs.json', jobs), ('events.json', events), ('stats.json', stats)):
        (SITE / 'data' / name).write_text(json.dumps(value, ensure_ascii=False, indent=1), encoding='utf-8')

    order = ['Werkstudent', 'Praktikum', 'Abschlussarbeit', 'Ausbildung / Duales Studium', 'Trainee', 'Junior / Berufseinstieg']
    types = sorted({j['type'] for j in jobs}, key=lambda t: order.index(t) if t in order else 99)
    regions = sorted({j['region'] for j in jobs if j.get('region') and j['region'] not in ('Österreich', 'Schweiz')})
    regions += [r for r in ('Österreich', 'Schweiz') if any(j.get('region') == r for j in jobs)]
    cities = len({j['city'] for j in jobs if j.get('city')})
    firms = len({j['company'] for j in jobs})
    updated = de((stats.get('generated_at') or today)[:10])

    def event_card(e):
        when = de(e['start']) + (f" – {de(e['end'])}" if e.get('end') and e['end'] != e['start'] else '')
        return (f'<article class="card"><span class="badge">{escape(e.get("status", ""))}</span><h3>{escape(e["name"])}</h3><p>{when} · {escape(e.get("city", ""))}</p>'
                f'<p><strong>Für:</strong> {escape(e.get("audience", ""))}</p><p>{escape(e.get("description", ""))}</p>'
                f'<a href="{escape(e["url"])}" target="_blank" rel="noopener noreferrer">Zur Veranstaltung (Quelle) ↗</a></article>')

    data = json.dumps(jobs, ensure_ascii=False).replace('</', '<\\/').replace('&', '\\u0026')
    body = f'''<section class="hero"><p class="eyebrow">DEIN NÄCHSTER SCHRITT</p><h1>KI braucht<br>deinen Einstieg.</h1><p class="tagline">Werkstudent, Praktikum, Abschlussarbeit &amp; Ausbildung in KI – in Deutschland, Österreich und der Schweiz.</p><div class="metrics"><p><strong>{len(jobs)}</strong> Stellen</p><p><strong>{firms}</strong> Unternehmen</p><p><strong>{cities}</strong> Städte</p><p><strong>{updated}</strong> Letzte Aktualisierung</p></div></section>
<section id="stellen"><h2>Finde deinen Platz in der KI.</h2><form id="filters" class="filters"><label>Typ<select id="type"><option value="">Alle Typen</option>{options(types)}</select></label><label>Region<select id="region"><option value="">Alle Regionen</option>{options(regions)}</select></label><label class="search">Stadt, Unternehmen oder Titel<input id="search" type="search" placeholder="z. B. Berlin oder Machine Learning"></label><label class="check"><input id="remote" type="checkbox"> Remote/Homeoffice</label><label class="check"><input id="recent" type="checkbox"> Nur letzte 14 Tage</label></form><p id="result-count" role="status" aria-live="polite"></p><div id="jobs" class="grid"></div><button id="load-more" type="button" hidden>Mehr laden</button><noscript><p>Bitte JavaScript für die Stellenfilter aktivieren. Alle Stellen stehen auch als <a href="data/jobs.json">JSON-Datei</a> bereit.</p></noscript></section>
<section id="events"><p class="eyebrow">GEMEINSAM LOSLEGEN</p><h2>Hackathons &amp; Wettbewerbe</h2><div class="grid">{''.join(event_card(e) for e in events)}</div></section>
<section class="newsletter"><h2>Dein nächster Einstieg im Postfach.</h2><p>Newsletter · Platzhalter – Anmeldung noch nicht aktiv.</p><form id="newsletter"><label for="email">E-Mail-Adresse</label><div class="email-row"><input id="email" type="email" autocomplete="email" placeholder="du@beispiel.de"><button type="submit">Eintragen</button></div><p id="newsletter-message" role="status" aria-live="polite"></p></form></section>
<script type="application/json" id="jobs-data">{data}</script><script src="assets/app.js" defer></script>'''
    (SITE / 'index.html').write_text(page('Stellen entdecken', body), encoding='utf-8')

    per = Counter(j['company'] for j in jobs)
    def link(c): return f'<a href="{escape(c["careers_url"])}" target="_blank" rel="noopener noreferrer">{escape(c["name"])}</a>'
    with_jobs = sorted((c for c in companies if per.get(c['name'])), key=lambda c: (-per[c['name']], c['name'].casefold()))
    rows = ''.join(f'<li>{link(c)} · {escape(c["ats"])} · {per[c["name"]]} passende Stellen</li>' for c in with_jobs)
    others = ', '.join(link(c) for c in sorted((c for c in companies if not per.get(c['name'])), key=lambda c: c['name'].casefold()))
    rows += f'</ul><h2>Weitere beobachtete Feeds (derzeit ohne passende Einstiegsstelle)</h2><p class="small">{others}</p><ul>'
    sources = (f'<h1>Quellen</h1><p>KI-Einstieg liest ausschließlich öffentliche, zum Einbinden gedachte Job-Feeds der Unternehmen ({ATS}) und verlinkt immer auf die Originalanzeige beim Unternehmen. '
               f'Aktuell {len(companies)} Unternehmen, davon {len(per)} mit passenden Einstiegsstellen.</p><ul>{rows}</ul>'
               '<p>Unternehmen können die Entfernung ihrer Einträge oder die Aufnahme ihres Feeds anfordern. Kontakt: TODO (E-Mail-Adresse folgt).</p>')
    (SITE / 'quellen.html').write_text(page('Quellen', sources), encoding='utf-8')

    pricing = ('<h1>Talente für KI gewinnen.</h1><div class="todo">ENTWURF – Preise noch nicht final, Buchung noch nicht möglich</div><div class="grid">'
               '<article class="card"><h2>Basis</h2><p class="price">49 €</p><p>30 Tage</p></article>'
               '<article class="card"><h2>Plus</h2><p class="price">89 €</p><p>60 Tage, hervorgehoben, im Newsletter</p></article>'
               '<article class="card"><h2>Premium</h2><p class="price">149 €</p><p>90 Tage, oben angepinnt, Newsletter + Social Post</p></article></div>'
               '<p>Alle Preise netto zzgl. MwSt.</p><p>Kostenlose Einträge für Hochschulen und gemeinnützige Hackathons.</p><p>Kontakt: TODO (E-Mail-Adresse folgt)</p>')
    (SITE / 'stelle-veroeffentlichen.html').write_text(page('Stelle veröffentlichen', pricing), encoding='utf-8')
    (SITE / 'impressum.html').write_text(page('Impressum', '<h1>Impressum</h1>' + TODO_LEGAL), encoding='utf-8')
    (SITE / 'datenschutz.html').write_text(page('Datenschutz', '<h1>Datenschutz</h1>' + TODO_LEGAL + '<h2>Vor Veröffentlichung zu ergänzen</h2><ul><li>Hosting-Anbieter</li><li>Server-Logs und Aufbewahrungsdauer</li><li>Newsletter-Anbieter (derzeit nicht aktiv)</li><li>Keine Cookies/Tracking derzeit</li></ul>'), encoding='utf-8')
    print(f'Statische Website erstellt: {SITE}')


if __name__ == '__main__':
    main()
