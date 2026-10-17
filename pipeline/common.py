"""Shared atomic JSON storage and detail-cache paths."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def cache_path(refnr):
    return ROOT / 'data/details_cache' / (hashlib.sha1(str(refnr).encode()).hexdigest() + '.json')


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temporary.replace(path)
