#!/usr/bin/env python3
"""Merge probe results -> data/companies.json. Picks the ATS feed with most jobs per company,
verifies the board belongs to the company (board name / careers page title) and records evidence."""
import json, re, time, unicodedata, html
from datetime import datetime
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
UA = 'KI-Einstieg-Feedreader/0.1 (privates Projekt; Prototyp)'
FEED = {
    'personio': 'https://{s}.jobs.personio.de/xml?language=de',
    'greenhouse': 'https://boards-api.greenhouse.io/v1/boards/{s}/jobs?content=true',
    'lever': 'https://api.lever.co/v0/postings/{s}?mode=json',
    'smartrecruiters': 'https://api.smartrecruiters.com/v1/companies/{s}/postings?limit=100',
    'ashby': 'https://api.ashbyhq.com/posting-api/job-board/{s}?includeCompensation=false',
    'recruitee': 'https://{s}.recruitee.com/api/offers/',
    'workable': 'https://apply.workable.com/api/v1/widget/accounts/{s}?details=true',
}
PAGE = {
    'personio': 'https://{s}.jobs.personio.de/',
    'greenhouse': 'https://boards-api.greenhouse.io/v1/boards/{s}',
    'lever': 'https://jobs.lever.co/{s}',
    'smartrecruiters': 'https://careers.smartrecruiters.com/{s}',
    'ashby': 'https://jobs.ashbyhq.com/{s}',
    'recruitee': 'https://{s}.recruitee.com/',
    'workable': 'https://apply.workable.com/api/v1/widget/accounts/{s}',
}
CAREERS = dict(PAGE, greenhouse='https://job-boards.greenhouse.io/{s}', workable='https://apply.workable.com/{s}/')

def norm(s):
    s = unicodedata.normalize('NFKD', s.lower().replace('ü','ue').replace('ö','oe').replace('ä','ae')).encode('ascii','ignore').decode()
    return re.sub(r'[^a-z0-9]', '', s)

STOP = {'gmbh','ag','se','group','gruppe','the','jobs','bei','at','careers','kgaa','co','kg','ltd','inc'}
def tokens(s):
    return {norm(t) for t in re.split(r'[\s/()&,.:+-]+', s) if len(norm(t)) >= 3 and norm(t) not in STOP}

def board_name(ats, slug):
    url = PAGE[ats].format(s=slug)
    time.sleep(0.4)
    try:
        with urlopen(Request(url, headers={'User-Agent': UA}), timeout=20) as r:
            body = r.read(400000).decode('utf-8', 'ignore')
    except Exception as e:
        return '', url
    if ats in ('greenhouse', 'workable'):
        try: return json.loads(body).get('name', '') or '', url
        except ValueError: return '', url
    m = re.search(r'<title[^>]*>(.*?)</title>', body, re.S | re.I)
    og = re.search(r'property="og:(?:title|site_name)"\s+content="([^"]+)"', body)
    return html.unescape(' '.join(x.group(1) for x in (m, og) if x)).strip()[:200], url

def main():
    rows = []
    import os
    for f in os.environ.get('FILES', 'probe_results.json,candidates2_results.json,candidates3_results.json').split(','):
        p = ROOT / f
        if p.exists(): rows += json.loads(p.read_text())
    out, seen = [], set()
    for r in rows:
        hits = [h for h in r['hits'] if h['jobs_total'] > 0]
        if not hits: continue
        best = max(hits, key=lambda h: h['jobs_total'])
        key = (best['ats'], best['slug'].lower())
        if key in seen: continue
        seen.add(key)
        name_found, page = board_name(best['ats'], best['slug'])
        cand = tokens(r['name'].split('(')[0])
        found = norm(name_found)
        ok = any(t in found for t in cand) or norm(best['slug']) in found or (found and found in norm(r['name']))
        out.append(dict(name=re.sub(r'\s*\((?:Personio|GH|SR|Ashby|Lever)\)$', '', r['name']), ats=best['ats'], slug=best['slug'],
                        endpoint=FEED[best['ats']].format(s=best['slug']), careers_url=CAREERS[best['ats']].format(s=best['slug']),
                        hq_country=r['hq_country'], hq_city=r['hq_city'], category=r['category'], verified=True,
                        identity_ok=bool(ok), board_name=name_found, jobs_total=best['jobs_total'],
                        source_url=page, verified_at=datetime.now().strftime('%Y-%m-%d %H:%M'),
                        other_feeds=[f"{h['ats']}:{h['slug']}" for h in hits if h is not best]))
        print(('OK ' if ok else '?? ') + f"{r['name']} | {best['ats']}:{best['slug']} | {best['jobs_total']} | board='{name_found[:60]}'", flush=True)
    (ROOT / os.environ.get('OUT', 'companies_verified.json')).write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(len(out), 'feeds;', sum(not c['identity_ok'] for c in out), 'need identity review')

if __name__ == '__main__':
    main()
