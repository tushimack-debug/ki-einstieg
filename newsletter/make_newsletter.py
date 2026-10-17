#!/usr/bin/env python3
"""Erzeugt einen Newsletter-Entwurf (Markdown + HTML) aus data/jobs.json und data/events.json.
Nutzung: python3 newsletter/make_newsletter.py [YYYY-Www]   (Standard: aktuelle ISO-Woche)
Es wird nichts versendet."""
import html, json, sys
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
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

def main():
    week = sys.argv[1] if len(sys.argv) > 1 else '%d-W%02d' % date.today().isocalendar()[:2]
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
    today = date.today().isoformat()
    events = [e for e in json.loads((ROOT / 'data/events.json').read_text()) if (e.get('end') or e['start']) >= today]
    events.sort(key=lambda e: e['start'])
    def when(e):
        return de(e['start']) + (f" – {de(e['end'])}" if e.get('end') and e['end'] != e['start'] else '')

    md = [f'<!-- ENTWURF – nicht versendet. Erzeugt {datetime.now():%d.%m.%Y %H:%M} aus echten Daten. -->',
          f'# KI-Einstieg Weekly · KW {int(w)}/{y}', '',
          f'Hi! 👋 Diese Woche ({monday:%d.%m.}–{sunday:%d.%m.%Y}) sind **{len(week_jobs)} neue KI-Einstiegsstellen** '
          f'dazugekommen; insgesamt findest du gerade **{len(jobs)}** auf KI-Einstieg. Hier sind {len(picked)} frische, die uns aufgefallen sind:', '',
          f'## 💼 {len(picked)} frische Stellen', '']
    for j in picked:
        loc = (j['city'] or j.get('region') or 'Remote') + ({'AT': ' (AT)', 'CH': ' (CH)'}.get(j.get('country'), '')) + (' · Remote möglich' if j.get('remote') else '')
        md.append(f"- **{j['title']}**: {j['company']} · {loc} · {j['type']} · seit {de(j['date'])}  \n  [{j.get('source_label') or 'Zur Stelle bei ' + j['company']} ↗]({j['url']})")
    md += ['', '## 🛠️ Hackathons & Events', '']
    for e in events:
        md.append(f"- **[{e['name']}]({e['url']})**: {when(e)}, {e['city']}  \n  {e.get('status','')}")
    md += ['', '## 💡 ' + TIP.split(':')[0], '', TIP.split(': ', 1)[1], '',
           '---', 'Alle Stellen findest du auf KI-Einstieg. Quelle: die öffentlichen Karriere-Seiten bzw. Job-Feeds der Unternehmen; beworben wird immer direkt beim Unternehmen. '
           'Angaben ohne Gewähr; maßgeblich ist die Originalanzeige.  ',
           'Du bekommst diese Mail, weil du dich für den KI-Einstieg-Newsletter angemeldet hast. [Abmelden](#)  ',
           'Impressum: TODO']
    (OUT / f'{week}.md').write_text('\n'.join(md) + '\n', encoding='utf-8')

    h = html.escape
    jobs_html = ''.join(
        f'<tr><td style="padding:10px 0;border-bottom:1px solid #eee"><a href="{h(j["url"])}" style="color:#4338ca;font-weight:600;text-decoration:none">{h(j["title"])}</a><br>'
        f'<span style="color:#555;font-size:14px">{h(j["company"])} · {h(j["city"] or j.get("region") or "Remote")}{ {"AT": " (AT)", "CH": " (CH)"}.get(j.get("country"), "")}{" · Remote möglich" if j.get("remote") else ""} · {h(j["type"])} · seit {de(j["date"])}</span><br>'
        f'<a href="{h(j["url"])}" style="color:#4338ca;font-size:14px">{h(j.get("source_label") or "Zur Stelle bei " + j["company"])} ↗</a></td></tr>'
        for j in picked)
    ev_html = ''.join(
        f'<li style="margin-bottom:8px"><a href="{h(e["url"])}" style="color:#4338ca;font-weight:600">{h(e["name"])}</a><br>'
        f'<span style="color:#555;font-size:14px">{when(e)}, {h(e["city"])}. {h(e.get("status",""))}</span></li>' for e in events)
    doc = f'''<!DOCTYPE html><html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>KI-Einstieg Weekly · KW {int(w)}/{y}</title></head>
<body style="margin:0;background:#f4f4f7;font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif;color:#1f2937">
<!-- ENTWURF – nicht versendet -->
<table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr><td align="center" style="padding:24px 12px">
<table role="presentation" width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;background:#fff;border-radius:12px;padding:28px">
<tr><td>
<p style="margin:0;color:#6366f1;font-weight:700;letter-spacing:.04em;font-size:13px">KI-EINSTIEG WEEKLY · KW {int(w)}/{y}</p>
<h1 style="font-size:24px;margin:8px 0 12px">Neue KI-Einstiegsjobs &amp; Hackathons</h1>
<p style="line-height:1.55">Hi! 👋 Diese Woche ({monday:%d.%m.}–{sunday:%d.%m.%Y}) sind <b>{len(week_jobs)} neue KI-Einstiegsstellen</b> dazugekommen; insgesamt findest du gerade <b>{len(jobs)}</b> auf KI-Einstieg. Hier sind {len(picked)} frische, die uns aufgefallen sind:</p>
<h2 style="font-size:18px;margin:24px 0 4px">💼 {len(picked)} frische Stellen</h2>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0">{jobs_html}</table>
<h2 style="font-size:18px;margin:24px 0 8px">🛠️ Hackathons &amp; Events</h2><ul style="padding-left:18px;margin:0">{ev_html}</ul>
<h2 style="font-size:18px;margin:24px 0 8px">💡 Tipp der Woche</h2>
<p style="line-height:1.55;background:#eef2ff;border-radius:8px;padding:12px 14px;margin:0">{h(TIP.split(": ",1)[1])}</p>
<p style="color:#6b7280;font-size:12px;line-height:1.5;margin-top:28px;border-top:1px solid #eee;padding-top:12px">Quelle: die öffentlichen Karriere-Seiten bzw. Job-Feeds der Unternehmen; beworben wird immer direkt beim Unternehmen. Angaben ohne Gewähr; maßgeblich ist die Originalanzeige.<br>Du bekommst diese Mail, weil du dich für den KI-Einstieg-Newsletter angemeldet hast. <a href="#" style="color:#6b7280">Abmelden</a> · Impressum: TODO</p>
</td></tr></table></td></tr></table></body></html>'''
    (OUT / f'{week}.html').write_text(doc, encoding='utf-8')
    print(f'Newsletter {week}: {len(week_jobs)} neue Stellen in der Woche, {len(picked)} ausgewählt, {len(events)} Events -> {OUT}/{week}.md/.html')

if __name__ == '__main__':
    main()
