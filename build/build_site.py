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
CONTACT = 'tushimack@gmail.com'
MAIL = f'<a href="mailto:{CONTACT}">{CONTACT}</a>'
IMPRESSUM = (
    '<h1>Impressum</h1>'
    '<h2>Angaben gemäß § 5 DDG</h2>'
    '<p>Tom Mack<br>Pfälzer Straße 20b<br>91052 Erlangen<br>Deutschland</p>'
    f'<h2>Kontakt</h2><p>E-Mail: {MAIL}</p>'
    '<p>KI-Einstieg wird von einer Privatperson betrieben. Eine Umsatzsteuer-Identifikationsnummer ist derzeit nicht vorhanden.</p>'
    '<h2>Verantwortlich für den Inhalt nach § 18 Abs. 2 MStV</h2>'
    '<p>Tom Mack, Pfälzer Straße 20b, 91052 Erlangen</p>'
    '<h2>Hinweis zu externen Links</h2>'
    '<p>Die Stellenanzeigen auf dieser Website stammen aus den öffentlichen Job-Feeds der jeweiligen Arbeitgeber und verlinken auf deren eigene Seiten. '
    'Für Inhalte externer Seiten sind ausschließlich deren Betreiber verantwortlich. Zum Zeitpunkt der Verlinkung waren keine Rechtsverstöße erkennbar; '
    'bei Bekanntwerden von Rechtsverletzungen entfernen wir entsprechende Links umgehend. Angaben zu Stellen (z. B. Verfügbarkeit, Inhalte) ohne Gewähr.</p>')
DATENSCHUTZ = (
    '<h1>Datenschutzerklärung</h1>'
    '<h2>1. Verantwortlicher</h2>'
    f'<p>Tom Mack, Pfälzer Straße 20b, 91052 Erlangen, Deutschland · E-Mail: {MAIL}</p>'
    '<h2>2. Hosting über GitHub Pages</h2>'
    '<p>Diese Website wird über GitHub Pages bereitgestellt, einen Dienst der GitHub, Inc., 88 Colin P. Kelly Jr. Street, San Francisco, CA 94107, USA '
    '(ein Unternehmen der Microsoft Corporation). Beim Aufruf der Seiten verarbeitet GitHub technisch notwendige Server-Logdaten, insbesondere die IP-Adresse, '
    'Datum und Uhrzeit des Zugriffs, die aufgerufene Seite, Browser- und Systeminformationen sowie die verweisende Seite. Dies dient der sicheren und '
    'stabilen Auslieferung der Website (Art. 6 Abs. 1 lit. f DSGVO; berechtigtes Interesse an einem sicheren, funktionsfähigen Webangebot). '
    'Wir selbst haben keinen Zugriff auf diese Logdaten und werten sie nicht aus.</p>'
    '<p>Dabei kann eine Übermittlung personenbezogener Daten in die USA erfolgen. GitHub ist unter dem EU-US Data Privacy Framework zertifiziert; '
    'die Übermittlung stützt sich auf den Angemessenheitsbeschluss der EU-Kommission (Art. 45 DSGVO). Weitere Informationen: '
    '<a href="https://docs.github.com/de/site-policy/privacy-policies/github-general-privacy-statement" target="_blank" rel="noopener noreferrer">GitHub General Privacy Statement</a>.</p>'
    '<h2>3. Keine Cookies, kein Tracking</h2>'
    '<p>Diese Website setzt keine Cookies, verwendet keine Analyse- oder Tracking-Dienste und bindet keine externen Schriften, Skripte oder Inhalte '
    'von Drittanbietern ein. Die Stellenfilter laufen vollständig lokal in Ihrem Browser.</p>'
    '<h2>4. Externe Links</h2>'
    '<p>Stellenanzeigen verlinken auf die Seiten der jeweiligen Arbeitgeber. Erst wenn Sie einen solchen Link anklicken, werden Daten an den '
    'jeweiligen Anbieter übertragen; dafür gilt dessen Datenschutzerklärung.</p>'
    '<h2>5. Kontakt per E-Mail</h2>'
    '<p>Wenn Sie uns per E-Mail kontaktieren, verarbeiten wir Ihre Angaben (E-Mail-Adresse, Inhalt der Nachricht), um Ihre Anfrage zu beantworten '
    '(Art. 6 Abs. 1 lit. b bzw. f DSGVO). Die Daten werden gelöscht, sobald sie dafür nicht mehr erforderlich sind und keine gesetzlichen Aufbewahrungspflichten bestehen. '
    'Für den E-Mail-Empfang nutzen wir Google Mail (Google Ireland Limited).</p>'
    '<h2>6. Newsletter</h2><p>Ein Newsletter ist geplant, derzeit aber nicht aktiv. Es werden keine Anmeldedaten erhoben.</p>'
    '<h2>7. Ihre Rechte</h2>'
    '<p>Sie haben das Recht auf Auskunft (Art. 15 DSGVO), Berichtigung (Art. 16), Löschung (Art. 17), Einschränkung der Verarbeitung (Art. 18), '
    'Datenübertragbarkeit (Art. 20) sowie Widerspruch gegen Verarbeitungen auf Grundlage von Art. 6 Abs. 1 lit. f DSGVO (Art. 21). '
    f'Wenden Sie sich dazu an {MAIL}.</p>'
    '<p>Sie haben außerdem das Recht, sich bei einer Datenschutz-Aufsichtsbehörde zu beschweren. Zuständig ist das Bayerische Landesamt für '
    'Datenschutzaufsicht (BayLDA), Promenade 18, 91522 Ansbach, '
    '<a href="https://www.lda.bayern.de" target="_blank" rel="noopener noreferrer">www.lda.bayern.de</a>.</p>'
    '<p>Stand: Oktober 2026</p>')


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
<section class="newsletter"><h2>Dein nächster Einstieg im Postfach.</h2><p>Newsletter kommt bald.</p></section>
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
               '<p>Unternehmen können die Entfernung ihrer Einträge oder die Aufnahme ihres Feeds anfordern. Kontakt: ' + MAIL + '.</p>')
    (SITE / 'quellen.html').write_text(page('Quellen', sources), encoding='utf-8')

    pricing = ('<h1>Talente für KI gewinnen.</h1><p class="note">Vorläufige Preise – Buchung derzeit per E-Mail.</p><div class="grid">'
               '<article class="card"><h2>Basis</h2><p class="price">49 €</p><p>30 Tage</p></article>'
               '<article class="card"><h2>Plus</h2><p class="price">89 €</p><p>60 Tage, hervorgehoben, im Newsletter</p></article>'
               '<article class="card"><h2>Premium</h2><p class="price">149 €</p><p>90 Tage, oben angepinnt, Newsletter + Social Post</p></article></div>'
               '<p>Alle Preise netto zzgl. MwSt.</p><p>Kostenlose Einträge für Hochschulen und gemeinnützige Hackathons.</p><p>Kontakt: ' + MAIL + '</p>')
    (SITE / 'stelle-veroeffentlichen.html').write_text(page('Stelle veröffentlichen', pricing), encoding='utf-8')
    (SITE / 'impressum.html').write_text(page('Impressum', IMPRESSUM), encoding='utf-8')
    (SITE / 'datenschutz.html').write_text(page('Datenschutz', DATENSCHUTZ), encoding='utf-8')
    print(f'Statische Website erstellt: {SITE}')


if __name__ == '__main__':
    main()
