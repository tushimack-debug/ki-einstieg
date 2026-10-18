"""Shared exclusion list for feed retrieval, classification and site builds."""
import json
from pathlib import Path
from urllib.parse import urlsplit

PATH = Path(__file__).resolve().parents[1] / 'data/optout.json'


def load_optout():
    try:
        return json.loads(PATH.read_text(encoding='utf-8'))
    except FileNotFoundError:
        return {'slugs': [], 'domains': [], 'names': []}


def is_opted_out(item):
    rules = load_optout()
    slug = item.get('company_slug') or item.get('slug') or ''
    # Legacy jobs encode the company slug in their feed identifier.
    if not slug and len(str(item.get('id', '')).split(':')) >= 3:
        slug = item['id'].split(':')[1]
    if slug.casefold() in {s.casefold() for s in rules.get('slugs', [])}:
        return True
    name = item.get('company') or item.get('name') or item.get('firma') or ''
    if name.casefold() in {s.casefold() for s in rules.get('names', [])}:
        return True
    for field in ('endpoint', 'careers_url', 'url'):
        host = (urlsplit(item.get(field) or '').hostname or '').lower().rstrip('.')
        for domain in rules.get('domains', []):
            domain = domain.lower().strip().rstrip('.')
            if domain and (host == domain or host.endswith('.' + domain)):
                return True
    return False
