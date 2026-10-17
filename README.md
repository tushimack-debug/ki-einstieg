# KI-Einstieg

Statische deutsche Stellenbörse für den Einstieg in KI, mit regelbasierter Auswahl und Veranstaltungen aus einer vom Betreiber gepflegten Datei. Python 3.13, ausschließlich Standardbibliothek; HTML/CSS/JavaScript ohne externe Abhängigkeiten.

## Ausführen

```sh
./run.sh
python3 -m http.server 8000 --directory site
```

Anschließend http://localhost:8000 öffnen. Der Lauf fragt die echte API ab (bis zu 153 Anfragen, 20 Sekunden Timeout, mindestens 0,5 Sekunden Pause), dedupliziert, klassifiziert und baut `site/`. Fehler einzelner Abfragen werden protokolliert; der Lauf kann deshalb unvollständige Ergebnisse liefern. Schlagen alle Abfragen fehl, bricht er ab und erhält vorhandene Rohdaten. Details von Einstiegskandidaten werden mit derselben Pause separat geladen und unter `data/details_cache/` gespeichert. Erfolgreiche Abrufe und 404-Antworten werden wiederverwendet; Fehler werden beim nächsten Lauf erneut versucht. Zum Schluss erscheint eine einzeilige Zusammenfassung mit neuen Stellen, Gesamtzahl, Events und neu geladenen Details.

Einzelschritte: `python3 pipeline/fetch_feeds.py`, `python3 pipeline/classify.py`, `python3 build/build_site.py [Ausgabeordner]` (alternativ `SITE_DIR`). Die Auswahl kombiniert Titel mit starken KI-Begriffen in Beschreibungen und kann relevante Stellen übersehen; `data/dropped_sample.json` enthält bis zu 40 verworfene Treffer mit Gründen. Rohdaten stehen in `data/raw_feed_jobs.json`.

`data/events.json` gehört dem Betreiber und wird niemals vom Programm verändert. Erwartet wird eine Liste von Objekten mit `name`, `start`, `end`, `city`, `audience`, `description`, `url`, `status`. Datumswerte: ISO 8601; URLs: HTTPS/HTTP. Eine leere Liste `[]` ist erlaubt und zeigt einen Leerzustand. Keine Veranstaltungen werden erfunden.

## Unbeaufsichtigte Läufe und Prüfung

`run.sh` verwendet `flock` auf `/tmp/ki-einstieg.lock`, protokolliert nach `logs/run-YYYY-MM-DD.log` und entfernt Logs nach 30 Tagen. Der Build erfolgt in einem temporären Ordner. Erst nach Prüfung von `index.html` und mindestens `MIN_JOBS` Stellen (Standard: 50) wird `site/` ausgetauscht; `site.prev/` enthält die vorherige Version. Fehler vor dem Austausch lassen die aktuelle Website unverändert.

`MAX_DETAILS` begrenzt Detailanfragen pro Lauf (Standard: 2000). Nach 20 aufeinanderfolgenden Fehlern bricht der Detailabruf mit Status 2 ab. `data/seen.json` hält das erste Sichtungsdatum in Europe/Berlin fest; `new_today` zählt alle heute erstmals gesehenen, aktuell behaltenen Stellen auch bei wiederholten Läufen.

`data/classify_report.json` enthält die Entscheidungsgründe, `data/eval_sample.json` eine reproduzierbare Stichprobe mit bis zu 30 behaltenen und 30 verworfenen Einstiegskandidaten. `via_description` markiert Stellen mit unspezifischem Titel; `ai_terms` nennt bis zu fünf gefundene Konzepte. Zwei unterschiedliche starke Begriffe oder drei Vorkommen genügen für eine Beschreibung als KI-Signal. Transformer wird nicht als Signal verwendet.

Optional aktiviert `USE_LLM=1` eine gebündelte Bewertung von Grenzfällen über `/home/box/.local/bin/codex`, falls vorhanden. `LLM_MAX` begrenzt neue Bewertungen (Standard: 40), Beschreibungen werden auf 1200 Zeichen gekürzt. Urteile stehen in `data/llm_cache.json`; bei Ausführungs- oder Parsingfehlern gelten die Regeln. Standardmäßig ist dieser Schritt deaktiviert.

## Datenquelle und Grenzen

Öffentliche Karriere-Feeds der Unternehmen (Personio, Greenhouse, Lever, SmartRecruiters, Ashby, Recruitee, Workable). Bewerbung direkt beim Unternehmen. BA-Pfad deaktiviert, siehe Nutzungsbedingungen.

## Vor Veröffentlichung

- Impressum und Datenschutz mit echten Angaben von Tom ausfüllen (Hosting, Logs, Kontakt, § 5 DDG).
- Preise und Buchungsablauf prüfen; Arbeitgeberseite ist als Entwurf markiert.
- Kontaktadresse ergänzen. Newsletter ist nur ein lokaler Platzhalter: keine Übermittlung, keine Speicherung, kein Versand.
- Veranstaltungen und Stichprobe der Klassifizierung prüfen.

Kein Deployment, keine Kontenerstellung und kein E-Mail-Versand im Skript.

English: Run `./run.sh` to fetch public company career feeds, classify entry-level AI roles and build the static site in `site/`. Operator-owned events are read unchanged. All legal, pricing and newsletter placeholders require review before publication.

## Runde 3 (16.10.2026)
- `./run.sh` ist für einen täglichen Cron-Lauf gedacht, z. B. `15 6 * * * /workspace/ki-einstieg/run.sh`. Der Lauf ist idempotent, über flock gesperrt und schreibt nach `logs/run-YYYY-MM-DD.log`. Bei einem Fehler bleibt die alte Website stehen, und das Skript endet mit Exit-Code ≠ 0. Ein erfolgreicher Lauf endet mit genau einer `OK …`-Zeile.
- Detailtexte werden pro refnr in `data/details_cache/` gecacht, sodass jeder Lauf nur neue Stellen nachlädt.
- Klassifikation: KI im Titel wird nur verworfen, wenn der Titel schwach ist (Marketing/Sales/…) und die Beschreibung keine starken KI-Begriffe enthält. Bei einem Titel ohne KI-Bezug müssen in der Beschreibung mindestens 2 verschiedene und mindestens 4 starke KI-Begriffe vorkommen.
- Optionaler LLM-Schritt: `USE_LLM=1 ./run.sh` prüft Grenzfälle per codex exec. Ohne diese Variable laufen nur die Regeln.
- Newsletter-Entwurf: `python3 newsletter/make_newsletter.py 2026-W42` (wird auch von run.sh erzeugt). Der Entwurf wird nicht versendet.

## Karriere-Feeds

Standard: `./run.sh` mit `data/companies.json`. Fehlt diese Datei, kann die verifizierte Beispieldatei mit `COMPANIES_FILE=data/companies.sample.json ./run.sh` verwendet werden. Unternehmen und Veranstaltungen werden nur gelesen.

`FEED_SLEEP=1` regelt den Mindestabstand zwischen Requests, `FEED_MAX_AGE_H=20` die Cache-Frische. Rohdaten und Metadaten liegen unter `data/feeds_cache/`; SmartRecruiters-Details werden dauerhaft unter `details/` gespeichert. Fehler und Firmenzahlen: `data/feeds_summary.json`. `MIN_JOBS=20` ist die Standard-Untergrenze im Feed-Modus. `SOURCE=feeds` ist der Standard für den Klassifikator. Der optionale BA-Pfad benötigt explizit `USE_BA=1` und einen eigenen `BA_USER_AGENT`; er wird standardmäßig nicht aufgerufen.
