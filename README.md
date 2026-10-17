# KI-Laufbahn (Repo: ki-einstieg)

Statische Stellenbörse für Einstiegsjobs in KI (Werkstudent, Praktikum, Abschlussarbeit, Ausbildung/Duales Studium, Trainee, Junior) in Deutschland, Österreich und der Schweiz.

Live: https://tushimack-debug.github.io/ki-einstieg/

## Datenquellen

Ausschließlich öffentliche, zum Einbinden gedachte Job-Feeds der Unternehmen: Personio (XML), Greenhouse Job Board API, Lever Postings API, SmartRecruiters Posting API, Ashby Job Board API, Recruitee und Workable (öffentliche Widget-APIs) sowie die RSS-Suchfeeds von SAP-SuccessFactors-Karriereseiten. Jede Anzeige verlinkt auf die Originalseite des Arbeitgebers; beworben wird dort. Die Liste der Feeds steht in `data/companies.json`. Unternehmen, die nicht aufgeführt werden möchten, melden sich bitte per E-Mail (siehe Impressum).

## Ausführen

Python 3.12+, nur Standardbibliothek.

```sh
./run.sh                                   # Feeds laden, klassifizieren, site/ bauen, Newsletter-Entwurf erzeugen
python3 -m http.server 8000 --directory site
```

Wichtige Schalter: `MAX_DETAILS` (SmartRecruiters-Detailabrufe pro Lauf), `FEED_MAX_AGE_H` (Cache-Frische, Standard 20 h), `MIN_JOBS` (Mindestzahl Stellen für einen gültigen Build). Der frühere Abruf über die Jobsuche der Bundesagentur für Arbeit ist deaktiviert (`USE_BA=0`).

## Aufbau

- `pipeline/fetch_feeds.py` – höfliches, gecachtes Laden der Feeds (je ATS ein Adapter), Normalisierung, DACH-Filter
- `pipeline/geo.py`, `pipeline/build_gazetteer.py` – Orte, Länder, Bundesländer
- `pipeline/classify.py` – regelbasierte Auswahl von Einstiegsrollen mit KI-Bezug
- `build/build_site.py`, `assets/` – statische Website ohne externe Abhängigkeiten, ohne Cookies und Tracking
- `newsletter/make_newsletter.py` – wöchentlicher Newsletter-Entwurf (wird nicht versendet)
- `discovery/` – Skripte zum Finden und Prüfen öffentlicher Feeds
- `.github/workflows/nightly.yml` – nächtlicher Build und Veröffentlichung über GitHub Pages

## SEO-Seiten
`build/seo.py` erzeugt bei jedem Build: Stellenseiten `/stellen/<slug>/` mit schema.org-JobPosting, Landingpages je Einstiegsart (`/werkstudent/`, `/praktikum/` …), je Stadt (`/ki-jobs/muenchen/`) und Art × Stadt (`/werkstudent/muenchen/`), dazu `sitemap.xml`, `robots.txt` und `404.html`. Seiten mit weniger als 2 Stellen sind `noindex` und fehlen in der Sitemap; Kombinationen ohne Stellen werden nicht erzeugt. Verschwundene Stellen verlieren ihre Seite beim nächsten Build.
Markenname, Slogan und Basis-URL stehen zentral in `data/brand.json`.
