"""Politely fetch and cache descriptions for entry-level candidates."""
import base64
import json
import os
import re
import time
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from classify import RULES
from common import ROOT, cache_path, write_json
from fetch_jobs import HEADERS


def main():
    if os.environ.get('USE_BA') != '1' or not os.environ.get('BA_USER_AGENT'):
        print('BA-Pfad deaktiviert: USE_BA=1 und BA_USER_AGENT sind erforderlich.')
        raise SystemExit(3)
    rows = json.loads((ROOT / 'data/raw_jobs.json').read_text())
    candidates = {str(r['referenznummer']): r for r in rows if r.get('referenznummer') and (any(re.search(pattern, str(r.get('stellenangebotsTitel') or ''), re.I) for _, pattern in RULES) or r.get('stellenangebotsart') in ('PRAKTIKUM_TRAINEE', 'AUSBILDUNG'))}
    cached = fetched = errors = consecutive = 0
    limit = max(0, int(os.environ.get('MAX_DETAILS', '2000')))
    for refnr in candidates:
        path = cache_path(refnr)
        try:
            if json.loads(path.read_text()).get('status') in ('ok', 'gone'):
                cached += 1
                continue
        except (OSError, ValueError):
            pass
        if fetched >= limit or consecutive >= 20:
            continue
        if fetched:
            time.sleep(0.5)
        record = dict(refnr=refnr, fetched_at=datetime.now(timezone.utc).isoformat(), status='error', description='', allianzpartnerName=None, allianzpartnerUrl=None)
        try:
            encoded = quote(base64.b64encode(refnr.encode()).decode(), safe='')
            with urlopen(Request('https://rest.arbeitsagentur.de/jobboerse/jobsuche-service/pc/v4/jobdetails/' + encoded, headers=HEADERS), timeout=20) as response:
                payload = json.load(response)
            record.update(status='ok', description=str(payload.get('stellenangebotsBeschreibung') or ''), allianzpartnerName=payload.get('allianzpartnerName'), allianzpartnerUrl=payload.get('allianzpartnerUrl'))
            consecutive = 0
        except HTTPError as exc:
            if exc.code == 404:
                record['status'] = 'gone'
                consecutive = 0
            else:
                errors += 1
                consecutive += 1
                print(f'Detail {refnr}: {exc}', flush=True)
        except (URLError, OSError, ValueError, TypeError, AttributeError) as exc:
            errors += 1
            consecutive += 1
            print(f'Detail {refnr}: {exc}', flush=True)
        write_json(path, record)
        fetched += 1
        if fetched % 50 == 0:
            print(f'Details: {fetched} geladen, {errors} Fehler', flush=True)
    summary = dict(candidates=len(candidates), cached=cached, fetched_now=fetched, errors=errors)
    write_json(ROOT / 'data/details_summary.json', summary)
    print('Details: ' + ', '.join(f'{k}={v}' for k, v in summary.items()), flush=True)
    return 2 if consecutive >= 20 else 0


if __name__ == '__main__':
    raise SystemExit(main())
