#!/usr/bin/env python3
"""Wöchentlicher Newsletter-Versand über Brevo.

Nutzung:
  python3 newsletter/send_campaign.py                 # Dry run (Standard): baut den Newsletter, prüft Bedingungen, sendet nichts
  python3 newsletter/send_campaign.py --test-to ADR   # legt einen Kampagnen-Entwurf an und schickt NUR eine Brevo-Testmail an ADR
  python3 newsletter/send_campaign.py --send          # echter Versand an die Liste (nur aus dem Wochen-Workflow)
Optionen: --week YYYY-Www (Standard: die zuletzt abgeschlossene ISO-Woche, Europe/Berlin), --live-data (jobs/events von der Website laden)

Echter Versand nur, wenn ALLE Bedingungen erfüllt sind:
  * data/newsletter.json: tracking_anonymous == true (anonyme Öffnungs-/Klickmessung in Brevo aktiviert)
  * die Liste hat mindestens 1 Abonnent:in
  * die Woche hat mindestens 1 neue Stelle
  * für diese Woche existiert noch keine Kampagne (kein Doppelversand)
API-Schlüssel nur aus der Umgebungsvariable BREVO_API_KEY (wird nie ausgegeben)."""
import argparse, json, os, subprocess, sys, urllib.error, urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
BRAND_CFG = json.loads((ROOT / 'data/brand.json').read_text(encoding='utf-8'))
BRAND = BRAND_CFG['name']
SITE_URL = BRAND_CFG['site_url'].rstrip('/')
API = 'https://api.brevo.com/v3'
SENDER = {'name': BRAND, 'email': 'tushimack@gmail.com'}


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
        raise SystemExit(f'Brevo {method} {path}: HTTP {e.code} {e.read().decode(errors="replace")[:500]}')


def fetch_live():
    for name in ('jobs.json', 'events.json'):
        with urllib.request.urlopen(f'{SITE_URL}/data/{name}', timeout=60) as r:
            (ROOT / 'data' / name).write_bytes(r.read())


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group()
    g.add_argument('--send', action='store_true')
    g.add_argument('--test-to')
    ap.add_argument('--week')
    ap.add_argument('--live-data', action='store_true')
    a = ap.parse_args()

    cfg = json.loads((ROOT / 'data/newsletter.json').read_text())
    list_id = int(cfg['list_id'])
    now = datetime.now(ZoneInfo('Europe/Berlin'))
    week = a.week or '%d-W%02d' % (now.date() - timedelta(days=7)).isocalendar()[:2]
    if a.live_data or not (ROOT / 'data/jobs.json').exists():
        fetch_live()
    subprocess.run([sys.executable, str(ROOT / 'newsletter/make_newsletter.py'), week], check=True)
    meta = json.loads((ROOT / f'newsletter/{week}.meta.json').read_text())
    html = (ROOT / f'newsletter/{week}.html').read_text()
    assert '{{ unsubscribe }}' in html and 'Pfälzer Straße 20b' in html, 'Abmeldelink/Impressum fehlen'

    lst = brevo('GET', f'/contacts/lists/{list_id}')
    subs = int(lst.get('totalSubscribers') or 0)
    name = f'{BRAND} Weekly {week}'
    existing = [c for c in brevo('GET', '/emailCampaigns?limit=100&sort=desc').get('campaigns', []) if c.get('name') == name]
    checks = {'mind. 1 Abonnent:in': subs >= 1, 'mind. 1 neue Stelle': meta['new_jobs'] >= 1,
              'anonyme Messung aktiv (tracking_anonymous)': cfg.get('tracking_anonymous') is True,
              'noch nicht versendet': not any(c.get('status') in ('sent', 'queued', 'in_process') for c in existing)}
    print(f"Woche {week}: {meta['new_jobs']} neue Stellen, {meta['picked']} im Newsletter, Liste {list_id} ({lst.get('name')}): {subs} Abonnent:innen")
    for k, v in checks.items():
        print(f"  [{'x' if v else ' '}] {k}")
    summary = os.environ.get('GITHUB_STEP_SUMMARY')

    def report(line):
        print(line)
        if summary:
            with open(summary, 'a') as f:
                f.write(line + '\n')

    payload = {'name': name, 'subject': meta['subject'], 'sender': SENDER, 'replyTo': SENDER['email'],
               'htmlContent': html, 'recipients': {'listIds': [list_id]}, 'inlineImageActivation': False, 'mirrorActive': True}

    if a.test_to:
        payload['name'] = name + ' [TEST]'
        payload.pop('recipients')  # Test-Entwurf ohne Empfängerliste: kann nie an die Liste gehen
        cid = brevo('POST', '/emailCampaigns', payload)['id']
        brevo('POST', f'/emailCampaigns/{cid}/sendTest', {'emailTo': [a.test_to]})
        report(f'Testmail an {a.test_to} angestoßen (Kampagnen-Entwurf {cid}, wird nicht an die Liste versendet).')
        return
    if not a.send:
        report(f'Dry run {week}: nichts versendet. Bedingungen ' + ('erfüllt' if all(checks.values()) else 'NICHT erfüllt') + '.')
        return
    if not all(checks.values()):
        report(f'Kein Versand {week}: ' + ', '.join(k for k, v in checks.items() if not v) + ' nicht erfüllt.')
        return
    draft = next((c for c in existing if c.get('status') == 'draft'), None)
    cid = draft['id'] if draft else brevo('POST', '/emailCampaigns', payload)['id']
    if draft:
        brevo('PUT', f'/emailCampaigns/{cid}', {k: v for k, v in payload.items() if k != 'name'})
    brevo('POST', f'/emailCampaigns/{cid}/sendNow')
    report(f'Versendet: Kampagne {cid} ({name}) an Liste {list_id} mit {subs} Abonnent:innen.')


if __name__ == '__main__':
    main()
