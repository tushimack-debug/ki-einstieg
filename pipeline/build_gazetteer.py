#!/usr/bin/env python3
"""Build data/geo_cities.json: city -> Bundesland for German cities, learned from
(a) SmartRecruiters feed locations (city + region code) and (b) optionally (GAZ_USE_BA=1) the old local BA sample. Default: feeds only.
Only factual city/state pairs are kept; used to fill missing Bundesland for other ATS."""
import glob, json, os, re
from collections import Counter, defaultdict
from common import ROOT, write_json
from geo import key, REGION_CODE

pairs = defaultdict(Counter)
for f in glob.glob(str(ROOT / 'data/feeds_cache/smartrecruiters_*.json')):
    if f.endswith('.meta.json'): continue
    try: d = json.load(open(f))
    except ValueError: continue
    for p in d.get('content', []):
        l = p.get('location') or {}
        if (l.get('country') or '').lower() == 'de' and l.get('city'):
            region = REGION_CODE.get(key(l.get('region') or ''))
            if region: pairs[key(l['city'])][region] += 1
raw = ROOT / 'data/raw_jobs.json'
if raw.exists() and os.environ.get('GAZ_USE_BA') == '1':  # BA-Daten standardmäßig nicht verwenden
    for r in json.load(open(raw)):
        for loc in r.get('stellenlokationen') or []:
            a = loc.get('adresse') or {}
            region = REGION_CODE.get(key(a.get('region') or ''))
            if a.get('ort') and region: pairs[key(a['ort'])][region] += 1
out = {city: c.most_common(1)[0][0] for city, c in pairs.items()}
write_json(ROOT / 'data/geo_cities.json', out)
print(len(out), 'Städte im Gazetteer')
