#!/usr/bin/env python3
"""Turn discovery/cc/probe_cc.json (+ sf_companies.json) into new data/companies.json entries.
Keeps feeds with >=1 DACH posting (Personio: >=1 posting in a known DACH city), resolves the company name
from the feed itself or the public board page title, and records evidence."""
import html, json, os, re, sys, time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from urllib.request import Request, urlopen
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'pipeline'))
os.environ.setdefault('MAX_DETAILS', '0')
import fetch_feeds as ff
from geo import CITY, key, fill_region

UA = ff.UA
CAREERS = {'personio': 'https://{s}.jobs.personio.de/', 'greenhouse': 'https://job-boards.greenhouse.io/{s}', 'lever': 'https://jobs.lever.co/{s}',
           'smartrecruiters': 'https://careers.smartrecruiters.com/{s}', 'ashby': 'https://jobs.ashbyhq.com/{s}', 'recruitee': 'https://{s}.recruitee.com/',
           'workable': 'https://apply.workable.com/{s}/'}

def get(url):
    time.sleep(0.3)
    with urlopen(Request(url, headers={'User-Agent': UA}), timeout=20) as r:
        return r.read(300000).decode('utf-8', 'ignore')

def load(p):
    stem = re.sub(r'[^\w.-]', '_', p['ats'] + '_' + p['slug'])
    path = ff.CACHE / (stem + ('.xml' if p['ats'] == 'personio' else '.json'))
    payload, _, _ = ff.cached(p['endpoint'], path, p['ats'] == 'personio')
    return payload

def clean_title(t, slug):
    t = html.unescape(re.sub(r'\s+', ' ', t)).strip()
    t = re.sub(r'^(?:Jobs|Karriere|Careers|Stellenangebote|Offene Stellen)\s+(?:bei|at|@)\s+', '', t, flags=re.I)
    t = re.split(r'\s+[-–|·]\s+|\s+(?:Jobs|Careers|Karriere|Stellenangebote)\b', t)[0].strip()
    return t if 1 < len(t) < 70 and not re.search(r'personio|ashby|lever|404|not found', t, re.I) else slug.replace('-', ' ').title()

def name_for(p, payload):
    ats, s = p['ats'], p['slug']
    try:
        if ats == 'workable' and payload.get('name'): return payload['name']
        if ats == 'smartrecruiters' and payload.get('content'): return payload['content'][0]['company']['name']
        if ats == 'recruitee' and payload.get('offers') and payload['offers'][0].get('company_name'): return payload['offers'][0]['company_name']
        if ats == 'greenhouse': return json.loads(get(f'https://boards-api.greenhouse.io/v1/boards/{s}')).get('name') or s
        body = get(CAREERS[ats].format(s=s))
        og = re.search(r'property="og:site_name"\s+content="([^"]+)"', body) or re.search(r'property="og:title"\s+content="([^"]+)"', body)
        m = og or re.search(r'<title[^>]*>(.*?)</title>', body, re.S | re.I)
        return clean_title(m.group(1), s) if m else s
    except Exception:
        return s.replace('-', ' ').title()

def evaluate(p):
    try: payload = load(p)
    except Exception: return None
    c = dict(name=p['slug'], ats=p['ats'], slug=p['slug'], endpoint=p['endpoint'], hq_country='')
    rows = [r for r in ff.ADAPTERS[p['ats']](c, payload) if r]
    if not rows: return None
    known = [r for r in rows if r['country'] in ('AT', 'CH') or key(r['city']) in CITY or fill_region(r['city'])]
    if p['ats'] == 'personio' and not known: return None
    countries = Counter(r['country'] for r in rows)
    name = name_for(p, payload)
    total = len(payload.findall('.//position')) if p['ats'] == 'personio' else p.get('sr_total') or (len(payload) if isinstance(payload, list) else len(payload.get('jobs') or payload.get('offers') or payload.get('content') or []))
    global_firm = total > 2 * len(rows) and p['ats'] != 'personio'
    return dict(name=name, ats=p['ats'], slug=p['slug'], endpoint=p['endpoint'], careers_url=CAREERS[p['ats']].format(s=p['slug']),
                hq_country='' if global_firm else countries.most_common(1)[0][0], hq_city='' if global_firm else (Counter(r['city'] for r in known).most_common(1) or [('', 0)])[0][0],
                category='Global (nur DACH-Stellen)' if global_firm else 'DACH-Arbeitgeber', verified=True, identity_ok=True, board_name=name,
                jobs_total=total, jobs_dach=len(rows), source_url=p['endpoint'], verified_at=datetime.now().strftime('%Y-%m-%d %H:%M'),
                discovered_via='Common Crawl URL-Index (öffentliche Board-URL) + Abruf der offiziellen Feed-API')

def main():
    probes = [p for p in json.load(open(ROOT / 'discovery/cc/probe_cc.json')) if p['dach'] > 0]
    print(len(probes), 'Feeds mit DACH-Stellen', flush=True)
    with ThreadPoolExecutor(8) as ex:
        new = [c for c in ex.map(evaluate, probes) if c]
    json.dump(new, open(ROOT / 'discovery/cc/cc_companies.json', 'w'), ensure_ascii=False, indent=1)
    print(len(new), 'neue Firmen', Counter(c['ats'] for c in new), Counter(c['hq_country'] for c in new))

if __name__ == '__main__':
    main()
