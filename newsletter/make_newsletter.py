#!/usr/bin/env python3
"""Erzeugt einen Newsletter-Entwurf (Markdown + HTML) aus data/jobs.json und data/events.json.
Nutzung: python3 newsletter/make_newsletter.py [YYYY-Www] [TYP|STADT]   (Standard: aktuelle ISO-Woche, ohne Job-Alarm)
TYP/STADT = Slugs aus build/seo.py (z. B. werkstudent|muenchen, alle|remote); erzeugt <Woche>.<typ>-<stadt>.html mit Job-Alarm-Block.
Es wird nichts versendet. Zusätzlich: newsletter/<Woche>.meta.json (Anzahl neuer Stellen, Betreff) für send_campaign.py.
Abmeldelink: Brevo-Platzhalter {{ unsubscribe }} (wird von Brevo pro Empfänger ersetzt)."""
import html, json, sys
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'build'))
import seo  # noqa: E402  (Typ-/Stadt-Definitionen, identisch mit den Landingpages)
BRAND_CFG = json.loads((ROOT / 'data/brand.json').read_text(encoding='utf-8'))
BRAND = BRAND_CFG['name']
SITE_URL = BRAND_CFG['site_url'].rstrip('/')
OUT = ROOT / 'newsletter'
TYPE_ORDER = ['Werkstudent', 'Praktikum', 'Abschlussarbeit', 'Junior', 'Trainee', 'Ausbildung']
MAX_PER_TYPE = {'Ausbildung / Duales Studium': 2}
TIP = ("Tipp der Woche: Ein kleines eigenes Projekt schlägt jede Kursliste. "
       "Bau in einem Wochenende etwas Konkretes, z. B. einen Chatbot für die FAQ deines Sportvereins "
       "oder eine Auswertung offener Daten deiner Stadt. Stell es mit einer kurzen README auf GitHub "
       "und verlinke es ganz oben in deiner Bewerbung. Bei Werkstudenten- und Praktikumsstellen ist das "
       "oft das, worüber im Gespräch zuerst geredet wird.")

def de(d):
    return datetime.strptime(d, '%Y-%m-%d').strftime('%d.%m.%Y')

TYPES = {t[0]: t for t in seo.TYPES}
CITIES = {c[0]: c for c in seo.CITIES}


def segment_label(typ, stadt):
    t = TYPES[typ][1] if typ in TYPES else 'KI-Einstiegsjobs'
    if stadt == 'remote':
        return f'{t} remote'
    return f'{t} in {CITIES[stadt][1]}' if stadt in CITIES else t


def segment_path(typ, stadt, jobs):
    if typ not in TYPES and stadt not in CITIES:
        return ''
    match = [j for j in jobs if (typ not in TYPES or TYPES[typ][3](j)) and (stadt not in CITIES or seo.in_city(j, CITIES[stadt]))]
    if not match:
        return ''
    return (f'{typ}/' if typ in TYPES else 'ki-jobs/') + (f'{stadt}/' if stadt in CITIES else '')


def main():
    week = sys.argv[1] if len(sys.argv) > 1 else '%d-W%02d' % date.today().isocalendar()[:2]
    segment = sys.argv[2] if len(sys.argv) > 2 else ''
    typ, _, stadt = segment.partition('|')
    typ = typ if typ in TYPES else 'alle'
    stadt = stadt if stadt in CITIES else 'alle'
    personal = typ != 'alle' or stadt != 'alle'
    suffix = f'.{typ}-{stadt}' if personal else ''
    y, w = week.split('-W')
    monday = date.fromisocalendar(int(y), int(w), 1)
    sunday = monday + timedelta(days=6)
    jobs = json.loads((ROOT / 'data/jobs.json').read_text())
    def first(j):
        return j.get('date') or ''  # Veröffentlichungsdatum laut BA
    week_jobs = [j for j in jobs if monday.isoformat() <= first(j) <= sunday.isoformat()]
    week_jobs.sort(key=lambda j: (first(j), j['id']), reverse=True)
    # Zu wenige neue Stellen in dieser Woche? Mit den frischesten der Vorwoche auffüllen.
    pool = week_jobs + sorted([j for j in jobs if j not in week_jobs and first(j) >= (monday - timedelta(days=7)).isoformat()], key=lambda j: (first(j), j['id']), reverse=True)
    picked, per_type, companies = [], Counter(), set()
    for rnd in range(2):  # Runde 1: max. 3 pro Typ, Runde 2: auffüllen
        for j in pool:
            if len(picked) == 10: break
            if j in picked or (rnd == 0 and j['company'] in companies) or sum(p['company'] == j['company'] for p in picked) >= 2: continue
            cap = MAX_PER_TYPE.get(j['type'], 3 if rnd == 0 else 10)
            if per_type[j['type']] >= cap: continue
            picked.append(j); per_type[j['type']] += 1; companies.add(j['company'])
    picked.sort(key=lambda j: (TYPE_ORDER.index(j['type']) if j['type'] in TYPE_ORDER else 99, j['title']))
    alarm, alarm_new = [], 0
    if personal:
        match = [j for j in jobs if (typ == 'alle' or TYPES[typ][3](j)) and (stadt == 'alle' or seo.in_city(j, CITIES[stadt]))]
        new = sorted([j for j in match if j in week_jobs], key=lambda j: (first(j), j['id']), reverse=True)
        alarm_new = len(new)
        alarm = (new or sorted(match, key=lambda j: (first(j), j['id']), reverse=True))[:10]
        picked = [j for j in picked if j not in alarm][:6]
    seg_name = segment_label(typ, stadt)
    seg_url = f"{SITE_URL}/{segment_path(typ, stadt, jobs)}"
    today = date.today().isoformat()
    events = [e for e in json.loads((ROOT / 'data/events.json').read_text()) if (e.get('end') or e['start']) >= today]
    events.sort(key=lambda e: e['start'])
    def when(e):
        return de(e['start']) + (f" – {de(e['end'])}" if e.get('end') and e['end'] != e['start'] else '')

    md = [f'<!-- ENTWURF – nicht versendet. Erzeugt {datetime.now():%d.%m.%Y %H:%M} aus echten Daten. -->',
          f'# {BRAND} Weekly · KW {int(w)}/{y}', '',
          f'Hi! 👋 Diese Woche ({monday:%d.%m.}–{sunday:%d.%m.%Y}) sind **{len(week_jobs)} neue KI-Einstiegsstellen** '
          f'dazugekommen; insgesamt findest du gerade **{len(jobs)}** auf {BRAND}. Hier sind {len(picked)} frische, die uns aufgefallen sind:', '',
          f'## 💼 {len(picked)} frische Stellen', '']
    for j in picked:
        loc = (j['city'] or j.get('region') or 'Remote') + ({'AT': ' (AT)', 'CH': ' (CH)'}.get(j.get('country'), '')) + (' · Remote möglich' if j.get('remote') else '')
        md.append(f"- **{j['title']}**: {j['company']} · {loc} · {j['type']} · seit {de(j['date'])}  \n  [{j.get('source_label') or 'Zur Stelle bei ' + j['company']} ↗]({j['url']})")
    md += ['', '## 🛠️ Hackathons & Events', '']
    for e in events:
        md.append(f"- **[{e['name']}]({e['url']})**: {when(e)}, {e['city']}  \n  {e.get('status','')}")
    md += ['', '## 💡 ' + TIP.split(':')[0], '', TIP.split(': ', 1)[1], '',
           '---', f'Alle Stellen findest du auf {BRAND}.'
           ' Quelle: die öffentlichen Karriere-Seiten bzw. Job-Feeds der Unternehmen; beworben wird immer direkt beim Unternehmen. '
           'Angaben ohne Gewähr; maßgeblich ist die Originalanzeige.  ',
           f'Du bekommst diese Mail, weil du dich für den {BRAND}-Newsletter angemeldet hast. [Abmelden]({{{{ unsubscribe }}}})  ',
           f'{BRAND} · Tom Mack · Pfälzer Straße 20b · 91052 Erlangen · Deutschland · tushimack@gmail.com  ',
           f'Impressum: {SITE_URL}/impressum.html']
    if not personal:
        (OUT / f'{week}.md').write_text('\n'.join(md) + '\n', encoding='utf-8')

    h = html.escape
    jobs_html = ''.join(
        f'<tr><td style="padding:10px 0;border-bottom:1px solid #eee"><a href="{h(j["url"])}" style="color:#4338ca;font-weight:600;text-decoration:none">{h(j["title"])}</a><br>'
        f'<span style="color:#555;font-size:14px">{h(j["company"])} · {h(j["city"] or j.get("region") or "Remote")}{ {"AT": " (AT)", "CH": " (CH)"}.get(j.get("country"), "")}{" · Remote möglich" if j.get("remote") else ""} · {h(j["type"])} · seit {de(j["date"])}</span><br>'
        f'<a href="{h(j["url"])}" style="color:#4338ca;font-size:14px">{h(j.get("source_label") or "Zur Stelle bei " + j["company"])} ↗</a></td></tr>'
        for j in picked)
    def rows(items):
        return ''.join(
            f'<tr><td style="padding:10px 0;border-bottom:1px solid #eee"><a href="{h(j["url"])}" style="color:#4338ca;font-weight:600;text-decoration:none">{h(j["title"])}</a><br>'
            f'<span style="color:#555;font-size:14px">{h(j["company"])} · {h(j["city"] or j.get("region") or "Remote")}{" · Remote möglich" if j.get("remote") else ""} · {h(j["type"])} · seit {de(j["date"])}</span></td></tr>'
            for j in items)
    alarm_html = ''
    if personal:
        head = (f'{alarm_new} neue Stellen diese Woche' if alarm_new else 'Diese Woche keine neuen Stellen, hier die aktuellsten passenden') if alarm else 'Gerade keine passenden Stellen'
        alarm_html = (f'<div style="background:#ecfdf5;border-radius:10px;padding:14px 16px;margin:20px 0"><p style="margin:0;color:#065f46;font-weight:700;font-size:13px;letter-spacing:.04em">🔔 DEIN JOB-ALARM: {h(seg_name.upper())}</p>'
                      f'<p style="margin:6px 0 0;color:#065f46">{h(head)}.</p>'
                      + (f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0">{rows(alarm)}</table>' if alarm else '')
                      + f'<p style="margin:10px 0 0;font-size:13px"><a href="{h(seg_url)}" style="color:#065f46">Alle {h(seg_name)} ansehen ↗</a> · Alarm ändern: einfach mit neuer Auswahl erneut anmelden.</p></div>')
    ev_html = ''.join(
        f'<li style="margin-bottom:8px"><a href="{h(e["url"])}" style="color:#4338ca;font-weight:600">{h(e["name"])}</a><br>'
        f'<span style="color:#555;font-size:14px">{when(e)}, {h(e["city"])}. {h(e.get("status",""))}</span></li>' for e in events)
    doc = f'''<!DOCTYPE html><html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>{h(BRAND)} Weekly · KW {int(w)}/{y}</title></head>
<body style="margin:0;background:#f4f4f7;font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif;color:#1f2937">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr><td align="center" style="padding:24px 12px">
<table role="presentation" width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;background:#fff;border-radius:12px;padding:28px">
<tr><td>
<p style="margin:0;color:#6366f1;font-weight:700;letter-spacing:.04em;font-size:13px">{h(BRAND.upper())} WEEKLY · KW {int(w)}/{y}</p>
<h1 style="font-size:24px;margin:8px 0 12px">Neue KI-Einstiegsjobs &amp; Hackathons</h1>
<p style="line-height:1.55">Hi! 👋 Diese Woche ({monday:%d.%m.}–{sunday:%d.%m.%Y}) sind <b>{len(week_jobs)} neue KI-Einstiegsstellen</b> dazugekommen; insgesamt findest du gerade <b>{len(jobs)}</b> auf {BRAND}. Hier sind {len(picked)} frische, die uns aufgefallen sind:</p>
{alarm_html}
<h2 style="font-size:18px;margin:24px 0 4px">💼 {len(picked)} {"weitere " if personal else ""}frische Stellen</h2>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0">{jobs_html}</table>
<h2 style="font-size:18px;margin:24px 0 8px">🛠️ Hackathons &amp; Events</h2><ul style="padding-left:18px;margin:0">{ev_html}</ul>
<h2 style="font-size:18px;margin:24px 0 8px">💡 Tipp der Woche</h2>
<p style="line-height:1.55;background:#eef2ff;border-radius:8px;padding:12px 14px;margin:0">{h(TIP.split(": ",1)[1])}</p>
<p style="color:#6b7280;font-size:12px;line-height:1.5;margin-top:28px;border-top:1px solid #eee;padding-top:12px">Quelle: die öffentlichen Karriere-Seiten bzw. Job-Feeds der Unternehmen; beworben wird immer direkt beim Unternehmen. Angaben ohne Gewähr; maßgeblich ist die Originalanzeige.<br>Du bekommst diese Mail, weil du dich für den {h(BRAND)}-Newsletter angemeldet hast. <a href="{{{{ unsubscribe }}}}" style="color:#6b7280">Abmelden</a> · <a href="{SITE_URL}/impressum.html" style="color:#6b7280">Impressum</a> · <a href="{SITE_URL}/datenschutz.html" style="color:#6b7280">Datenschutz</a><br>{h(BRAND)} · Tom Mack · Pfälzer Straße 20b · 91052 Erlangen · Deutschland · tushimack@gmail.com</p>
</td></tr></table></td></tr></table></body></html>'''
    subject = (f'{BRAND} Weekly KW {int(w)}: {alarm_new} neue {seg_name}' if personal and alarm_new else
               f'{BRAND} Weekly KW {int(w)}: {len(week_jobs)} neue KI-Einstiegsstellen')
    (OUT / f'{week}{suffix}.html').write_text(doc, encoding='utf-8')
    (OUT / f'{week}{suffix}.meta.json').write_text(json.dumps({'week': week, 'segment': f'{typ}|{stadt}', 'new_jobs': len(week_jobs), 'alarm_jobs': len(alarm),
        'alarm_new': alarm_new, 'picked': len(picked), 'events': len(events), 'subject': subject}, ensure_ascii=False), encoding='utf-8')
    if personal:
        print(f'Newsletter {week} [{typ}|{stadt}]: {alarm_new} neue / {len(alarm)} im Alarm-Block, {len(picked)} weitere -> {OUT}/{week}{suffix}.html')
        return
    print(f'Newsletter {week}: {len(week_jobs)} neue Stellen in der Woche, {len(picked)} ausgewählt, {len(events)} Events -> {OUT}/{week}.md/.html')

if __name__ == '__main__':
    main()
