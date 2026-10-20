"""SEO pages for the static job board: job detail pages with schema.org JobPosting,
landing pages per job type / city / type x city, sitemap.xml, robots.txt, 404.html.

Rules (Google JobPosting guidelines): only current jobs get pages; every build writes a
fresh site directory, so jobs that disappear from the feeds lose their page (404) and
their sitemap entry on the next nightly build. Pages with < MIN_INDEX jobs are noindex
and not in the sitemap; combinations with 0 jobs are not generated at all."""
import hashlib, json, re, unicodedata
from collections import Counter
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo
from html import escape
from pathlib import Path

MIN_INDEX = 2
EXCERPT_CHARS = 700

ML_TERMS = {'machine learning', 'deep learning', 'maschinelles lernen', 'pytorch', 'tensorflow', 'computer vision',
            'reinforcement learning', 'MLOps', 'scikit-learn', 'NLP'}
DS_TERMS = {'data science', 'data scientist'}
ML_TITLE = re.compile(r'(?<![A-Za-z])(?:ML|Machine Learning|Deep Learning|Computer Vision|MLOps)(?![A-Za-z])', re.I)
DS_TITLE = re.compile(r'data\s*scien|data\s*analy|daten', re.I)

# slug, H1/title label, short noun for text, filter
TYPES = [
    ('werkstudent', 'KI Werkstudent Jobs', 'Werkstudentenstellen', lambda j: j['type'] == 'Werkstudent',
     'Als Werkstudent:in arbeitest du neben dem Studium meist 15–20 Stunden pro Woche mit, in den Semesterferien oft mehr. '
     'So sammelst du echte Projekterfahrung mit KI und AI-Tools, bevor du fertig bist.'),
    ('praktikum', 'KI Praktikum', 'Praktika', lambda j: j['type'] == 'Praktikum',
     'Ein Praktikum im KI-Bereich dauert meist drei bis sechs Monate, als Pflicht- oder freiwilliges Praktikum. '
     'Du arbeitest in einem AI-Team mit und lernst, wie Modelle in echten Produkten eingesetzt werden.'),
    ('abschlussarbeit', 'Abschlussarbeit KI', 'Abschlussarbeiten', lambda j: j['type'] == 'Abschlussarbeit',
     'Eine Bachelor- oder Masterarbeit im Unternehmen verbindet Forschung mit Praxis: Du bearbeitest eine konkrete KI-Fragestellung '
     'mit echten Daten und wirst fachlich betreut, oft mit Aussicht auf einen Einstieg danach.'),
    ('duales-studium-ausbildung', 'Duales Studium & Ausbildung KI', 'Ausbildungs- und Dual-Studienplätze',
     lambda j: j['type'] == 'Ausbildung / Duales Studium',
     'Mit einer Ausbildung oder einem dualen Studium startest du direkt nach dem Abi: Theorie an Hochschule oder Berufsschule, '
     'Praxis im Betrieb, Gehalt von Anfang an. Immer mehr Plätze haben einen Schwerpunkt auf KI, Data oder AI.'),
    ('junior', 'Junior KI/ML Jobs', 'Junior- und Trainee-Stellen', lambda j: j['type'] in ('Junior / Berufseinstieg', 'Trainee'),
     'Junior-Stellen und Trainee-Programme richten sich an Absolvent:innen mit wenig Berufserfahrung. '
     'Gefragt sind vor allem Grundlagen in Python, Statistik und Machine Learning, dazu Neugier auf neue AI-Methoden.'),
    ('machine-learning', 'Machine Learning Praktikum & Werkstudent', 'Machine-Learning-Stellen für Studierende',
     lambda j: j['type'] in ('Praktikum', 'Werkstudent') and (bool(ML_TERMS & set(j.get('ai_terms', []))) or bool(ML_TITLE.search(j['title']))),
     'Hier landen Praktika und Werkstudentenjobs, in denen Machine Learning im Mittelpunkt steht: Modelle trainieren, evaluieren '
     'und in Produkte bringen, oft mit PyTorch, TensorFlow oder scikit-learn. Ideal, wenn du KI nicht nur nutzen, sondern bauen willst.'),
    ('data-science-werkstudent', 'Data Science Werkstudent Jobs', 'Data-Science-Werkstudentenstellen',
     lambda j: j['type'] == 'Werkstudent' and (bool(DS_TERMS & set(j.get('ai_terms', []))) or bool(DS_TITLE.search(j['title']))),
     'Data-Science-Werkstudent:innen bereiten Daten auf, bauen Auswertungen und erste Vorhersagemodelle. '
     'Python, SQL und ein Gefühl für Statistik reichen oft für den Einstieg; KI- und AI-Methoden lernst du im Team dazu.'),
]

CITIES = [
    ('muenchen', 'München', {'München', 'Garching', 'Garching bei München', 'Unterföhring', 'Ismaning'},
     'München ist einer der größten KI-Standorte Europas, mit TUM, LMU, vielen Tech-Konzernen und einer lebendigen AI-Startup-Szene.'),
    ('berlin', 'Berlin', {'Berlin'}, 'Berlin ist Deutschlands Startup-Hauptstadt: Viele junge KI-Firmen und AI-Labs suchen hier Studierende und Einsteiger:innen.'),
    ('frankfurt', 'Frankfurt', {'Frankfurt am Main', 'Frankfurt'}, 'In Frankfurt treiben vor allem Banken, Versicherungen und Beratungen KI-Projekte voran, von Risikomodellen bis zu AI-Assistenten.'),
    ('hamburg', 'Hamburg', {'Hamburg'}, 'Hamburg verbindet Logistik, Medien und E-Commerce, Branchen, in denen KI und AI-Automatisierung gerade stark wachsen.'),
    ('stuttgart', 'Stuttgart', {'Stuttgart'}, 'Rund um Stuttgart setzen Autobauer, Zulieferer und Maschinenbauer auf KI, etwa für autonomes Fahren und AI in der Produktion.'),
    ('karlsruhe', 'Karlsruhe', {'Karlsruhe'}, 'Karlsruhe ist mit dem KIT und vielen Software-Firmen ein starker Standort für KI-Forschung und angewandte AI.'),
    ('koeln', 'Köln', {'Köln'}, 'In Köln suchen Versicherer, Medienhäuser und Tech-Firmen Nachwuchs für KI-Projekte und AI-Produkte.'),
    ('nuernberg-erlangen', 'Nürnberg/Erlangen', {'Nürnberg', 'Erlangen', 'Fürth'},
     'Die Region Nürnberg/Erlangen mit FAU, Fraunhofer-Instituten und großen Industrieunternehmen bietet viele Einstiege in KI und AI.'),
    ('wien', 'Wien', {'Wien'}, 'Wien hat eine wachsende KI-Szene mit Forschungseinrichtungen, Startups und internationalen Firmen, die AI-Talente suchen.'),
    ('zuerich', 'Zürich', {'Zürich'}, 'Zürich ist mit ETH und den Forschungszentren großer Tech-Firmen einer der wichtigsten AI-Standorte Europas.'),
    ('remote', 'Remote', None, 'Remote- und Homeoffice-Stellen kannst du unabhängig vom Wohnort machen, ideal neben dem Studium oder vor dem Umzug.'),
]

# Fachgebiete für Filter und Job-Alarm (aus den erkannten KI-Begriffen)
FIELDS = [
    ('Machine Learning', ML_TERMS | {'maschinelles lernen'}, ML_TITLE),
    ('Data Science', DS_TERMS, re.compile(r'data\s*scien', re.I)),
    ('GenAI & LLM', {'LLM', 'generative KI/AI', 'large language model', 'RAG', 'prompt engineering', 'KI-Agent', 'AI agent', 'Sprachmodell', 'KI-Modell'},
     re.compile(r'(?<![A-Za-z])(?:LLM|GenAI|Generative|Agent\w*|Prompt)(?![A-Za-z])', re.I)),
    ('Computer Vision', {'computer vision'}, re.compile(r'computer\s*vision|bildverarbeitung', re.I)),
    ('Robotik', set(), re.compile(r'robot', re.I)),
]


def job_fields(j):
    terms = set(j.get('ai_terms', []))
    out = [name for name, ts, rx in FIELDS if terms & ts or rx.search(j['title'])]
    return out or ['KI allgemein']


EMPLOYMENT = {'Werkstudent': ['PART_TIME'], 'Praktikum': ['INTERN'], 'Abschlussarbeit': ['INTERN'],
              'Ausbildung / Duales Studium': ['FULL_TIME'], 'Trainee': ['FULL_TIME'], 'Junior / Berufseinstieg': ['FULL_TIME']}
COUNTRY_NAME = {'DE': 'Deutschland', 'AT': 'Österreich', 'CH': 'Schweiz'}


def slugify(text, limit=60):
    text = text.replace('ß', 'ss').replace('ä', 'ae').replace('ö', 'oe').replace('ü', 'ue').replace('Ä', 'Ae').replace('Ö', 'Oe').replace('Ü', 'Ue')
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode().lower()
    text = re.sub(r'\(?[mwfd]\s*/\s*[mwfd](?:\s*/\s*[mwfdx*])*\)?', ' ', text)  # (m/w/d)
    text = re.sub(r'\((?:all genders?|gn\*?|alle geschlechter)\)', ' ', text)
    text = re.sub(r'[^a-z0-9]+', '-', text).strip('-')
    return text[:limit].rstrip('-') or 'stelle'


def job_path(j):
    return f"stellen/{slugify(j['title'], 60)}-{slugify(j['company'], 30)}-{hashlib.sha1(j['id'].encode()).hexdigest()[:6]}/"


def in_city(j, city):
    slug, _, names, _ = city
    return bool(j.get('remote')) if slug == 'remote' else j.get('city') in names


def excerpt(text, limit=EXCERPT_CHARS):
    text = re.sub(r'\s+', ' ', text or '').strip()
    if len(text) <= limit:
        return text
    cut = text[:limit]
    end = max(cut.rfind('. '), cut.rfind('! '), cut.rfind('? '))
    return (cut[:end + 1] if end > limit * 0.5 else cut.rsplit(' ', 1)[0]) + ' …'


def load_texts(root, jobs):
    """{job id: excerpt}. From the raw feed dump when the pipeline ran, else from the published copy."""
    raw = root / 'data' / 'raw_feed_jobs.json'
    ids = {j['id'] for j in jobs}
    texts, extra = {}, {}
    if raw.exists():
        for r in json.loads(raw.read_text(encoding='utf-8')):
            if r.get('id') in ids:
                if r.get('description'):
                    texts[r['id']] = excerpt(r['description'])
                extra[r['id']] = {'employment_type': r.get('employment_type') or ''}
    else:
        pub = root / 'data' / 'job_texts.json'
        if pub.exists():
            data = json.loads(pub.read_text(encoding='utf-8'))
            texts = {k: v for k, v in data.get('texts', {}).items() if k in ids}
            extra = {k: v for k, v in data.get('extra', {}).items() if k in ids}
    return texts, extra


def loc_text(j):
    place = j.get('city') or j.get('region') or ''
    if j.get('country') in ('AT', 'CH') and place:
        place += f" ({j['country']})"
    if j.get('remote'):
        place = (place + ' · ' if place else '') + 'Remote möglich'
    return place or 'Ort nicht angegeben'


def de(d):
    try:
        return datetime.strptime(d, '%Y-%m-%d').strftime('%d.%m.%Y')
    except (TypeError, ValueError):
        return d or ''


ATS_LABELS = {'personio': 'Personio', 'greenhouse': 'Greenhouse', 'lever': 'Lever',
              'smartrecruiters': 'SmartRecruiters', 'ashby': 'Ashby', 'recruitee': 'Recruitee',
              'workable': 'Workable', 'successfactors': 'SAP SuccessFactors'}


def retrieved_date(j, fallback=None):
    for value in (j.get('retrieved'), fallback):
        try:
            return date.fromisoformat((value or '')[:10]).isoformat()
        except (ValueError, TypeError):
            pass
    return datetime.now(ZoneInfo('Europe/Berlin')).date().isoformat()


def is_expired(j):
    try:
        return date.fromisoformat(j.get('valid_through') or '') < datetime.now(ZoneInfo('Europe/Berlin')).date()
    except ValueError:
        return False


def source_note(j):
    ats = ATS_LABELS.get(j.get('ats'), j.get('ats') or 'Karriere-Feed')
    return (f'<p class="source-note">Quelle: Karriereseite von {escape(j["company"])} via {escape(ats)}'
            f' · abgerufen am {de(retrieved_date(j))} · Angaben ohne Gewähr</p>')


def ad_label(j):
    return '<span class="ad-label">Anzeige</span>' if j.get('featured') is True else ''


def job_card(j):
    badges = f'<span class="badge">{escape(j["type"])}</span>' + (f'<span class="badge">{j["country"]}</span>' if j.get('country') in ('AT', 'CH') else '') \
        + ('<span class="badge remote">Homeoffice</span>' if j.get('remote') else '')
    data = (f' data-search="{escape(" ".join([j["title"], j["company"], j.get("city") or "", j.get("region") or ""] + j.get("ai_terms", [])).lower())}"'
            f' data-fields="{escape("|".join(j.get("fields", [])))}" data-remote="{1 if j.get("remote") else 0}"')
    return (f'<article class="card{" featured" if j.get("featured") is True else ""}"{data}><div class="badges">{badges}{ad_label(j)}</div><h3><a href="{j["page"]}">{escape(j["title"])}</a></h3>'
            f'<p class="company">{escape(j["company"])}</p><p>{escape(loc_text(j))}</p><time datetime="{escape(j["date"])}">{de(j["date"])}</time>'
            f'{source_note(j)}<a class="button" href="{escape(j["url"])}" target="_blank" rel="noopener noreferrer">Zur Originalanzeige ↗</a></article>')


def filter_bar(items):
    fields = sorted({f for j in items for f in j.get('fields', [])})
    opts = ''.join(f'<option value="{escape(f)}">{escape(f)}</option>' for f in fields)
    remote = '<label class="check"><input id="lf-remote" type="checkbox"> Remote/Homeoffice</label>' if any(j.get('remote') for j in items) else ''
    return ('<form id="landing-filters" class="filters" hidden role="search"><label class="search">Suche in diesen Stellen'
            '<input id="lf-search" type="search" placeholder="z. B. Python, LLM oder Firmenname"></label>'
            f'<label>Fachgebiet<select id="lf-field"><option value="">Alle Fachgebiete</option>{opts}</select></label>{remote}</form>'
            '<p id="lf-count" role="status" aria-live="polite"></p><script src="assets/filter.js" defer></script>')


def employment_types(j, extra):
    et = (extra.get(j['id'], {}).get('employment_type') or '').lower().replace('-', '').replace('_', '')
    base = list(EMPLOYMENT.get(j['type'], ['OTHER']))
    if 'parttime' in et or 'teilzeit' in et or 'workingstudent' in et:
        base = ['PART_TIME'] + ([b for b in base if b == 'INTERN'])
    return base


def job_posting(j, texts, extra, company_urls, site_url, brand):
    country = j.get('country') or 'DE'
    summary = (f"{j['type']} bei {j['company']}" + (f" in {j['city']}" if j.get('city') else '') + '. '
               + (f"Themen: {', '.join(j.get('ai_terms', [])[:6])}. " if j.get('ai_terms') else ''))
    desc = f'<p>{escape(summary)}</p>'
    if texts.get(j['id']):
        desc += f"<p>{escape(texts[j['id']])}</p>"
    desc += f'<p>Vollständige Ausschreibung und Bewerbung beim Unternehmen: {escape(j["url"])}</p>'
    org = {'@type': 'Organization', 'name': j['company']}
    if company_urls.get(j['company']):
        org['sameAs'] = company_urls[j['company']]
    ld = {'@context': 'https://schema.org/', '@type': 'JobPosting', 'title': j['title'], 'description': desc,
          'datePosted': j['date'], 'hiringOrganization': org, 'employmentType': employment_types(j, extra),
          'directApply': False, 'url': f"{site_url}/{j['page']}",
          'identifier': {'@type': 'PropertyValue', 'name': j['company'], 'value': j['id']}}
    ld['validThrough'] = j.get('valid_through') or (date.fromisoformat(retrieved_date(j)) + timedelta(days=30)).isoformat()
    if j.get('city') or not j.get('remote'):
        addr = {'@type': 'PostalAddress', 'addressCountry': country}
        if j.get('city'):
            addr['addressLocality'] = j['city']
        if j.get('region') and j['region'] not in ('Österreich', 'Schweiz'):
            addr['addressRegion'] = j['region']
        if j.get('plz'):
            addr['postalCode'] = j['plz']
        ld['jobLocation'] = {'@type': 'Place', 'address': addr}
    if j.get('remote'):
        ld['jobLocationType'] = 'TELECOMMUTE'
        ld['applicantLocationRequirements'] = {'@type': 'Country', 'name': COUNTRY_NAME.get(country, country)}
    return ld


def generate(site, root, jobs, companies, page, brand, site_url):
    today = datetime.now(ZoneInfo('Europe/Berlin')).date().isoformat()
    jobs[:] = [j for j in jobs if not is_expired(j)]
    stats_path = root / 'data' / 'stats.json'
    stats = json.loads(stats_path.read_text(encoding='utf-8')) if stats_path.exists() else {}
    for j in jobs:
        j['retrieved'] = retrieved_date(j, stats.get('generated_at'))
    texts, extra = load_texts(root, jobs)
    (site / 'data' / 'job_texts.json').write_text(json.dumps({'texts': texts, 'extra': extra}, ensure_ascii=False), encoding='utf-8')
    company_urls = {c['name']: c.get('careers_url') for c in companies if c.get('careers_url')}
    for j in jobs:
        j['page'] = job_path(j)
        j['fields'] = job_fields(j)
    sitemap = [('', today), ('quellen.html', today), ('stelle-veroeffentlichen.html', today), ('entfernen/', today)]
    noindex_pages = []

    # Landing pages
    landing = {}  # (type_slug|None, city_slug|None) -> (path, label, count, indexable)

    def plan(tslug, cslug, items):
        if not items:
            return
        path = (f'{tslug}/' if tslug else 'ki-jobs/') + (f'{cslug}/' if cslug else '')
        landing[(tslug, cslug)] = {'path': path, 'jobs': items, 'index': len(items) >= MIN_INDEX}

    for t in TYPES:
        tj = [j for j in jobs if t[3](j)]
        plan(t[0], None, tj)
        for c in CITIES:
            plan(t[0], c[0], [j for j in tj if in_city(j, c)])
    for c in CITIES:
        plan(None, c[0], [j for j in jobs if in_city(j, c)])
    T = {t[0]: t for t in TYPES}
    C = {c[0]: c for c in CITIES}

    def label(tslug, cslug):
        tl = T[tslug][1] if tslug else 'KI Jobs für Einsteiger'
        if not cslug:
            return tl, f'{tl} – aktuelle Stellen in Deutschland, Österreich & Schweiz'
        cname = C[cslug][1]
        where = 'remote & im Homeoffice' if cslug == 'remote' else f'in {cname}'
        return f'{tl} {where}', f'{tl} {where} – aktuelle Stellen'

    def link_list(keys, heading):
        items = [(k, landing[k]) for k in keys if k in landing and landing[k]['index']]
        if not items:
            return ''
        lis = ''.join(f'<li><a href="{v["path"]}">{escape(label(*k)[0])}</a> ({len(v["jobs"])})</li>' for k, v in items)
        return f'<h2>{escape(heading)}</h2><ul class="link-list">{lis}</ul>'

    for (tslug, cslug), v in landing.items():
        items = sorted(v['jobs'], key=lambda j: (j['date'], j['id']), reverse=True)
        h1, title_core = label(tslug, cslug)
        n = len(items)
        firms = Counter(j['company'] for j in items)
        top_firms = ', '.join(f for f, _ in firms.most_common(3))
        terms = ', '.join(t for t, _ in Counter(t for j in items for t in j.get('ai_terms', [])).most_common(3))
        newest = de(items[0]['date'])
        noun = T[tslug][2] if tslug else 'Einstiegsstellen in KI'
        type_text = T[tslug][4] if tslug else ('Hier findest du alle Einstiegsstellen rund um KI und AI: Werkstudent, Praktikum, Abschlussarbeit, '
                                                'Ausbildung, duales Studium und Junior-Jobs.')
        city_text = C[cslug][3] if cslug else 'Wir sammeln die Stellen täglich direkt aus den Job-Feeds der Unternehmen in Deutschland, Österreich und der Schweiz.'
        count_text = (f'Aktuell {"gibt es" if n != 1 else "gibt es"} {n} {noun if n != 1 else "passende Stelle"}'
                      + (f' {("remote" if cslug == "remote" else "in " + C[cslug][1])}' if cslug else '')
                      + f' (neueste Anzeige vom {newest}). Mit dabei: {top_firms}.' + (f' Häufige Themen: {terms}.' if terms else ''))
        intro = f'<p class="tagline">{escape(city_text)} {escape(type_text)}</p><p>{escape(count_text)}</p>'
        desc = f'{n} aktuelle {h1}: {top_firms}. Einstieg in KI & AI, Bewerbung direkt beim Unternehmen.'
        if len(desc) > 158:
            desc = f'{n} aktuelle {h1}, z. B. bei {firms.most_common(1)[0][0]}. Einstieg in KI & AI, Bewerbung direkt beim Unternehmen.'
        if len(desc) > 158:
            desc = desc[:155].rsplit(' ', 1)[0] + ' …'
        links = ''
        if tslug and cslug:
            links += link_list([(tslug, c[0]) for c in CITIES if c[0] != cslug], f'{T[tslug][1]} in anderen Städten')
            links += link_list([(t[0], cslug) for t in TYPES if t[0] != tslug] + [(None, cslug)], f'Weitere KI-Einstiegsjobs {label(None, cslug)[0].split(" ", 4)[-1]}')
            links += link_list([(tslug, None)], 'Alle Städte')
        elif tslug:
            links += link_list([(tslug, c[0]) for c in CITIES], f'{T[tslug][1]} nach Stadt')
            links += link_list([(t[0], None) for t in TYPES if t[0] != tslug], 'Weitere Einstiegsarten')
        else:
            links += link_list([(t[0], cslug) for t in TYPES], f'Nach Einstiegsart {("remote" if cslug == "remote" else "in " + C[cslug][1])}')
            links += link_list([(None, c[0]) for c in CITIES if c[0] != cslug], 'Andere Städte')
        crumbs = [{'@type': 'ListItem', 'position': 1, 'name': brand, 'item': f'{site_url}/'}]
        if tslug and cslug:
            crumbs.append({'@type': 'ListItem', 'position': 2, 'name': T[tslug][1], 'item': f'{site_url}/{tslug}/'})
        crumbs.append({'@type': 'ListItem', 'position': len(crumbs) + 1, 'name': h1, 'item': f'{site_url}/{v["path"]}'})
        body = (f'<nav class="crumbs" aria-label="Brotkrumen"><a href="./">{escape(brand)}</a>'
                + (f' › <a href="{tslug}/">{escape(T[tslug][1])}</a>' if tslug and cslug else '') + f' › {escape(h1)}</nav>'
                f'<section class="hero landing"><p class="eyebrow">{n} AKTUELLE {"STELLEN" if n != 1 else "STELLE"}</p><h1>{escape(h1)}</h1>{intro}</section>'
                + (filter_bar(items) if n >= 4 else '') +
                f'<section><div class="grid" id="landing-jobs">{"".join(job_card(j) for j in items)}</div></section>'
                f'<section class="links">{links}<p><a href="./#stellen">Alle Stellen mit Filtern durchsuchen →</a></p></section>')
        robots = 'index,follow' if v['index'] else 'noindex,follow'
        out = site / v['path']
        out.mkdir(parents=True, exist_ok=True)
        (out / 'index.html').write_text(page(h1, body, path=v['path'], description=desc, robots=robots, full_title=f'{title_core} | {brand}',
                                             jsonld=[{'@context': 'https://schema.org', '@type': 'BreadcrumbList', 'itemListElement': crumbs}]), encoding='utf-8')
        (sitemap if v['index'] else noindex_pages).append((v['path'], items[0]['date'] if v['index'] else today))

    # Job pages
    for j in jobs:
        ld = job_posting(j, texts, extra, company_urls, site_url, brand)
        related = [k for k in [(t[0], None) for t in TYPES if t[3](j)] + [(t[0], c[0]) for t in TYPES if t[3](j) for c in CITIES if in_city(j, c)]
                   + [(None, c[0]) for c in CITIES if in_city(j, c)] if k in landing and landing[k]['index']]
        rel = ''.join(f'<li><a href="{landing[k]["path"]}">{escape(label(*k)[0])}</a></li>' for k in related[:8])
        terms = ''.join(f'<span class="badge">{escape(t)}</span>' for t in j.get('ai_terms', [])[:8])
        text = texts.get(j['id'])
        body = (f'<nav class="crumbs" aria-label="Brotkrumen"><a href="./">{escape(brand)}</a> › Stelle</nav>'
                f'<article class="job-detail{" featured" if j.get("featured") is True else ""}">{ad_label(j)}<p class="eyebrow">{escape(j["type"].upper())}</p><h1 class="job-title">{escape(j["title"])}</h1>'
                f'<p class="company">{escape(j["company"])} · {escape(loc_text(j))} · seit {de(j["date"])}</p>'
                + (f'<div class="badges">{terms}</div>' if terms else '')
                + (f'<h2>Auszug aus der Anzeige</h2><p>{escape(text)}</p>' if text else '')
                + source_note(j)
                + f'<p><a class="button" href="{escape(j["url"])}" target="_blank" rel="noopener noreferrer">Zur Originalanzeige ↗</a></p>'
                '<p class="note">Bewerbung immer direkt beim Unternehmen. Maßgeblich ist die Originalanzeige; Angaben ohne Gewähr.</p></article>'
                + (f'<section class="links"><h2>Ähnliche Stellen</h2><ul class="link-list">{rel}</ul></section>' if rel else ''))
        desc = f"{j['type']} bei {j['company']}" + (f" in {j['city']}" if j.get('city') else '') + f": {j['title']}. Jetzt direkt beim Unternehmen bewerben."
        if len(desc) > 158:
            desc = desc[:155].rsplit(' ', 1)[0] + ' …'
        out = site / j['page']
        out.mkdir(parents=True, exist_ok=True)
        (out / 'index.html').write_text(page(j['title'], body, path=j['page'], description=desc, jsonld=[ld], og_type='article',
                                             full_title=f"{j['title']} bei {j['company']} | {brand}"), encoding='utf-8')
        sitemap.append((j['page'], j['date']))

    # 404 (GitHub Pages serves it for removed job pages)
    (site / '404.html').write_text(page('Seite nicht gefunden', '<section class="hero"><h1>Diese Seite gibt es nicht (mehr).</h1>'
                                        '<p class="tagline">Vermutlich ist die Stelle inzwischen besetzt oder nicht mehr ausgeschrieben.</p>'
                                        '<p><a href="./#stellen">Zu den aktuellen Stellen →</a></p></section>', path='404.html', robots='noindex,follow'), encoding='utf-8')

    urls = ''.join(f'<url><loc>{escape(site_url)}/{escape(p)}</loc><lastmod>{d}</lastmod></url>' for p, d in sitemap)
    (site / 'sitemap.xml').write_text(f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>\n', encoding='utf-8')
    key_cfg = root / 'data' / 'indexnow.json'
    if key_cfg.exists():
        key = json.loads(key_cfg.read_text(encoding='utf-8'))['key']
        (site / f'{key}.txt').write_text(key, encoding='utf-8')
    (site / 'robots.txt').write_text(f'User-agent: *\nAllow: /\n\nSitemap: {site_url}/sitemap.xml\n', encoding='utf-8')

    index_links = [(k, v) for k, v in landing.items() if v['index']]
    return {'landing': landing, 'label': label, 'sitemap': len(sitemap), 'noindex': len(noindex_pages), 'jobs': len(jobs),
            'index_links': index_links, 'with_text': sum(1 for j in jobs if texts.get(j['id']))}
