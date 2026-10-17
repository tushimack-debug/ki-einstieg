"""Fetch public BA listings; standard library only."""
import os
import json
import sys
import time
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import URLError

ROOT = Path(__file__).resolve().parents[1]
KEYWORDS = ['KI', 'Künstliche Intelligenz', 'Machine Learning', 'Data Science', 'Data Scientist', 'LLM', 'Deep Learning', 'AI', 'Werkstudent KI', 'Werkstudent Machine Learning', 'Werkstudent Data Science', 'Praktikum KI', 'Abschlussarbeit KI', 'Masterarbeit Machine Learning', 'Bachelorarbeit KI', 'Duales Studium Data Science', 'Duales Studium Informatik KI']
HEADERS = {'X-API-Key': 'jobboerse-jobsuche', 'User-Agent': os.environ.get('BA_USER_AGENT', ''), 'Accept': 'application/json'}


def main():
    if os.environ.get('USE_BA') != '1' or not os.environ.get('BA_USER_AGENT'):
        print('BA-Pfad deaktiviert: USE_BA=1 und BA_USER_AGENT sind erforderlich.')
        raise SystemExit(3)
    jobs = {}
    successful = 0
    errors = 0
    first = True
    for keyword in KEYWORDS:
        for kind in (34, 4, 1):
            for page in range(1, 4):
                if not first:
                    time.sleep(0.5)
                first = False
                query = urlencode(dict(was=keyword, angebotsart=kind, size=50, page=page, veroeffentlichtseit=60))
                request = Request('https://rest.arbeitsagentur.de/jobboerse/jobsuche-service/pc/v6/jobs?' + query, headers=HEADERS)
                try:
                    with urlopen(request, timeout=20) as response:
                        payload = json.load(response)
                    rows = payload.get('ergebnisliste', [] if str(payload.get('maxErgebnisse')) == '0' else None)
                    if not isinstance(rows, list):
                        raise ValueError('Antwort enthält keine ergebnisliste')
                    successful += 1
                except (URLError, TimeoutError, OSError, ValueError) as exc:
                    errors += 1
                    print(f'Warnung: {keyword} / {kind} / {page}: {exc}', file=sys.stderr, flush=True)
                    break
                for row in rows:
                    if isinstance(row, dict) and row.get('referenznummer'):
                        jobs[str(row['referenznummer'])] = row
                print(f'{keyword} / {kind} / {page}: {len(rows)} Treffer', flush=True)
                if len(rows) < 50:
                    break
    if not successful:
        raise SystemExit('Kein API-Abruf erfolgreich; vorhandene Daten bleiben erhalten.')
    path = ROOT / 'data/raw_jobs.json'
    path.parent.mkdir(exist_ok=True)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(list(jobs.values()), ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temporary.replace(path)
    print(f'{len(jobs)} eindeutige Stellen gespeichert; {errors} fehlgeschlagene Abfragen.', flush=True)


if __name__ == '__main__':
    main()
