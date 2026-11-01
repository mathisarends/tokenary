# Abgleich der Review-Tickets am 01.11.2026

Geprüfter Implementierungsstand: `facde09`, Version 0.2.0, Merge von
[PR #1](https://github.com/mathisarends/tokenary/pull/1).
Der ursprüngliche Reviewstand war älter. Dieser Abgleich ändert ausschließlich
Ticketdokumente, nicht die Runtime oder deren eingecheckte Tests.

## Ergebnis

| Ticket | Ergebnis | Wesentlicher Nachweis / Rest |
| --- | --- | --- |
| 001 | done | Nichtnegative Felder, endliche Mengen, 38 zusätzliche Fehlerfälle |
| 002 | done | `is None`-Fallback, vier zusätzlich geprüfte Ratenszenarien |
| 003 | done | `MissingPriceError`, alle 13 Kategorien mit fehlendem und Nullpreis geprüft |
| 004 | partial | Kontextstaffeln funktionieren; unbekannte Schreibweisen werden noch ignoriert |
| 005 | done | Wheel generiert und importiert Teilmodul ohne Ruff |
| 006 | done | Eigene Kataloge über `PricingCatalog` und `catalog=`, keine globale Enum-Bindung |
| 007 | partial | Atomare Ausgabe vorhanden; implizites Ziel `model_prices.py` bleibt |
| 008 | partial | Modellfilter vorhanden, Providerfilter fehlt |
| 009 | partial | Lazy Preisobjekte vorhanden, gesamte Standard-Rohdaten werden weiterhin gelesen |
| 010 | partial | Wheel-/CI-Grundlage vorhanden, Integration der Restfunktionen fehlt |

## Ausgeführte Prüfungen

Ausführung in einem separaten Worktree des geprüften Stands unter Windows mit
Python 3.14.0. Die vorhandene Entwicklungsumgebung wurde für die Tests verwendet;
der Importpfad wurde auf diesen Worktree geprüft. Im ursprünglichen Checkout
wurde die fremde lokale Änderung an `uv.lock` nicht übernommen oder verändert.

### Bestehende Suite

```powershell
# .pytest_cache muss vorher existieren; einen neuen Basetemp-Pfad wählen.
C:\code\tokenary\.venv\Scripts\python.exe -m pytest --basetemp=.pytest_cache/reconcile-20261101b
```

**Ergebnis: 86 passed in 3.07s.** Ein erster Versuch scheiterte bei 12 Temp-Fixtures
am fehlenden Elternverzeichnis; nach dessen Anlage bestand die vollständige Suite.
Das war ein Setupfehler dieses Abgleichs, kein Runtimefehler.

Besonders relevante eingecheckte Nachweise:

- [Billing-Regressions](../tests/test_billing_regressions.py): Pixelpreise,
  fehlende Preise, Nullpreis, inklusive Tokenzahlen, Kontext- und Cachetarife.
- [Runtime-Katalog](../tests/test_runtime_catalog.py): verzögerte Validierung,
  frische Importprozesse, eigene Modelle, Roundtrips, Prüfsummen, Isolation.
- [Generatorauswahl](../tests/test_generator_selection.py): Modellauswahl,
  Namenskollisionen, Reproduzierbarkeit, Drift und tatsächlich importiertes Teilmodul.

### Zusätzliche, nicht eingecheckte Abgleichproben

- 38 Aufrufe für ungültigen Verbrauch: alle 13 Felder negativ, zusätzlich NaN
  und beide Unendlichkeiten in beiden GB-Tage-Feldern; jeweils Request und Keywords.
  Alle wurden vor dem Defaultkatalogzugriff abgewiesen.
- Vier Reasoning-/Outputpreisvarianten mit inklusiv `output_tokens=40` und
  `reasoning_tokens=40`: `(0, .002) -> 0`, `(.003, .002) -> .12`,
  `(None, .002) -> .08`, `(None, 0) -> 0`.
- Alle 13 Abrechnungskategorien mit Menge 1 und erforderlichen Gesamtmengen:
  ohne Preis jeweils `MissingPriceError`, mit passendem Nullpreis jeweils Kosten 0.
- Zwei eigene Kataloge mit identischer unbekannter Modell-ID und Inputpreis
  `.25` beziehungsweise `.5`: vier Tokens kosten unabhängig 1 beziehungsweise 2;
  Defaultkatalog bleibt ungeladen.
- Synthetische nicht erkannte Staffel `input_cost_per_token_above_200K_tokens=2`
  mit Basispreis 1: `ModelPricing.rate(..., 200001)` liefert 1. Kein Nachweis, dass
  diese Schreibweise in aktuellen Upstream-Daten vorkommt; Restabsicherung in 004.
- CLI `main(['--all'])` mit gemocktem Download, Namenslesen und Schreiben:
  Ziel ist `model_prices.py`; Defaultkatalog wurde zur Namenshistorie geladen.
  Keine echte Ausgabedatei wurde bei dieser Probe geschrieben.
- Danach enthielt der Defaultkatalog 2.973 Rohmodelle und null validierte
  Preisobjekte. Die Trennung von Datenladen und Objektvalidierung ist relevant für 009.

### Isolierte Wheelinstallation

```powershell
uv build --wheel --offline --out-dir dist/review
uv run --isolated --offline --no-project --python 3.14 --with C:/code/tokenary/temp/publish-review-tickets/dist/review/tokenary-0.2.0-py3-none-any.whl python -I C:/code/tokenary/temp/publish-review-tickets/scripts/smoke_installed.py
```

**Beide Prüfungen erfolgreich.** Das Smoke-Skript prüft Import aus `site-packages`
ohne Ruff/OpenAI-/Anthropic-SDK, erzeugt im Temp-Verzeichnis ein Teilmodul, führt
Driftprüfung und eigene Berechnung aus und prüft anschließend die Standardberechnung.
Ausgabe: Runtimequellen **35.614 Bytes**, Einmodell-Artefakt **789 Bytes**.
Der erste isolierte Start scheiterte an Sandboxrechten für den uv-Cache; der
anschließende autorisierte Offline-Aufruf bestand. Keine Runtimeabhängigkeit wurde
in die bestehende Entwicklungsumgebung installiert.

### Aktuelle Performanceprobe

```powershell
uv run --isolated --offline --no-project --python 3.14 --with C:/code/tokenary/temp/publish-review-tickets/dist/review/tokenary-0.2.0-py3-none-any.whl python -I C:/code/tokenary/temp/publish-review-tickets/scripts/benchmark_runtime.py --runs 7
```

Sieben frische Prozesse; pro Prozess 10.000 wiederholte Berechnungen je Aufrufart.
Mediane des vorhandenen Skripts:

| Messgröße | Ergebnis |
| --- | ---: |
| Import | 457,085 ms |
| Erste Berechnung inklusive Total | 34,086 ms |
| Wiederholter Keyword-Aufruf inklusive Total | 11,972 µs |
| Wiederholtes validiertes Requestobjekt inklusive Total | 9,027 µs |

Lokale Beobachtungen, keine CI-Grenzwerte. Es wurde kein zeitgleicher alter
Wheel-Baseline-Lauf durchgeführt und kein neuer Speicherwert erhoben. Daher aus
diesen Zahlen keine prozentuale Beschleunigung gegenüber dem alten Review ableiten.
Das vorhandene Skript gibt Mediane aus, keine Streuung oder Bytecode-Cache-Metrik.

## Grenzen und offene Nachweise

- Python 3.13 und aktuelle GitHub-CI-Ergebnisse wurden hier nicht ausgeführt bzw.
  abgefragt. Die CI-Konfiguration für beide Versionen wurde gelesen.
- Der bestehende Wheel-Smoke testet den Modulaufruf und Pythonexport. Console Script,
  eigene neue Modell-ID und JSON/gzip als kombinierter Wheel-Workflow bleiben in 010.
- Die Semantik externer Providertarife wurde hier nicht erneut online recherchiert;
  spezifische Quellenprüfung bleibt Teil des Restauftrags 004.
- Erledigt bedeutet erfülltes Nutzerziel, nicht wortgleiche Umsetzung früherer
  API-Vorschläge. Vorhandene Namen und Formate sollen erhalten bleiben.
