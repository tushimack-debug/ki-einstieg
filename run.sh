#!/usr/bin/env bash
set -Eeuo pipefail
cd -- "$(dirname -- "$0")"
mkdir -p logs
export TZ=Europe/Berlin
exec > >(tee -a "logs/run-$(date +%F).log") 2>&1
exec 9>/tmp/ki-einstieg.lock
if ! flock -n 9; then
    echo 'Bereits ein Lauf aktiv; übersprungen.'
    exit 0
fi
step='Vorbereitung'
temporary=''
old_moved=0
fail() {
    local code=$?
    trap - ERR
    if [[ "$old_moved" == 1 && ! -e site && -d site.prev ]]; then
        mv -- site.prev site || true
    fi
    if [[ -n "$temporary" && -d "$temporary" ]]; then
        rm -rf -- "$temporary"
    fi
    echo "FEHLER: $step – vorherige Website bleibt online"
    exit "$code"
}
trap fail ERR
find logs -maxdepth 1 -type f -name 'run-*.log' -mtime +29 -delete
export USE_BA=${USE_BA:-0}
if [[ "$USE_BA" == 1 ]]; then
    step='fetch_jobs'
    python3 -u pipeline/fetch_jobs.py
    step='fetch_details'
    python3 -u pipeline/fetch_details.py
    export SOURCE=ba
    export MIN_JOBS=${MIN_JOBS:-50}
else
    step='fetch_feeds'
    python3 -u pipeline/fetch_feeds.py
    export SOURCE=feeds
    export MIN_JOBS=${MIN_JOBS:-20}
fi
step='classify'
python3 -u pipeline/classify.py
step='build'
temporary=$(mktemp -d "$PWD/.site-build.XXXXXX")
python3 build/build_site.py "$temporary"
chmod -R a+rX "$temporary"
step='sanity check'
python3 - "$temporary" <<'PY'
import json
import os
import sys
from pathlib import Path
site = Path(sys.argv[1])
if not (site / 'index.html').is_file():
    raise SystemExit('index.html fehlt')
jobs = json.loads((site / 'data/jobs.json').read_text())
if len(jobs) < int(os.environ.get('MIN_JOBS', '50')):
    raise SystemExit(f'Zu wenige Stellen: {len(jobs)}')
PY
# Prepare the summary before publishing, so data/read failures cannot affect site.
step='Zusammenfassung'
summary=$(python3 - <<'PY'
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
stats = json.loads(Path('data/stats.json').read_text())
feeds = json.loads(Path('data/feeds_summary.json').read_text()) if Path('data/feeds_summary.json').exists() else {}
print(f"OK {datetime.now(ZoneInfo('Europe/Berlin')):%Y-%m-%d %H:%M} | neu heute: {stats['new_today']} | Stellen gesamt: {stats['total_kept']} | Firmen mit Stellen: {stats.get('companies_with_jobs', 0)} | Feeds ok: {stats.get('feeds_ok', 0)}/{feeds.get('total', 0)} | Events: {stats['events_upcoming']}")
PY
)
step='Website austauschen'
if [[ -e site ]]; then
    rm -rf -- site.prev
    mv -- site site.prev
    old_moved=1
fi
mv -- "$temporary" site
temporary=''
old_moved=0
step='Newsletter-Entwurf'
python3 newsletter/make_newsletter.py >/dev/null || echo 'Warnung: Newsletter-Entwurf nicht erzeugt (Website ist trotzdem aktuell).'
printf '%s\n' "$summary"
