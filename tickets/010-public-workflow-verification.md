# 010 — Restfunktionen in Doku und Wheel-Test integrieren

- Status: in_review
- Priorität des Rests: P2
- Bereits umgesetzt: [PR #1](https://github.com/mathisarends/tokenary/pull/1), `facde09`
- Offene Abhängigkeiten: 004, 007, 008, 009
- Branch für Rest: `codex/ticket-010-workflow-verification`
- Rest-PR: [#6](https://github.com/mathisarends/tokenary/pull/6)
- Ablauf und Nachweise: [Index](README.md), [Prüfbericht](VERIFICATION.md)

## Bereits erledigt und verifiziert

- [x] README erklärt Standardberechnung, Requests, Modellfilter, eigene Python-/JSON-
  Kataloge, Fehler, Migration zu inklusiven Tokenmengen und Reproduzierbarkeit.
- [x] Wheel-Smoke prüft ohne Ruff/Provider-SDKs tatsächlichen Paketimport, Generierung,
  Driftprüfung, eigene Berechnung und danach den Standardkatalog.
- [x] CI enthält Python 3.13/3.14, Tests, Lint, Driftprüfung, Wheel-Build und Smoke-Test.
- [x] Reproduzierbarer Benchmarkbefehl ist vorhanden und wurde lokal ausgeführt.

## Restbefund

Providerfilter und getrenntes Laden fehlen noch und können noch nicht vollständig
beschrieben/getestet werden. Der vorhandene Wheel-Smoke erzeugt nur Python und
verwendet `gpt-4o`, also eine bereits bekannte Modell-ID. Er ruft nur
`python -m tokenary.generator` auf, nicht das installierte Console Script.
JSON-Roundtrips und eigene IDs sind in Unit-Tests vorhanden, aber noch nicht in
allen entsprechenden Wheel-Integrationspfaden.

## Restauftrag und Akzeptanzkriterien

- [x] README/Beispiele um Provider-only und kombinierte Filter sowie das endgültige
  Ausgabe-/Staffelfehlerverhalten ergänzen. Bestehende öffentliche API erhalten.
- [x] Installiertes Wheel mit eigener, nicht gebündelter Modell-ID durchspielen:
  lokale Quelle, Reduktion, JSON/gzip laden, korrekte Berechnung.
- [x] Nicht ausgewählte Modelle ablehnen; keine gebündelten Preise bei eigener Nutzung laden.
- [x] Installiertes Console Script und Modulaufruf abdecken.
- [x] Ressourcen-Ladegarantien aus 009 im integrierten Workflow absichern.
- [x] Aktualisierte Suite und Wheel-Smoke auf beiden CI-Pythonversionen nachweisen.
- [x] Messbedingungen und Performancegrenzen ehrlich dokumentieren; den jeweiligen
  Code-Stand der gemessenen Wheel-Version angeben.
- [x] Ticketindex mit tatsächlichen Rest-PRs und Merge-Status aktualisieren.

## Verifikation des Rest-PRs

Offline-Fixtures, Wheelinstallation außerhalb des Checkouts und ohne Ruff/SDKs.
Alle geänderten Beispiele ausführen. Gesamtsuite und Wheel-Smoke ausführen;
CI-Links für beide Pythonversionen ergänzen. Beim aktuellen Abgleich wurde lokal
nur Python 3.14 ausgeführt; die CI-Konfiguration ist kein Nachweis eines grünen Laufs.

## Verifikation der Umsetzung

- `scripts/smoke_installed.py` prüft echte Wheelinstallation ohne Ruff und
  Provider-SDKs, außerhalb des Checkouts und mit `python -I`.
- Beide installierten CLI-Einstiege erzeugen aus lokaler Fixture Provider-only,
  Modell-only und kombinierte Auswahlen. Pythonmodule, JSON und gzip werden geladen
  und gegen eine neue, nicht gebündelte Modell-ID berechnet: erwartete Kosten 1,75.
- Nicht ausgewählte IDs scheitern; unbekannte Provider lassen Ziele unverändert;
  `--help`, fehlendes `--output` und `--check` sind abgedeckt.
- Prozessweiter Audit-Hook zählt tatsächliche Ressourcenöffnungen unabhängig vom
  Lese-API. Reiner Import liest nichts, Enum nur Index, eigene Nutzung/Generierung
  keine Providerpreise, Standardlookup genau den benötigten Provider; Cache und
  Providerwechsel werden verifiziert. Da ein Elternprozess keine Kindprozess-I/O
  beobachtet, wird zusätzlich der installierte CLI-Entry unter dem Audit-Hook geprüft.
- Alle vier Beispiele einschließlich `examples/custom_catalog.py` laufen mit
  Python 3.13.8 und 3.14.0 gegen das isoliert installierte Wheel erfolgreich.
- Vollständige Suite: **129 passed** auf beiden lokalen Pythonversionen.
  Python 3.14: `C:/code/tokenary/.venv/Scripts/python.exe -m pytest --basetemp=.pytest_cache/integration-314`.
  Python 3.13: `uv run --isolated --offline --no-project --python 3.13 --with <wheel> --with pytest python -m pytest --basetemp=.pytest_cache/integration-313`.
- Wheel: `uv build --wheel --offline --out-dir dist/final` erfolgreich.
  Smoke von einem Temp-Verzeichnis außerhalb des Repos:
  `uv run --isolated --offline --no-project --python <3.13|3.14> --with <wheel> python -I <repo>/scripts/smoke_installed.py`.
- `ruff check .`, `ruff format --check .`, `git diff --check`, Bundle-Driftprüfung:
  erfolgreich. Neue CLI- und Runtimepfade bleiben offline.
- Messungen aus 009 beziehen sich auf die dort genannten Wheel-Hashes und werden
  nicht als neue Integrationsmessung ausgegeben. Median/Streuung/Cache/RSS und die
  Zunahme der komprimierten Paketdaten sind dort dokumentiert.
- Kein automatischer Merge; die fünf Resttickets bleiben bis zum tatsächlichen
  Merge `in_review`. Bereits erledigte Tickets bleiben PR #1 zugeordnet.

### Bereits bestätigte GitHub-CI-Läufe des Stacks

Jeweils beide Jobs `test (3.13)` und `test (3.14)` vollständig erfolgreich:

| Ticket / PR | Geprüfter Commit | CI |
| --- | --- | --- |
| 008 / #2 | `d835de8` | [Run 41287495737](https://github.com/mathisarends/tokenary/actions/runs/41287495737) |
| 009 / #3 | `fdeef7a` | [Run 41287988834](https://github.com/mathisarends/tokenary/actions/runs/41287988834) |
| 004 / #4 | `7712f7f` | [Run 41288243413](https://github.com/mathisarends/tokenary/actions/runs/41288243413) |
| 007 / #5 | `70c5646` | [Run 41288347352](https://github.com/mathisarends/tokenary/actions/runs/41288347352) |

| 010 / #6 | `1de0b32` | [Run 41288815458](https://github.com/mathisarends/tokenary/actions/runs/41288815458) |

Run 41288815458 ist für beide Pythonversionen vollständig erfolgreich,
inklusive aller Beispiele und des erweiterten installierten Wheel-Workflows.
Die anschließende Änderung ergänzt ausschließlich PR-/CI-Referenzen in Dokumenten.
Alle fünf neuen PRs sind offen und nicht gemergt; die Branchbasen wurden über
GitHub geprüft: `main` → 008 → 009 → 004 → 007 → 010.
