#!/usr/bin/env python3
"""Probe ATS slugs found in the Common Crawl URL index against the documented public job-board APIs.
Counts DACH postings with the real pipeline adapters (fetch_feeds.py) and caches feed bodies like the pipeline.
Output: discovery/cc/probe_cc.json"""
import json, os, re, sys, threading, time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
os.environ.setdefault('MAX_DETAILS', '0')
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'pipeline'))
import fetch_feeds as ff
from classify import RULES, AI, AI_ACRONYM, TITLE_EXTRA

FEED = {
    'personio': ['https://{s}.jobs.personio.de/xml?language=de'],
    'greenhouse': ['https://boards-api.greenhouse.io/v1/boards/{s}/jobs?content=true'],
    'lever': ['https://api.lever.co/v0/postings/{s}?mode=json', 'https://api.eu.lever.co/v0/postings/{s}?mode=json'],
    'smartrecruiters': ['https://api.smartrecruiters.com/v1/companies/{s}/postings?limit=100'],
    'ashby': ['https://api.ashbyhq.com/posting-api/job-board/{s}?includeCompensation=false'],
    'recruitee': ['https://{s}.recruitee.com/api/offers/'],
    'workable': ['https://apply.workable.com/api/v1/widget/accounts/{s}?details=true'],
}
locks = defaultdict(lambda: threading.Semaphore(3))

def probe(task):
    ats, slug = task
    with locks[ats]:
        for endpoint in FEED[ats]:
            url = endpoint.format(s=slug)
            stem = re.sub(r'[^\w.-]', '_', ats + '_' + slug)
            try:
                payload, stale, new = ff.cached(url, ff.CACHE / (stem + ('.xml' if ats == 'personio' else '.json')), ats == 'personio')
                if new: time.sleep(0.25)
                if ats == 'personio' and payload.tag != 'workzag-jobs': return None
                c = dict(name=slug, ats=ats, slug=slug, endpoint=url, hq_country='')
                rows = [r for r in ff.ADAPTERS[ats](c, payload) if r]
                total = len(payload['content']) if ats == 'smartrecruiters' else None
                titles = [r['title'] for r in rows]
                entry = sum(any(re.search(p, t, re.I) for _, p in RULES) for t in titles)
                ai = sum(bool(AI.search(t) or AI_ACRONYM.search(t) or TITLE_EXTRA.search(t)) for t in titles)
                return dict(ats=ats, slug=slug, endpoint=url, dach=len(rows), entry=entry, ai=ai,
                            countries=sorted({r['country'] for r in rows}), sr_total=payload.get('totalFound') if ats == 'smartrecruiters' else None)
            except Exception:
                continue
    return None

def main():
    slugs = json.load(open(Path(__file__).parent / 'cc/cc_slugs.json'))
    known = {(c['ats'], c['slug'].lower()) for c in json.load(open(Path(__file__).parents[1] / 'data/companies.json'))}
    per = {ats: [(ats, s) for s in lst if (ats, s.lower()) not in known] for ats, lst in slugs.items() if ats in FEED}
    from itertools import zip_longest
    tasks = [t for group in zip_longest(*per.values()) for t in group if t]  # ATS reihum -> parallele Hosts
    print(len(tasks), 'probes', flush=True)
    out = []
    with ThreadPoolExecutor(24) as ex:
        for i, r in enumerate(ex.map(probe, tasks)):
            if r: out.append(r)
            if i % 500 == 0:
                print(i, 'done,', len(out), 'feeds,', sum(x['dach'] > 0 for x in out), 'with DACH', flush=True)
                json.dump(out, open(Path(__file__).parent / 'cc/probe_cc.json', 'w'))
    json.dump(out, open(Path(__file__).parent / 'cc/probe_cc.json', 'w'))
    print('fertig', len(out), 'feeds,', sum(x['dach'] > 0 for x in out), 'with DACH', flush=True)

if __name__ == '__main__':
    main()
