#!/usr/bin/env python3
"""Probe public, documented ATS job-board endpoints for candidate companies.
Writes discovery/probe_results.json. Only GET requests to public job-board APIs."""
import json, re, sys, threading, time, unicodedata
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
UA = 'KI-Einstieg-Feedreader/0.1 (privates Projekt; Prototyp)'
ENDPOINTS = {
    'personio': 'https://{s}.jobs.personio.de/xml?language=de',
    'greenhouse': 'https://boards-api.greenhouse.io/v1/boards/{s}/jobs',
    'lever': 'https://api.lever.co/v0/postings/{s}?mode=json&limit=500',
    'lever_eu': 'https://api.eu.lever.co/v0/postings/{s}?mode=json&limit=500',
    'smartrecruiters': 'https://api.smartrecruiters.com/v1/companies/{s}/postings?limit=1',
    'ashby': 'https://api.ashbyhq.com/posting-api/job-board/{s}',
    'recruitee': 'https://{s}.recruitee.com/api/offers/',
    'workable': 'https://apply.workable.com/api/v1/widget/accounts/{s}',
}
HOSTKEY = {k: k.replace('_eu', '') for k in ENDPOINTS}
locks = {k: threading.Semaphore(2) for k in set(HOSTKEY.values())}

def slugify(name):
    n = unicodedata.normalize('NFKD', name.replace('ü','ue').replace('ö','oe').replace('ä','ae').replace('ß','ss')).encode('ascii','ignore').decode().lower()
    return [re.sub(r'[^a-z0-9]', '', n), re.sub(r'[^a-z0-9]+', '-', n).strip('-')]

def count(ats, body):
    if ats == 'personio':
        root = ET.fromstring(body)
        if root.tag != 'workzag-jobs': return None
        return len(root.findall('position'))
    d = json.loads(body)
    if ats == 'greenhouse': return len(d.get('jobs', []))
    if ats.startswith('lever'): return len(d) if isinstance(d, list) else None
    if ats == 'smartrecruiters': return d.get('totalFound', 0) or None
    if ats == 'ashby': return len(d.get('jobs', []))
    if ats == 'recruitee': return len(d.get('offers', []))
    if ats == 'workable': return len(d.get('jobs', []))

def probe(ats, slug):
    url = ENDPOINTS[ats].format(s=slug)
    with locks[HOSTKEY[ats]]:
        time.sleep(0.3)
        try:
            with urlopen(Request(url, headers={'User-Agent': UA, 'Accept': '*/*'}), timeout=20) as r:
                if ats == 'personio' and 'jobs.personio' not in r.geturl(): return None
                n = count(ats, r.read())
        except (HTTPError, URLError, OSError, ValueError, ET.ParseError):
            return None
    if n is None: return None
    return dict(ats=HOSTKEY[ats], slug=slug, endpoint=url.replace('?limit=1', '?limit=100').replace('&limit=500', ''), jobs_total=n)

def main():
    rows = []
    for line in (ROOT / (sys.argv[1] if len(sys.argv) > 1 else 'candidates.txt')).read_text().splitlines():
        if not line.strip() or line.startswith('#'): continue
        name, country, city, cat, slugs = (line.split('|') + [''])[:5]
        sl = [s.strip() for s in slugs.split(',') if s.strip()] or []
        for s in slugify(name):
            if s and s not in sl: sl.append(s)
        rows.append(dict(name=name, hq_country=country, hq_city=city, category=cat, slugs=sl[:4]))
    tasks = [(r, ats, s) for r in rows for s in r['slugs'] for ats in ENDPOINTS]
    print(len(rows), 'companies', len(tasks), 'probes', flush=True)
    with ThreadPoolExecutor(16) as ex:
        results = list(ex.map(lambda t: (t[0], probe(t[1], t[2])), tasks))
    found = {}
    for r, hit in results:
        if hit:
            found.setdefault(r['name'], dict(r, hits=[]))['hits'].append(hit)
    out = ROOT / ('probe_results.json' if len(sys.argv) < 2 else Path(sys.argv[1]).stem + '_results.json')
    out.write_text(json.dumps(list(found.values()), ensure_ascii=False, indent=1))
    print(len(found), 'companies with feeds ->', out)

if __name__ == '__main__':
    main()
