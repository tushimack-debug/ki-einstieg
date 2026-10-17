#!/usr/bin/env python3
"""Wöchentlicher Newsletter-Versand über Brevo, mit Job-Alarm-Segmenten.

Nutzung:
  python3 newsletter/send_campaign.py                       # Dry run (Standard): baut alle Ausgaben, zeigt Segmente, ändert/sendet nichts
  python3 newsletter/send_campaign.py --test-to ADR [--segment typ|stadt]   # Kampagnen-Entwurf ohne Liste + Brevo-Testmail NUR an ADR
  python3 newsletter/send_campaign.py --send                # echter Versand (nur aus dem Wochen-Workflow)
Optionen: --week YYYY-Www (Standard: zuletzt abgeschlossene ISO-Woche, Europe/Berlin), --live-data (jobs/events von der Website laden)

Job-Alarm (Design):
  * Leser:innen wählen im Anmeldeformular optional Einstiegsart (ALARM_TYP) und Stadt (ALARM_STADT). Das sind Brevo-Kontaktattribute;
    die Anmeldung läuft über dasselbe Brevo-Formular mit Double-Opt-in in dieselbe Liste (list_id).
  * Beim Versand liest das Skript die Liste, gruppiert die Kontakte nach (Typ, Stadt) und gleicht pro Kombination eine
    Brevo-Unterliste "Job-Alarm <typ>|<stadt>" im Ordner "<Marke> Job-Alarm" ab (hinzufügen/entfernen).
  * Pro Kombination mit Abonnent:innen geht eine Kampagne an die Unterliste (persönlicher Alarm-Block oben + allgemeine Auswahl);
    alle anderen bekommen die allgemeine Ausgabe an die Hauptliste, mit den Unterlisten als Ausschluss. Jede Person bekommt genau eine Mail.
  * Abmelden in irgendeiner Ausgabe sperrt die Adresse in Brevo global (blacklist) → sie fällt aus allen Listen.

Echter Versand nur, wenn: tracking_anonymous == true, Hauptliste >= 1 Abonnent:in, Woche >= 1 neue Stelle,
und die jeweilige Kampagne existiert noch nicht (kein Doppelversand). API-Schlüssel nur aus BREVO_API_KEY."""
import argparse, json, os, subprocess, sys, urllib.error, urllib.request
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
BRAND_CFG = json.loads((ROOT / 'data/brand.json').read_text(encoding='utf-8'))
BRAND = BRAND_CFG['name']
SITE_URL = BRAND_CFG['site_url'].rstrip('/')
sys.path.insert(0, str(ROOT / 'build'))
import seo  # noqa: E402

API = 'https://api.brevo.com/v3'
SENDER = {'name': BRAND, 'email': 'tushimack@gmail.com'}
TYPES = {t[0] for t in seo.TYPES if t[0] in ('werkstudent', 'praktikum', 'abschlussarbeit', 'duales-studium-ausbildung', 'junior', 'machine-learning', 'data-science-werkstudent')}
CITIES = {c[0] for c in seo.CITIES}
DAILY_LIMIT = int(os.environ.get('BREVO_DAILY_LIMIT', '300'))  # Brevo-Free-Plan


def brevo(method, path, body=None):
    key = os.environ.get('BREVO_API_KEY', '').strip()
    if not key:
        raise SystemExit('BREVO_API_KEY fehlt')
    req = urllib.request.Request(API + path, method=method, data=None if body is None else json.dumps(body).encode(),
                                 headers={'api-key': key, 'accept': 'application/json', 'content-type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            raw = r.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raise SystemExit(f'Brevo {method} {path.split("?")[0]}: HTTP {e.code} {e.read().decode(errors="replace")[:500]}')


def fetch_live():
    for name in ('jobs.json', 'events.json'):
        with urllib.request.urlopen(f'{SITE_URL}/data/{name}', timeout=60) as r:
            (ROOT / 'data' / name).write_bytes(r.read())


def list_contacts(list_id):
    out, offset = [], 0
    while True:
        page = brevo('GET', f'/contacts/lists/{list_id}/contacts?limit=500&offset={offset}').get('contacts', [])
        out += page
        if len(page) < 500:
            return out
        offset += 500


def segment_of(contact):
    a = contact.get('attributes') or {}
    typ = str(a.get('ALARM_TYP') or '').strip().lower()
    stadt = str(a.get('ALARM_STADT') or '').strip().lower()
    return (typ if typ in TYPES else 'alle', stadt if stadt in CITIES else 'alle')


def build(week, seg=None):
    args = [sys.executable, str(ROOT / 'newsletter/make_newsletter.py'), week] + ([f'{seg[0]}|{seg[1]}'] if seg else [])
    subprocess.run(args, check=True, stdout=subprocess.DEVNULL)
    suffix = f'.{seg[0]}-{seg[1]}' if seg else ''
    meta = json.loads((ROOT / f'newsletter/{week}{suffix}.meta.json').read_text())
    html = (ROOT / f'newsletter/{week}{suffix}.html').read_text()
    assert '{{ unsubscribe }}' in html and 'Pfälzer Straße 20b' in html, 'Abmeldelink/Impressum fehlen'
    return meta, html


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group()
    g.add_argument('--send', action='store_true')
    g.add_argument('--test-to')
    ap.add_argument('--segment', help='typ|stadt für --test-to, z. B. werkstudent|muenchen')
    ap.add_argument('--week')
    ap.add_argument('--live-data', action='store_true')
    a = ap.parse_args()

    cfg = json.loads((ROOT / 'data/newsletter.json').read_text())
    list_id = int(cfg['list_id'])
    now = datetime.now(ZoneInfo('Europe/Berlin'))
    week = a.week or '%d-W%02d' % (now.date() - timedelta(days=7)).isocalendar()[:2]
    if a.live_data or not (ROOT / 'data/jobs.json').exists():
        fetch_live()
    summary = os.environ.get('GITHUB_STEP_SUMMARY')

    def report(line):
        print(line)
        if summary:
            with open(summary, 'a') as f:
                f.write(line + '\n')

    meta, html = build(week)
    base = f'{BRAND} Weekly {week}'
    payload = lambda name, subject, body: {'name': name, 'subject': subject, 'sender': SENDER, 'replyTo': SENDER['email'],
                                           'htmlContent': body, 'inlineImageActivation': False, 'mirrorActive': True}

    if a.test_to:
        seg = tuple(a.segment.split('|', 1)) if a.segment else None
        if seg:
            meta, html = build(week, seg)
        p = payload(f'{base}{" [" + "|".join(seg) + "]" if seg else ""} [TEST]', meta['subject'], html)  # ohne Empfängerliste
        cid = brevo('POST', '/emailCampaigns', p)['id']
        brevo('POST', f'/emailCampaigns/{cid}/sendTest', {'emailTo': [a.test_to]})
        report(f'Testmail an {a.test_to} angestoßen (Entwurf {cid}, Segment {a.segment or "allgemein"}, geht nicht an eine Liste).')
        return

    contacts = [c for c in list_contacts(list_id) if not c.get('emailBlacklisted')]
    groups = defaultdict(list)
    for c in contacts:
        groups[segment_of(c)].append(c['email'])
    personal = {k: v for k, v in groups.items() if k != ('alle', 'alle')}
    existing = brevo('GET', '/emailCampaigns?limit=100&sort=desc').get('campaigns', [])
    sent_names = {c['name'] for c in existing if c.get('status') in ('sent', 'queued', 'in_process')}
    checks = {'mind. 1 Abonnent:in': len(contacts) >= 1, 'mind. 1 neue Stelle': meta['new_jobs'] >= 1,
              'anonyme Messung aktiv (tracking_anonymous)': cfg.get('tracking_anonymous') is True}
    print(f"Woche {week}: {meta['new_jobs']} neue Stellen, Liste {list_id}: {len(contacts)} aktive Abonnent:innen, "
          f"davon {sum(map(len, personal.values()))} mit Job-Alarm in {len(personal)} Segment(en)")
    for (t, s), emails in sorted(personal.items()):
        print(f'  Segment {t}|{s}: {len(emails)}')
    for k, v in checks.items():
        print(f"  [{'x' if v else ' '}] {k}")
    if len(contacts) > DAILY_LIMIT:
        report(f'WARNUNG: {len(contacts)} Empfänger:innen > Tageslimit {DAILY_LIMIT} des Brevo-Plans.')
    for seg in personal:  # Ausgaben immer bauen (Artefakt / Dry run)
        build(week, seg)

    if not a.send:
        report(f'Dry run {week}: nichts geändert, nichts versendet. Bedingungen ' + ('erfüllt' if all(checks.values()) else 'NICHT erfüllt') + '.')
        return
    if not all(checks.values()):
        report(f'Kein Versand {week}: ' + ', '.join(k for k, v in checks.items() if not v) + ' nicht erfüllt.')
        return

    # Unterlisten abgleichen
    folder_name = f'{BRAND} Job-Alarm'
    folders = brevo('GET', '/contacts/folders?limit=50').get('folders', [])
    folder = next((f['id'] for f in folders if f['name'] == folder_name), None) or brevo('POST', '/contacts/folders', {'name': folder_name})['id']
    lists = {l['name']: l['id'] for l in brevo('GET', f'/contacts/folders/{folder}/lists?limit=50').get('lists', [])}
    seg_lists = {}
    for name, lid in lists.items():
        if name.startswith('Job-Alarm '):
            t, _, s = name[len('Job-Alarm '):].partition('|')
            seg_lists[(t, s)] = lid
    for seg in personal:
        if seg not in seg_lists:
            seg_lists[seg] = brevo('POST', '/contacts/lists', {'name': f'Job-Alarm {seg[0]}|{seg[1]}', 'folderId': folder})['id']
    for seg, lid in seg_lists.items():
        want = set(personal.get(seg, []))
        have = {c['email'] for c in list_contacts(lid)}
        for chunk in (lambda xs: [xs[i:i + 150] for i in range(0, len(xs), 150)])(sorted(have - want)):
            brevo('POST', f'/contacts/lists/{lid}/contacts/remove', {'emails': chunk})
        for chunk in (lambda xs: [xs[i:i + 150] for i in range(0, len(xs), 150)])(sorted(want - have)):
            brevo('POST', f'/contacts/lists/{lid}/contacts/add', {'emails': chunk})

    def send(name, subject, body, recipients):
        if name in sent_names:
            report(f'Übersprungen (schon versendet): {name}')
            return
        draft = next((c for c in existing if c.get('name') == name and c.get('status') == 'draft'), None)
        p = payload(name, subject, body) | {'recipients': recipients}
        if draft:
            cid = draft['id']
            brevo('PUT', f'/emailCampaigns/{cid}', {k: v for k, v in p.items() if k != 'name'})
        else:
            cid = brevo('POST', '/emailCampaigns', p)['id']
        brevo('POST', f'/emailCampaigns/{cid}/sendNow')
        report(f'Versendet: {name} (Kampagne {cid})')

    for seg, emails in sorted(personal.items()):
        m, body = build(week, seg)
        send(f'{base} [{seg[0]}|{seg[1]}]', m['subject'], body, {'listIds': [seg_lists[seg]]})
    general = groups.get(('alle', 'alle'), [])
    if general:
        excl = [seg_lists[s] for s in personal]
        send(base, meta['subject'], html, {'listIds': [list_id]} | ({'exclusionListIds': excl} if excl else {}))


if __name__ == '__main__':
    main()
