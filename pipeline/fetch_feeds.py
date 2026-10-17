"""Sequential, conditional and cached public career-feed reader (stdlib only)."""
import hashlib
import html
import json
import os
import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit, urlencode, parse_qsl, urlunsplit, quote
from urllib.request import Request, urlopen
from common import ROOT, write_json
from geo import locate, COUNTRY, key, fill_region, REGION_CODE, region_from_plz

UA = 'KI-Einstieg-Feedreader/0.1 (privates Projekt; Prototyp)'
CACHE = ROOT / 'data/feeds_cache'
_last = None
DETAILS = 0
DETAIL_ERRORS = []


class Text(HTMLParser):
    def __init__(self):
        super().__init__(); self.parts = []; self.hidden = 0
    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'): self.hidden += 1
        self.parts.append(' ')
    def handle_endtag(self, tag):
        if tag in ('script', 'style'): self.hidden = max(0, self.hidden - 1)
        self.parts.append(' ')
    def handle_data(self, data):
        if not self.hidden: self.parts.append(data)


def plain(value):
    parser = Text(); parser.feed(html.unescape(str(value or '')))
    return re.sub(r'\s+', ' ', html.unescape(' '.join(parser.parts))).strip()[:20000]


def read_json(path, default):
    try: return json.loads(path.read_text())
    except (OSError, ValueError): return default


def request(url, headers):
    global _last
    for attempt in range(3):
        if _last is not None: time.sleep(max(0, float(os.environ.get('FEED_SLEEP', '1')) - (time.monotonic() - _last)))
        try:
            _last = time.monotonic()
            with urlopen(Request(url, headers={'User-Agent': UA, **headers}), timeout=20) as response:
                return response.read(), response.status, dict(response.headers)
        except HTTPError as exc:
            if exc.code == 304: return None, 304, dict(exc.headers)
            if exc.code != 429 and not 500 <= exc.code < 600: raise
            if attempt == 2: raise
            retry = exc.headers.get('Retry-After', '')
            try: delay = float(retry)
            except ValueError:
                try: delay = max(0, parsedate_to_datetime(retry).timestamp() - time.time())
                except (ValueError, TypeError): delay = 2 ** (attempt + 1)
            time.sleep(max(2 ** attempt, delay))
        except (URLError, OSError, TimeoutError):
            if attempt == 2: raise
            time.sleep(2 ** (attempt + 1))


def cached(url, path, xml=False, permanent=False):
    meta_path = path.with_suffix(path.suffix + '.meta.json')
    meta = read_json(meta_path, {})
    body = path.read_bytes() if path.exists() else None
    def decode(value):
        if not xml: return json.loads(value)
        try: return ET.fromstring(value)
        except ET.ParseError:  # manche RSS-Feeds enthalten unmaskierte '&' (z. B. "SE & Co. KG")
            return ET.fromstring(re.sub(rb'&(?!#?\w+;)', b'&amp;', value))
    if body is not None:
        try:
            value = decode(body)
            if permanent or time.time() - float(meta.get('fetched_at', 0)) < float(os.environ.get('FEED_MAX_AGE_H', '20')) * 3600:
                return value, False, False
        except (ValueError, TypeError, ET.ParseError): body = None
    headers = {}
    if meta.get('etag'): headers['If-None-Match'] = meta['etag']
    if meta.get('last_modified'): headers['If-Modified-Since'] = meta['last_modified']
    try:
        raw, status, response_headers = request(url, headers)
        if status == 304:
            if body is None: raise ValueError('304 ohne Cache')
            raw = body
        value = decode(raw)
        response_headers = {k.lower(): v for k, v in response_headers.items()}
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + '.tmp'); temporary.write_bytes(raw); temporary.replace(path)
        write_json(meta_path, dict(fetched_at=time.time(), status=status, etag=response_headers.get('etag', meta.get('etag')), last_modified=response_headers.get('last-modified', meta.get('last_modified'))))
        return value, False, status != 304
    except (URLError, OSError, ValueError, ET.ParseError) as exc:
        if body is not None: return decode(body), True, False
        raise ValueError(str(exc)) from exc


def date(value):
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value / 1000, timezone.utc).date().isoformat()
    return str(value or '')[:10]


def row(company, identifier, title, locations, country='', remote=False, published='', url='', description='', employment='', seniority='', personio=False, region_hint='', ref='', default=True):
    geo = locate(locations, country, remote, personio, COUNTRY.get(key(company.get('hq_country', ''))) in ('DE', 'AT', 'CH'))
    if not geo: return None
    city, country, region = geo
    if country == 'DE': region = fill_region(city, region_hint if REGION_CODE.get(key(region_hint or '')) else region)
    return dict(id=f"{company['ats']}:{company['slug']}:{identifier}", title=title or '', company=company['name'], company_slug=company['slug'], ats=company['ats'], city=city, country=country, region=region, remote=bool(remote), date=date(published), url=url, description=plain(description), employment_type=str(employment or ''), seniority=str(seniority or ''), ref=str(ref or ''), default_ad=bool(default))


def personio(c, payload):
    host = urlsplit(c['endpoint']).netloc
    for p in payload.findall('.//position'):
        get = lambda name: p.findtext(name) or ''
        locations = [get('office')] + [x.text or '' for x in p.findall('.//additionalOffices/office')]
        yield row(c, get('id'), get('name'), locations, remote=bool(re.search('remote|homeoffice', ' '.join(locations), re.I)), published=get('createdAt'), url=f"https://{host}/job/{get('id')}?language=de", description=' '.join(x.text or '' for x in p.findall('.//jobDescription/value')), employment=get('employmentType'), seniority=get('seniority'), personio=True)


def greenhouse(c, payload):
    for p in payload['jobs']:
        locations = [p.get('location', {}).get('name', '')] + [o.get('name', '') for o in p.get('offices', [])]
        yield row(c, p['id'], p['title'], locations, remote=any('remote' in x.lower() for x in locations), published=p.get('first_published') or p.get('first_published_at') or p.get('updated_at'), url=p['absolute_url'], description=p.get('content'))


def lever(c, payload):
    for p in payload:
        cats = p.get('categories') or {}; locations = cats.get('allLocations') or [cats.get('location', '')]
        yield row(c, p['id'], p['text'], locations, p.get('country', ''), p.get('workplaceType') == 'remote', p.get('createdAt'), p.get('hostedUrl'), ' '.join([p.get('descriptionPlain') or '', *[x.get('content', '') for x in p.get('lists', [])], p.get('additionalPlain') or '']), cats.get('commitment'))


def smartrecruiters(c, payload):
    global DETAILS
    from classify import RULES
    for p in payload['content']:
        exp = (p.get('experienceLevel') or {}).get('id', '')
        employment = (p.get('typeOfEmployment') or {}).get('label', '')
        description = ''
        wants = any(re.search(pattern, p['name'], re.I) for _, pattern in RULES) or re.search('internship|student|trainee|apprentice', exp + ' ' + employment, re.I)
        detail_path = CACHE / 'details' / (hashlib.sha256(f"{c['slug']}:{p['id']}".encode()).hexdigest() + '.json')
        # Cap new detail requests per run (MAX_DETAILS, default 400); the rest follow on later runs.
        if wants and not detail_path.exists() and DETAILS >= int(os.environ.get('MAX_DETAILS', '400')):
            wants = False
        if wants:
            try:
                detail, stale, new = cached(c['endpoint'].split('?')[0].rstrip('/') + '/' + quote(str(p['id']), safe=''), detail_path, permanent=True)
                DETAILS += new
                if stale: raise ValueError('Veralteter Detail-Cache')
                description = ' '.join(x.get('text', '') for x in (detail.get('jobAd', {}).get('sections') or {}).values() if isinstance(x, dict))
            except (ValueError, OSError, KeyError, TypeError) as exc:
                DETAIL_ERRORS.append(str(exc))
        loc = p.get('location') or {}
        yield row(c, p['id'], p['name'], [loc.get('city', '')], loc.get('country', ''), loc.get('remote', False), p.get('releasedDate'), f"https://jobs.smartrecruiters.com/{c['slug']}/{p['id']}", description, employment, exp, region_hint=loc.get('region') or '', ref=p.get('refNumber') or '', default=p.get('defaultJobAd', True) is not False)


def ashby(c, payload):
    for p in payload['jobs']:
        if p.get('isListed') is False: continue
        addr = ((p.get('address') or {}).get('postalAddress') or {})
        locations = [p.get('location', ''), addr.get('addressLocality', '')] + [x.get('location', '') if isinstance(x, dict) else x for x in p.get('secondaryLocations', [])]
        yield row(c, p['id'], p['title'], locations, addr.get('addressCountry', ''), p.get('isRemote', False), p.get('publishedAt'), p.get('jobUrl'), p.get('descriptionPlain'), p.get('employmentType'))


def recruitee(c, payload):
    for p in payload['offers']:
        yield row(c, p['id'], p['title'], [p.get('city', '')], p.get('country_code', ''), p.get('remote', False), p.get('published_at'), p.get('careers_url'), (p.get('description') or '') + ' ' + (p.get('requirements') or ''), p.get('employment_type_code'))


def workable(c, payload):
    for p in payload['jobs']:
        yield row(c, p['shortcode'], p['title'], [p.get('city', '')], p.get('country', ''), p.get('telecommuting', False), p.get('published_on') or p.get('created_at'), p.get('url'), p.get('description'), p.get('employment_type'))


# SAP SuccessFactors Career Site Builder: offizieller RSS-Feed der Jobsuche (/services/rss/job/, max. 20 Treffer je Suche).
# Wir fragen gezielt Einstiegs-/KI-Suchen ab statt die ganze Börse.
SF_QUERIES = ['(KI AND Werkstudent)', '(KI AND Praktikum)', '(KI AND Abschlussarbeit)', '(KI AND Masterarbeit)', '(KI AND Trainee)',
              '(AI AND Intern)', '(AI AND Working Student)', '(AI AND Thesis)', '(Machine AND Learning)', '(Data AND Science)',
              '(Data AND Werkstudent)', '(Data AND Praktikum)', '(künstliche AND Intelligenz)', '(Junior AND KI)', '(Junior AND AI)']


def successfactors(c, payload):
    for item in payload.findall('.//item'):
        raw_title = item.findtext('title') or ''
        m = re.search(r'\s*\(([^()]*),\s*([A-Z]{2})(?:,\s*([^()]*))?\)\s*$', raw_title)
        title = raw_title[:m.start()].strip() if m else raw_title
        city, country = (m.group(1).split(',')[0].strip(), m.group(2)) if m else ('', '')
        try: published = parsedate_to_datetime(item.findtext('pubDate') or '').date().isoformat()
        except (TypeError, ValueError): published = ''
        link = (item.findtext('link') or '').strip().split('?')[0]  # RSS-Tracking-Parameter entfernen
        ident = re.search(r'/(\d+)/?$', link)
        plz_region = region_from_plz(m.group(3)) if m and country == 'DE' else ''
        yield row(c, ident.group(1) if ident else hashlib.sha1(link.encode()).hexdigest()[:12], title, [city], country, False, published, link, item.findtext('description') or '', region_hint=plz_region)


def sf_payload(c, stem):
    """Fetch all SF_QUERIES for one Career Site Builder host; merge items by link."""
    root = ET.Element('rss'); channel = ET.SubElement(root, 'channel'); seen = set(); stale = False
    for i, q in enumerate(SF_QUERIES):
        url = c['endpoint'] + ('&' if '?' in c['endpoint'] else '?') + 'keywords=' + quote(q)
        payload, old, new = cached(url, CACHE / f'{stem}_q{i}.xml', True)
        stale |= old
        if new: time.sleep(0.5)
        for item in payload.findall('.//item'):
            link = item.findtext('link')
            if link not in seen: seen.add(link); channel.append(item)
    return root, stale


ADAPTERS = {f.__name__: f for f in (personio, greenhouse, lever, smartrecruiters, ashby, recruitee, workable, successfactors)}


def main():
    companies = read_json(ROOT / os.environ.get('COMPANIES_FILE', 'data/companies.json'), None)
    if not isinstance(companies, list): raise SystemExit('Unternehmensdatei fehlt oder ist ungültig (COMPANIES_FILE).')
    # Parallel "Spuren": je ATS-Host eine (Personio/Greenhouse mehrere), innerhalb einer Spur sequenziell und höflich.
    # SmartRecruiters bleibt in genau einer Spur (DETAIL_ERRORS/DETAILS sind global).
    lanes = {}
    for i, c in enumerate(companies):
        width = {'personio': 4, 'greenhouse': 2, 'workable': 2, 'ashby': 2, 'lever': 2}.get(c['ats'], 1)
        lanes.setdefault(f"{c['ats']}:{i % width}", []).append((i, c))

    # Checkpoint je Spur: data/feeds_lanes/<spur>.json. Ein Abbruch behält fertige Spuren;
    # beim nächsten Lauf werden Spuren mit gleicher Firmenliste und Alter < FEED_MAX_AGE_H übernommen.
    lane_dir = ROOT / 'data/feeds_lanes'; lane_dir.mkdir(parents=True, exist_ok=True)

    def run_lane(arg):
        name, items = arg
        signature = hashlib.sha256(json.dumps([[c['ats'], c['slug'], c['endpoint']] for _, c in items]).encode()).hexdigest()
        ckpt = lane_dir / (name.replace(':', '_') + '.json')
        saved = read_json(ckpt, {})
        if os.environ.get('RESUME', '1') == '1' and saved.get('signature') == signature and time.time() - saved.get('at', 0) < float(os.environ.get('FEED_MAX_AGE_H', '20')) * 3600:
            print(f'Spur {name}: Checkpoint übernommen ({len(items)} Feeds)', flush=True)
            return [tuple(x) for x in saved['out']]
        out = []
        for i, c in items:
            record = dict(name=c['name'], slug=c['slug'], ats=c['ats'], count=0, errors=[]); selected = []
            detail_start = len(DETAIL_ERRORS) if c['ats'] == 'smartrecruiters' else None
            try:
                stem = re.sub(r'[^\w.-]', '_', c['ats'] + '_' + c['slug'])
                if c['ats'] == 'successfactors': payload, stale = sf_payload(c, stem)
                else: payload, stale, _ = cached(c['endpoint'], CACHE / (stem + ('.xml' if c['ats'] == 'personio' else '.json')), c['ats'] == 'personio')
                postings = list(ADAPTERS[c['ats']](c, payload))
                if c['ats'] == 'smartrecruiters':
                    offset = len(payload['content'])
                    while offset < payload.get('totalFound', offset):
                        parts = urlsplit(c['endpoint']); query = dict(parse_qsl(parts.query)); query.update(limit='100', offset=str(offset))
                        more, old, _ = cached(urlunsplit(parts._replace(query=urlencode(query))), CACHE / f'{stem}_{offset}.json')
                        stale |= old
                        if not more['content']: break  # totalFound zählt teils nicht-öffentliche Stellen
                        postings.extend(ADAPTERS[c['ats']](c, more)); offset += len(more['content'])
                selected = [p for p in postings if p]
                # SmartRecruiters: DE/EN-Sprachvarianten teilen die refNumber – nur die Standardanzeige behalten
                by_ref = {}
                for p in sorted(selected, key=lambda r: not r.get('default_ad', True)):
                    by_ref.setdefault(p.get('ref') or p['id'], p)
                selected = list(by_ref.values())
                record['count'] = len(selected)
                if detail_start is not None: record['errors'].extend(DETAIL_ERRORS[detail_start:])
                stale |= bool(record['errors'])
                record['status'] = 'stale' if stale else 'ok'
                if stale: record['errors'].append('Abruf fehlgeschlagen; Cache verwendet')
            except (ValueError, KeyError, TypeError, AttributeError, OSError, ET.ParseError) as exc:
                record.update(status='error'); record['errors'].append(str(exc))
            out.append((i, record, selected))
        write_json(ckpt, dict(signature=signature, at=time.time(), out=out))
        print(f'Spur {name}: fertig ({len(items)} Feeds, {sum(len(x[2]) for x in out)} DACH-Stellen)', flush=True)
        return out

    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max(1, len(lanes))) as ex:
        done = [x for lane in ex.map(run_lane, lanes.items()) for x in lane]
    done.sort(key=lambda x: x[0])
    rows = [r for _, _, sel in done for r in sel]; results = [rec for _, rec, _ in done]
    ok = sum(r['status'] == 'ok' for r in results); stale_count = sum(r['status'] == 'stale' for r in results)
    failed = sum(r['status'] == 'error' for r in results); errors = stale_count + failed
    rows = list({r['id']: r for r in rows}.values())
    write_json(ROOT / 'data/feeds_summary.json', dict(ok=ok, stale=stale_count, error=errors, failed_without_cache=failed, total=len(companies), rows=len(rows), details_new=DETAILS, companies=results))
    print(f'Feeds: ok={ok} stale={stale_count} error={errors} | Stellen DACH: {len(rows)} | Details neu: {DETAILS}', flush=True)
    if not rows or failed > len(companies) / 2: return 2
    write_json(ROOT / 'data/raw_feed_jobs.json', rows)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
