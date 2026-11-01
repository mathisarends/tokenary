# 007 — Implizites Ausgabeziel absichern

- Status: done
- Priorität des Rests: P2
- Bereits umgesetzt: [PR #1](https://github.com/mathisarends/tokenary/pull/1), `facde09`
- Offene Abhängigkeiten: keine
- Branch für Rest: `codex/ticket-007-explicit-generator-output`
- Rest-PR: [#5](https://github.com/mathisarends/tokenary/pull/5)
- Ablauf und Nachweise: [Index](README.md), [Prüfbericht](VERIFICATION.md)

## Bereits erledigt und verifiziert

- [x] CLI unterstützt `--output`, lokale Quellen per `--input`, `.py`, `.json`, `.json.gz`.
- [x] Dateiformat wird über die Endung gewählt; ein zusätzliches `--format` ist unnötig.
- [x] Generierung aktualisiert nicht versehentlich `site-packages`; die Doku erklärt
  explizite Katalogübergabe und unveränderten Standardkatalog.
- [x] `_serialization.write_atomic` verwendet eine temporäre Datei im Zielordner
  und `os.replace`, mit Aufräumen im Fehlerfall.
- [x] Ungültige Auswahl lässt bestehende Ausgabe unverändert; `--check` schreibt nie.
- [x] Paketinstallation ohne Ruff und Modulaufruf funktionieren im isolierten Wheel-Test.

## Restbefund

`--output` ist optional und fällt in `generator/__main__.py` auf `model_prices.py`
zurück. Mit gültiger Auswahl, z. B. `--all`, wird deshalb ohne expliziten Zielpfad
in das Arbeitsverzeichnis geschrieben. Das ursprünglich geforderte explizite
Ausgabeziel ist noch nicht erfüllt. Die Prüfung wurde mit gemocktem Schreiben
reproduziert; keine Nutzerdatei wurde dabei überschrieben.

## Restauftrag und Akzeptanzkriterien

- [x] `--output` verpflichtend machen; Migration gegenüber 0.2 dokumentieren.
- [x] Fehlendes Ziel sowie Argumentfehler vor Download, Katalogladen und Schreiben abweisen.
- [x] Bestehende Formate, `--check`, Modellselektion und atomaren Austausch erhalten.
- [x] CLI-Hilfe, README und Hilfsskript konsistent halten.
- [x] Simulierten Austauschfehler testen: vorhandenes Ziel bleibt erhalten,
  temporäre Datei wird entfernt, CLI meldet Fehlercode.

## Verifikation des Rest-PRs

Argumentfehler ohne Seiteneffekte und vorhandenes Ziel bei `os.replace`-Fehler testen.
CLI als Modul und Console Script prüfen. Gesamtsuite ausführen und Ergebnisse
hier nachtragen. Kein Umbau des existierenden Katalogformats.

## Verifikation der Umsetzung

- `--output` ist in beiden Modi Pflicht. Fehlendes Ziel und ungültige Endung
  werden vor Download, Namenshistorie oder Schreiben abgewiesen. Bestehende
  `.py`/`.json`/gzip-Ausgaben, Selektion, Driftprüfung und atomarer Austausch bleiben.
- Gezielte Vorher-Regression: 3 Fehler/3 Erfolge; fehlendes Ziel und ungültige
  Endung gelangten noch bis zum gemockten Download.
- `C:/code/tokenary/.venv/Scripts/python.exe -m pytest --basetemp=.pytest_cache/output-after`:
  **129 passed** auf Python 3.14.0. Enthält seiteneffektfreie Hilfe/Argumentfehler
  und simulierten `os.replace`-Fehler mit Zielerhalt und vollständigem Temp-Cleanup.
- Ruff-Lint/-Format und `git diff --check`: erfolgreich.
- `uv build --wheel --offline --out-dir dist/after-007`: erfolgreich.
- Isolierter Offline-Wheel-Smoke mit Python 3.14 erfolgreich, ohne Ruff/SDKs.
  Console Script und Modulaufruf prüfen `--help` sowie fehlendes `--output`
  außerhalb des Checkouts. Erfolgreiche Generierung, Drift und Laden ebenfalls geprüft.
- README beschreibt die Migration: bisher implizites `model_prices.py` muss nun
  explizit mit `--output model_prices.py` angegeben werden. Das Bundleskript
  verwendet bereits ein explizites `--output-dir`.
- Python 3.13/Remote-CI folgen separat. Kein Merge; Stackbasis Ticket 004 / PR #4.


Nachtrag: [GitHub-CI](https://github.com/mathisarends/tokenary/actions/runs/41288347352)
besteht vollständig auf Python 3.13 und 3.14. Abschließender Stack-/Wheel-Nachweis:
[Ticket 010](010-public-workflow-verification.md).


## Tatsächlicher Mergeabschluss

Am 01.11.2026 nach main gemergt; bestätigter Merge-Commit: `303c376baf9e66e16491d21b8253bf217f3d354d`.
Der zugehörige Remote-Branch ist gelöscht. Gesamtnachweis: [Ticket 010](010-public-workflow-verification.md).
