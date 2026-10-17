import sys, re, time
from urllib.request import Request, urlopen
from concurrent.futures import ThreadPoolExecutor
UA = 'KI-Einstieg-Feedreader/0.1 (privates Projekt; Prototyp)'
def probe(line):
    name, cc, city, host = line.split('|')
    url = f'https://{host}/services/rss/job/?locale=de_DE&keywords=(praktikum%20OR%20werkstudent%20OR%20internship)'
    try:
        with urlopen(Request(url, headers={'User-Agent': UA}), timeout=20) as r:
            body = r.read(300000).decode('utf-8', 'ignore'); final = r.geturl()
        if '<rss' in body[:500] or '<channel' in body[:2000]:
            return f"OK|{line}|{body.count('<item>')}|{re.search(r'<title>(.*?)</title>', body, re.S).group(1)[:60] if '<title>' in body else ''}|{final[:80]}"
        return f"NO|{line}|notrss"
    except Exception as e:
        return f"NO|{line}|{str(e)[:50]}"
lines = [l.strip() for l in open(sys.argv[1]) if l.strip() and not l.startswith('#')]
with ThreadPoolExecutor(8) as ex:
    for r in ex.map(probe, lines): print(r, flush=True)
