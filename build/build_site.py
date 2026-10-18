#!/usr/bin/env python3
"""Build the static job-board site (brand name: data/brand.json) from data/jobs.json, data/events.json, data/companies.json.
Usage: python3 build/build_site.py [OUTPUT_DIR]   (or SITE_DIR env; default ./site)"""
import json, os, shutil, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import seo
from collections import Counter
from datetime import datetime
from html import escape
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'pipeline'))
from optout import is_opted_out

SITE = Path(sys.argv[1] if len(sys.argv) > 1 else os.environ.get('SITE_DIR', ROOT / 'site'))
ICON = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Crect width='64' height='64' rx='14' fill='%23144948'/%3E%3Ctext x='10' y='44' font-size='36' fill='white'%3EKI%3C/text%3E%3C/svg%3E"
ATS = 'Personio, Greenhouse, Lever, SmartRecruiters, Ashby, Recruitee, Workable, SAP SuccessFactors (RSS)'
BRAND_CFG = json.loads((ROOT / 'data' / 'brand.json').read_text(encoding='utf-8'))
BRAND = BRAND_CFG['name']
SITE_URL = BRAND_CFG['site_url'].rstrip('/')
BASE = (urlparse(SITE_URL).path.rstrip('/') or '') + '/'
CONTACT = 'tushimack@gmail.com'
MAIL = f'<a href="mailto:{CONTACT}">{CONTACT}</a>'
IMPRESSUM = (
    '<h1>Impressum</h1>'
    '<h2>Angaben gemäß § 5 DDG</h2>'
    '<p>Tom Mack<br>Pfälzer Straße 20b<br>91052 Erlangen<br>Deutschland</p>'
    f'<h2>Kontakt</h2><p>E-Mail: {MAIL}</p>'
    f'<p>{BRAND} wird von einer Privatperson betrieben. Eine Umsatzsteuer-Identifikationsnummer ist derzeit nicht vorhanden.</p>'
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
    'von Drittanbietern ein. Nur wenn Sie das Newsletter-Formular absenden, wird Ihre Eingabe an Brevo übermittelt (siehe Abschnitt 6). Die Stellenfilter laufen vollständig lokal in Ihrem Browser.</p>'
    '<p>Die Schrift wird lokal über Systemschriften geladen; es werden keine Google Fonts oder anderen externen Einbettungen verwendet.</p>'
    '<h2>4. Externe Links</h2>'
    '<p>Stellenanzeigen verlinken auf die Seiten der jeweiligen Arbeitgeber. Erst wenn Sie einen solchen Link anklicken, werden Daten an den '
    'jeweiligen Anbieter übertragen; dafür gilt dessen Datenschutzerklärung.</p>'
    '<h2>5. Kontakt per E-Mail</h2>'
    '<p>Wenn Sie uns per E-Mail kontaktieren, verarbeiten wir Ihre Angaben (E-Mail-Adresse, Inhalt der Nachricht), um Ihre Anfrage zu beantworten '
    '(Art. 6 Abs. 1 lit. b bzw. f DSGVO). Die Daten werden gelöscht, sobald sie dafür nicht mehr erforderlich sind und keine gesetzlichen Aufbewahrungspflichten bestehen. '
    'Für den E-Mail-Empfang nutzen wir Google Mail (Google Ireland Limited).</p>'
    '<h2 id="newsletter">6. Newsletter (Brevo)</h2>'
    '<p><strong>Zweck und Daten.</strong> Mit unserem kostenlosen Newsletter informieren wir einmal pro Woche über neue Einstiegsstellen im Bereich KI '
    'sowie über Hackathons und Veranstaltungen. Für die Anmeldung benötigen wir nur Ihre E-Mail-Adresse.</p>'
    '<p><strong>Job-Alarm (optional).</strong> Wenn Sie im Formular eine Einstiegsart und/oder eine Stadt auswählen, speichern wir diese Auswahl '
    'zusammen mit Ihrer E-Mail-Adresse bei Brevo und ordnen Sie einer entsprechenden Empfängergruppe zu, damit passende Stellen oben in Ihrer '
    'wöchentlichen Ausgabe stehen. Die Auswahl ist freiwillig; Sie können sie jederzeit ändern (erneut mit neuer Auswahl anmelden) oder per E-Mail '
    'löschen lassen. Es werden dafür keine weiteren Daten erhoben und kein Profil über Ihr Leseverhalten gebildet.</p>'
    '<p><strong>Rechtsgrundlage.</strong> Der Versand erfolgt ausschließlich mit Ihrer Einwilligung (Art. 6 Abs. 1 lit. a DSGVO). '
    'Sie können die Einwilligung jederzeit mit Wirkung für die Zukunft widerrufen, z. B. über den Abmeldelink in jeder Ausgabe oder per E-Mail an '
    f'{MAIL}. Die Rechtmäßigkeit der bis zum Widerruf erfolgten Verarbeitung bleibt unberührt.</p>'
    '<p><strong>Double-Opt-in und Protokollierung.</strong> Nach dem Absenden des Formulars erhalten Sie eine E-Mail mit einem Bestätigungslink. '
    'Erst wenn Sie diesen Link anklicken, werden Sie in den Verteiler aufgenommen. Damit wir die Einwilligung nachweisen können, werden der Zeitpunkt '
    'der Anmeldung und der Bestätigung sowie die dabei verwendete IP-Adresse protokolliert. Unbestätigte Anmeldungen erhalten keinen Newsletter.</p>'
    '<p><strong>Dienstleister.</strong> Für Anmeldung und Versand nutzen wir Brevo, einen Dienst der Sendinblue GmbH, Köpenicker Straße 126, '
    '10179 Berlin, Deutschland. Das Anmeldeformular sendet Ihre Eingabe direkt an Brevo; Brevo verarbeitet Ihre Daten in unserem Auftrag und '
    'speichert sie auf Servern in der EU. Mit Brevo besteht ein Vertrag zur Auftragsverarbeitung (Art. 28 DSGVO), der Bestandteil der '
    'Nutzungsbedingungen von Brevo ist. Weitere Informationen: '
    '<a href="https://www.brevo.com/de/legal/privacypolicy/" target="_blank" rel="noopener noreferrer">Datenschutzerklärung von Brevo</a>.</p>'
    '<p><strong>Öffnungs- und Klickmessung.</strong> Brevo kann standardmäßig erfassen, ob ein Newsletter geöffnet und welche Links angeklickt wurden. '
    'Über die Schnittstelle (API) lässt sich diese Messung pro Kampagne nicht abschalten. '
    '{TRACKING}'
    'Öffnungen und Klicks werden dann nur als Gesamtzahlen erfasst und nicht Ihrer Person oder E-Mail-Adresse zugeordnet. Wir erstellen keine '
    'individuellen Nutzerprofile.</p>'
    '<p><strong>Speicherdauer.</strong> Ihre E-Mail-Adresse speichern wir, bis Sie sich abmelden. Nach der Abmeldung wird die Adresse aus dem '
    'Verteiler entfernt; die Adresse und der Nachweis der früheren Einwilligung können bis zu drei Jahre gespeichert bleiben, damit wir die frühere '
    'Einwilligung belegen und eine erneute Zusendung ausschließen können (Art. 6 Abs. 1 lit. c und f DSGVO). '
    'Auf unserer Website werden für die Anmeldung keine Cookies gesetzt und keine Skripte von Brevo geladen.</p>'
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


def page(title, body, *, path='', description=None, robots='index,follow', jsonld=None, full_title=None, og_type='website'):
    """path: URL path relative to the site root ('' = home, 'werkstudent/muenchen/' = clean URL directory)."""
    full = full_title or f'{title} · {BRAND}'
    desc = description or BRAND_CFG['description']
    url = f'{SITE_URL}/{path}'
    ld = ''.join(f'<script type="application/ld+json">{json.dumps(x, ensure_ascii=False).replace("</", "<\\/")}</script>' for x in (jsonld or []))
    meta = (f'<meta name="description" content="{escape(desc)}"><meta name="robots" content="{robots}">'
            f'<link rel="canonical" href="{escape(url)}">'
            f'<meta property="og:type" content="{og_type}"><meta property="og:site_name" content="{escape(BRAND)}"><meta property="og:locale" content="de_DE">'
            f'<meta property="og:title" content="{escape(full)}"><meta property="og:description" content="{escape(desc)}"><meta property="og:url" content="{escape(url)}">'
            '<meta name="twitter:card" content="summary">')
    return f'''<!doctype html>
<html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<base href="{BASE}"><title>{escape(full)}</title>{meta}
<link rel="icon" href="{ICON}"><link rel="stylesheet" href="assets/style.css">{ld}</head>
<body><header class="wrap"><a class="brand" href="./">{escape(BRAND)}<span aria-hidden="true"> ↗</span></a><nav aria-label="Hauptnavigation"><a href="./#stellen">Stellen entdecken</a><a href="./#events">Hackathons</a><a href="stelle-veroeffentlichen.html">Stelle veröffentlichen</a></nav></header>
<main class="wrap">{body}</main><footer class="wrap"><p>{escape(BRAND)}: Stellen aus den öffentlichen Karriere-Seiten bzw. Job-Feeds der Unternehmen ({ATS}). Alle Rechte an den Anzeigen liegen bei den jeweiligen Unternehmen. Bewerbung immer direkt beim Unternehmen.</p><nav aria-label="Rechtliches"><a href="entfernen/">Eintrag entfernen</a><a href="quellen.html">Quellen</a><a href="impressum.html">Impressum</a><a href="datenschutz.html">Datenschutz</a><a href="stelle-veroeffentlichen.html">Stelle veröffentlichen</a></nav></footer></body></html>'''


def newsletter_html(action):
    head = '<section class="newsletter" id="newsletter"><h2>Dein nächster Einstieg im Postfach.</h2>'
    if not action.startswith('https://') or 'sibforms.com/' not in action:
        return head + '<p>Newsletter kommt bald.</p></section>'
    # Plain HTML form, posts directly to Brevo's hosted form endpoint: no API key, no Brevo script, no cookies on this site.
    # ALARM_TYP / ALARM_STADT are Brevo contact attributes (text); slugs match build/seo.py and newsletter/send_campaign.py.
    alarm_types = ''.join(f'<option value="{t[0]}">{escape(t[1])}</option>' for t in seo.TYPES)
    alarm_cities = ''.join(f'<option value="{c[0]}">{escape(c[1])}</option>' for c in seo.CITIES)
    return (head + '<p>Einmal pro Woche: neue KI-Einstiegsstellen (Werkstudent, Praktikum, Abschlussarbeit, Ausbildung) und Hackathons. Kostenlos, jederzeit abbestellbar.</p>'
            f'<form class="signup" method="post" action="{escape(action)}" accept-charset="utf-8">'
            '<label for="nl-email">E-Mail-Adresse</label><div class="email-row">'
            '<input id="nl-email" type="email" name="EMAIL" required autocomplete="email" placeholder="du@beispiel.de">'
            '<button type="submit">Anmelden</button></div>'
            '<details class="alarm"><summary>Optional: persönlicher Job-Alarm</summary><p>Wähle Einstiegsart und/oder Stadt. Passende neue Stellen stehen dann oben in deiner wöchentlichen Mail.</p><div class="alarm-row">'
            f'<label>Einstiegsart<select name="ALARM_TYP"><option value="">Alle</option>{alarm_types}</select></label>'
            f'<label>Stadt<select name="ALARM_STADT"><option value="">Alle</option>{alarm_cities}</select></label></div></details>'
            '<input type="text" name="email_address_check" value="" tabindex="-1" autocomplete="off" aria-hidden="true" class="hp">'
            '<input type="hidden" name="locale" value="de">'
            f'<p class="consent">Mit dem Absenden willigst du ein, dass wir dir den {escape(BRAND)}-Newsletter per E-Mail schicken. Du bekommst zuerst eine '
            'Bestätigungsmail (Double-Opt-in); erst nach deinem Klick wirst du eingetragen. Versand über Brevo (Sendinblue GmbH, Berlin). '
            'Wenn du einen Job-Alarm wählst, speichern wir diese Auswahl, um deine Mail anzupassen. '
            'Abmelden geht jederzeit über den Link in jeder Mail. Details in der <a href="datenschutz.html#newsletter">Datenschutzerklärung</a>.</p>'
            '</form></section>')


def simple_page(title, heading, text, path):
    return page(title, path=path, robots='noindex,follow', body=f'<section class="hero"><p class="eyebrow">NEWSLETTER</p><h1>{heading}</h1><p class="tagline">{text}</p>'
                       '<p><a href="./#stellen">Zu den Stellen →</a></p></section>')


def options(values):
    return ''.join(f'<option value="{escape(v)}">{escape(v)}</option>' for v in values)


def main():
    jobs = load('jobs.json', [])
    events = load('events.json', [])
    companies = load('companies.json', [])
    stats = load('stats.json', {})
    excluded_names = {c['name'].casefold() for c in companies if is_opted_out(c)}
    companies = [c for c in companies if not is_opted_out(c)]
    jobs = [j for j in jobs if not is_opted_out(j) and j['company'].casefold() not in excluded_names and not seo.is_expired(j)]
    for j in jobs:
        j['retrieved'] = seo.retrieved_date(j, stats.get('generated_at'))
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
        note = f'<p class="event-note"><strong>Hinweis:</strong> {escape(e["status"])}</p>' if e.get('status') else ''
        return (f'<article class="card event-card"><h3>{escape(e["name"])}</h3><p class="event-when">{when} · {escape(e.get("city", ""))}</p>{note}'
                f'<p><strong>Für:</strong> {escape(e.get("audience", ""))}</p><p>{escape(e.get("description", ""))}</p>'
                f'<a href="{escape(e["url"])}" target="_blank" rel="noopener noreferrer" aria-label="Zur Veranstaltung {escape(e["name"])} (Quelle)">Zur Veranstaltung ↗</a></article>')

    seo_info = seo.generate(SITE, ROOT, jobs, companies, page, BRAND, SITE_URL)
    (SITE / 'data' / 'jobs.json').write_text(json.dumps(jobs, ensure_ascii=False, indent=1), encoding='utf-8')
    lbl = seo_info['label']
    def hub(keys):
        return ''.join(f'<li><a href="{v["path"]}">{escape(lbl(*k)[0])}</a> ({len(v["jobs"])})</li>' for k, v in keys)
    il = seo_info['index_links']
    popular = (f'<section id="suchen" class="links"><h2>Beliebte Suchen</h2><div class="link-cols">'
               f'<div><h3>Nach Einstiegsart</h3><ul class="link-list">{hub([x for x in il if x[0][1] is None])}</ul></div>'
               f'<div><h3>Nach Stadt</h3><ul class="link-list">{hub([x for x in il if x[0][0] is None])}</ul></div>'
               f'<div><h3>Einstiegsart × Stadt</h3><ul class="link-list">{hub(sorted([x for x in il if x[0][0] and x[0][1]], key=lambda x: -len(x[1]["jobs"]))[:16])}</ul></div>'
               '</div></section>')
    city_count = Counter(j['city'] for j in jobs if j.get('city'))
    city_opts = [c for c, n in city_count.most_common() if n >= 2]
    field_opts = [f for f, _ in Counter(f for j in jobs for f in j.get('fields', [])).most_common()]
    newsletter_section = newsletter_html(load('newsletter.json', {}).get('form_action', ''))
    slim = [{k: j.get(k) for k in ('title', 'company', 'city', 'region', 'type', 'remote', 'date', 'url', 'country', 'source_label', 'page', 'fields', 'ai_terms', 'retrieved', 'ats', 'featured')} for j in jobs]
    data = json.dumps(slim, ensure_ascii=False).replace('</', '<\\/').replace('&', '\\u0026')
    body = f'''<section class="hero"><p class="eyebrow">DEIN NÄCHSTER SCHRITT</p><h1>{escape(BRAND_CFG['slogan'])}</h1><p class="tagline">Werkstudent, Praktikum, Abschlussarbeit &amp; Ausbildung in KI – in Deutschland, Österreich und der Schweiz.</p><div class="metrics"><p><strong>{len(jobs)}</strong> Stellen</p><p><strong>{firms}</strong> Unternehmen</p><p><strong>{cities}</strong> Städte</p><p><strong>{updated}</strong> Letzte Aktualisierung</p></div></section>
<section id="stellen"><h2>Finde deinen Platz in der KI.</h2><form id="filters" class="filters"><label>Typ<select id="type"><option value="">Alle Typen</option>{options(types)}</select></label><label>Stadt<select id="city"><option value="">Alle Städte</option>{options(city_opts)}</select></label><label>Region<select id="region"><option value="">Alle Regionen</option>{options(regions)}</select></label><label>Fachgebiet<select id="field"><option value="">Alle Fachgebiete</option>{options(field_opts)}</select></label><label class="search">Suche: Titel, Firma, Ort oder Thema<input id="search" type="search" placeholder="z. B. LLM, Bosch oder Hamburg"></label><label class="check"><input id="remote" type="checkbox"> Remote/Homeoffice</label><label class="check"><input id="recent" type="checkbox"> Nur letzte 14 Tage</label></form><p id="result-count" role="status" aria-live="polite"></p><div id="jobs" class="grid"></div><button id="load-more" type="button" hidden>Mehr laden</button><noscript><p>Bitte JavaScript für die Stellenfilter aktivieren. Alle Stellen stehen auch als <a href="data/jobs.json">JSON-Datei</a> bereit.</p></noscript></section>
<section id="events"><p class="eyebrow">GEMEINSAM LOSLEGEN</p><h2>Hackathons &amp; Wettbewerbe</h2><div class="grid">{''.join(event_card(e) for e in events)}</div></section>
{popular}
{newsletter_section}
<script type="application/json" id="jobs-data">{data}</script><script src="assets/app.js" defer></script>'''
    (SITE / 'index.html').write_text(page('Stellen entdecken', body, full_title=f'{BRAND}: KI Jobs für Einsteiger – Werkstudent, Praktikum & Abschlussarbeit in KI/AI'), encoding='utf-8')

    per = Counter(j['company'] for j in jobs)
    def link(c): return f'<a href="{escape(c["careers_url"])}" target="_blank" rel="noopener noreferrer">{escape(c["name"])}</a>'
    with_jobs = sorted((c for c in companies if per.get(c['name'])), key=lambda c: (-per[c['name']], c['name'].casefold()))
    rows = ''.join(f'<li>{link(c)} · {escape(c["ats"])} · {per[c["name"]]} passende Stellen</li>' for c in with_jobs)
    others = ', '.join(link(c) for c in sorted((c for c in companies if not per.get(c['name'])), key=lambda c: c['name'].casefold()))
    rows += f'</ul><h2>Weitere beobachtete Feeds (derzeit ohne passende Einstiegsstelle)</h2><p class="small">{others}</p><ul>'
    sources = (f'<h1>Quellen</h1><p>{escape(BRAND)} liest ausschließlich öffentliche, zum Einbinden gedachte Job-Feeds der Unternehmen ({ATS}) und verlinkt immer auf die Originalanzeige beim Unternehmen. '
               f'Aktuell {len(companies)} Unternehmen, davon {len(per)} mit passenden Einstiegsstellen.</p><ul>{rows}</ul>'
               '<p>Unternehmen können die Entfernung ihrer Einträge oder die Aufnahme ihres Feeds anfordern. Kontakt: ' + MAIL + '.</p>')
    (SITE / 'quellen.html').write_text(page('Quellen', path='quellen.html', body=sources), encoding='utf-8')

    pricing = ('<h1>Talente für KI gewinnen.</h1><p class="note">Vorläufige Preise – Buchung derzeit per E-Mail.</p><div class="grid">'
               '<article class="card"><h2>Basis</h2><p class="price">49 €</p><p>30 Tage</p></article>'
               '<article class="card"><h2>Plus</h2><p class="price">89 €</p><p>60 Tage, hervorgehoben, im Newsletter</p></article>'
               '<article class="card"><h2>Premium</h2><p class="price">149 €</p><p>90 Tage, oben angepinnt, Newsletter + Social Post</p></article></div>'
               '<p>Alle Preise netto zzgl. MwSt.</p><p>Kostenlose Einträge für Hochschulen und gemeinnützige Hackathons.</p><p>Kontakt: ' + MAIL + '</p>')
    (SITE / 'stelle-veroeffentlichen.html').write_text(page('Stelle veröffentlichen', path='stelle-veroeffentlichen.html', body=pricing), encoding='utf-8')
    removal = (f'<h1>Eintrag entfernen oder korrigieren</h1><p>Unternehmen können die Entfernung ihrer Stellenanzeigen oder ihres gesamten Feeds '
               f'bei {escape(BRAND)} sowie Korrekturen per E-Mail anfordern: '
               f'<a href="mailto:{CONTACT}?subject=Entfernung%20KI-Laufbahn">{CONTACT}</a>. '
               'Bitte nennen Sie das Unternehmen und die betroffene URL.</p>'
               '<p>Wir entfernen die Einträge innerhalb von 48 Stunden nach Eingang Ihrer Anfrage und nehmen das Unternehmen in unsere '
               'Ausschlussliste auf, damit es nicht erneut importiert wird.</p>'
               f'<p>Für die Aufnahme Ihres Unternehmens oder Feeds in {escape(BRAND)} schreiben Sie ebenfalls an diese Adresse '
               'und nennen Sie den Firmennamen und die URL Ihrer Karriereseite bzw. Ihres öffentlichen Job-Feeds.</p>')
    (SITE / 'entfernen').mkdir(exist_ok=True)
    (SITE / 'entfernen' / 'index.html').write_text(page('Eintrag entfernen oder korrigieren', removal, path='entfernen/'), encoding='utf-8')
    (SITE / 'impressum.html').write_text(page('Impressum', IMPRESSUM, path='impressum.html', robots='noindex,follow'), encoding='utf-8')
    anon = load('newsletter.json', {}).get('tracking_anonymous') is True
    tracking = ('Wir haben deshalb in Brevo die anonyme Messung aktiviert: ' if anon else
                'Deshalb aktivieren wir in Brevo vor dem Versand der ersten Ausgabe die anonyme Messung; ohne sie wird kein Newsletter verschickt. ')
    (SITE / 'datenschutz.html').write_text(page('Datenschutz', DATENSCHUTZ.replace('{TRACKING}', tracking), path='datenschutz.html', robots='noindex,follow'), encoding='utf-8')
    (SITE / 'newsletter-bestaetigen.html').write_text(simple_page('Fast geschafft', 'Fast geschafft!',
        'Wir haben dir eine E-Mail geschickt. Bitte klicke auf den Bestätigungslink darin, erst dann bist du eingetragen. '
        'Nichts angekommen? Schau im Spam-Ordner nach.', 'newsletter-bestaetigen.html'), encoding='utf-8')
    (SITE / 'newsletter-danke.html').write_text(simple_page('Danke', 'Danke, du bist dabei!',
        'Deine Anmeldung ist bestätigt. Ab jetzt bekommst du jeden Montag neue KI-Einstiegsstellen und Hackathons. '
        'Abmelden kannst du dich jederzeit über den Link in jeder Mail.', 'newsletter-danke.html'), encoding='utf-8')
    print(f"Statische Website erstellt: {SITE} | {seo_info['jobs']} Stellenseiten ({seo_info['with_text']} mit Auszug), "
          f"{len(seo_info['landing'])} Landingpages ({seo_info['noindex']} noindex), Sitemap {seo_info['sitemap']} URLs")


if __name__ == '__main__':
    main()
