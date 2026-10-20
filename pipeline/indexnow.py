"""IndexNow-Ping: alle URLs aus der Live-Sitemap an api.indexnow.org (Bing, Yandex, …) melden."""
import json, re, sys, urllib.request
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
site = json.loads((ROOT / 'data/brand.json').read_text())['site_url'].rstrip('/')
key = json.loads((ROOT / 'data/indexnow.json').read_text())['key']
UA = {'User-Agent': 'KI-Laufbahn-Bot/1.0 (+mailto:tushimack@gmail.com)'}
xml = urllib.request.urlopen(urllib.request.Request(site + '/sitemap.xml', headers=UA), timeout=30).read().decode()
urls = re.findall(r'<loc>([^<]+)</loc>', xml)
body = json.dumps({'host': site.split('/')[2], 'key': key, 'keyLocation': f'{site}/{key}.txt', 'urlList': urls}).encode()
req = urllib.request.Request('https://api.indexnow.org/indexnow', data=body, method='POST',
                             headers={**UA, 'Content-Type': 'application/json; charset=utf-8'})
import time
for attempt in range(3):  # 403 direkt nach Deploy: Key-Datei noch nicht ausgeliefert -> später erneut
    try:
        with urllib.request.urlopen(req, timeout=30) as r: status = r.status
    except urllib.error.HTTPError as e: status = e.code
    if status != 403: break
    time.sleep(60)
print(f'IndexNow: {len(urls)} URLs -> HTTP {status}')
sys.exit(0 if status in (200, 202) else 1)
