#!/usr/bin/env python3
"""After a fetch: drop boards whose current postings are all outside DACH (non-DACH-only),
and boards whose identity check failed. Empty boards (0 postings) stay (seasonal hiring).
Writes data/companies.json (+ discovery/pruned_round5.json with reasons)."""
import json, re
from pathlib import Path
import xml.etree.ElementTree as ET
ROOT = Path(__file__).resolve().parents[1]
companies = json.load(open(ROOT / 'data/companies.json'))
summary = {(r['ats'], r['slug']): r for r in json.load(open(ROOT / 'data/feeds_summary.json'))['companies']}
CACHE = ROOT / 'data/feeds_cache'

def total(c):
    stem = re.sub(r'[^\w.-]', '_', c['ats'] + '_' + c['slug'])
    try:
        if c['ats'] == 'personio': return len(ET.parse(CACHE / (stem + '.xml')).getroot().findall('position'))
        if c['ats'] == 'successfactors': return None
        d = json.load(open(CACHE / (stem + '.json')))
        if isinstance(d, list): return len(d)
        return d.get('totalFound') if c['ats'] == 'smartrecruiters' else len(d.get('jobs') or d.get('offers') or [])
    except (OSError, ValueError, ET.ParseError): return None

keep, pruned = [], []
for c in companies:
    rec = summary.get((c['ats'], c['slug']), {})
    n = total(c)
    if c.get('identity_ok') is False:
        pruned.append(dict(c, reason='Identität nicht bestätigt'))
    elif rec.get('status') in ('ok', 'stale') and rec.get('count', 0) == 0 and n:
        pruned.append(dict(c, reason=f'nur Nicht-DACH-Stellen ({n})'))
    else:
        keep.append(c)
json.dump(keep, open(ROOT / 'data/companies.json', 'w'), ensure_ascii=False, indent=1)
json.dump(pruned, open(ROOT / 'discovery/pruned_round5.json', 'w'), ensure_ascii=False, indent=1)
print(len(companies), '->', len(keep), 'Feeds;', len(pruned), 'entfernt')
