# 009 — Providerdaten und Namenshistorie getrennt laden

- Status: in_review
- Priorität des Rests: P1
- Bereits umgesetzt: [PR #1](https://github.com/mathisarends/tokenary/pull/1), `facde09`
- Offene Abhängigkeiten: 008
- Branch für Rest: `codex/ticket-009-lazy-bundled-catalog`
- Rest-PR: [#3](https://github.com/mathisarends/tokenary/pull/3)
- Ablauf und Nachweise: [Index](README.md), [Prüfbericht](VERIFICATION.md)

## Bereits erledigt und verifiziert

- [x] Monolithischer generierter Pythoncode entfällt; Runtimequellen im Wheel: 35.614 Bytes.
- [x] Reiner Import lädt den Defaultkatalog nicht; eigenes Teilmodul benötigt ihn ebenfalls nicht.
- [x] Preisobjekte werden nur für angefragte Modelle validiert und gecacht.
- [x] Die frühere zweite Population aller Pydantic-Preisobjekte ist entfernt.
- [x] Paketressourcen funktionieren im isolierten Wheel; explizites Enum bleibt kompatibel.

## Restbefund

`catalog.get_default_catalog()` liest weiterhin **eine vollständige**
`data/catalog.json.gz`. `_from_bytes` dekomprimiert und parst alle Preise;
`_LazyPricings.__init__` kopiert alle Rohmodelle. Bei der ersten Standardberechnung
sind somit 2.973 Rohmodelle im Speicher, obwohl nur eines validiert wird.
`loaded_model_count == 1` ist kein Nachweis selektiven Datenladens.

Zusätzlich lädt `generator/__main__.py` bei tatsächlicher Generierung den vollständigen
Defaultkatalog, um historische Enum-Namen zu erhalten. Der bloße Generatorimport
ist dagegen bereits leichtgewichtig. Explizites `ModelName` liest ebenfalls den
vollen Rohkatalog, auch ohne Preisobjekte zu validieren.

## Restauftrag und Akzeptanzkriterien

- [x] Modell-ID-/Enum-Historienindex ohne Preise separat bereitstellen.
- [x] Gebündelte Preise nach Provider in getrennten Ressourcen ablegen; nur benötigte
  Providerdatei lesen, dann wie bisher nur verwendete Preisobjekte validieren/cachen.
- [x] Reiner Import, eigene Kataloge und Generierung aus lokaler Quelle lesen keine
  gebündelten Preisdateien. Namenshistorie darf separat geladen werden.
- [x] Explizites `ModelName` benötigt nur Namen, keine Rohpreise.
- [x] Wiederholte Lookups laden dieselbe Providerdatei nicht erneut; andere Provider
  bleiben ungelesen, bis tatsächlich verwendet.
- [x] Sichere kollisionsfreie Dateinamen, fehlender Provider, Paketressourcen und
  reproduzierbare Erzeugung aller Artefakte sind berücksichtigt.
- [x] Öffentliche API, eigene Einzeldatei-Kataloge und Enum-Aliase bleiben kompatibel.

## Verifikation des Rest-PRs

In frischen Prozessen Ressourcenlesen sowie Validierungen zählen: Import,
Standardmodell, Wiederholung, zweites Modell gleichen Providers, anderer Provider,
eigener Katalog, explizites Enum und Generierung. Wheel-Smoke und Driftprüfung
an neue gebündelte Struktur anpassen. Vorher/nachher unter gleichen Bedingungen
messen; keine absoluten Timing-Gates. Aktuelle Messung im Prüfbericht.
Befehle, Ergebnisse und Ressourcenstruktur im PR nachtragen.

## Verifikation der Umsetzung

- Struktur: `tokenary/data/index.json.gz` ohne Preise und 123 Dateien unter
  `tokenary/data/providers/`. Dateinamen sind gekürzter sicherer Providername plus
  voller SHA-256 des Providerwerts; fehlende Metadaten erhalten eine eigene Gruppe.
- Index und Providerkataloge sind geprüft; Validierung/Cache bleiben pro Modell.
  Historische Enum-Aliase, öffentliche Einzeldateiformate und Provenienz bleiben erhalten.
- Frischer Prozess mit gezählten `Path.read_bytes` und `ModelPricing.model_validate`:
  Import 0 Preisdateien/0 Objekte; Enum nur Index/0 Objekte; erstes Modell 1 Datei/1
  Objekt; Wiederholung keine weitere Arbeit; zweites Modell desselben Providers
  keine weitere Datei/1 weiteres Objekt; anderer Provider genau 1 weitere Datei.
- Eigener Katalog und lokale Generierung öffnen keine gebündelten Preisdateien.
  Dieselben Ressourcenprüfungen bestehen auch im isolierten installierten Wheel.
- Der Lade-Regressionstest scheitert am Vorher-Wheel erwartungsgemäß beim Enumzugriff,
  weil dieser dort noch `catalog.json.gz` statt des reinen Namensindex liest.
- `C:/code/tokenary/.venv/Scripts/python.exe -m pytest --basetemp=.pytest_cache/bundle-final`:
  **107 passed** auf Python 3.14.0. `ruff check .`, `ruff format --check .` und
  Bundlegenerierung mit `--check` erfolgreich; Wheel-Build und Offline-Smoke ohne
  Ruff/SDKs erfolgreich (45.290 B Runtimequellen). Python 3.13/CI folgen separat.

### Vergleich unter denselben Bedingungen

Windows 11, Python 3.14.0, Pydantic 2.13.4, isolierte Wheelinstallationen, je sieben
frische Prozesse nach einem ungemessenen Bytecode-Warmup; je 10.000 warme Aufrufe.
Befehl: `uv run --isolated --offline --no-project --python 3.14 --with <wheel> python -I scripts/benchmark_runtime.py --runs 7`.
Rohwerte inklusive Umgebung: [vorher](benchmarks/009-before.json), [nachher](benchmarks/009-after.json).

| Messgröße (Median; Min–Max) | Vorher, `d835de8` | Providerimplementierung dieses PRs |
| --- | --- | --- |
| Import, ms | 687,923; 468,084–1212,962 | 729,102; 505,521–872,494 |
| Erste Berechnung, ms | 50,721; 32,606–64,999 | 35,007; 24,163–83,420 |
| Warme Keywords, µs | 18,973; 14,044–36,193 | 23,845; 17,087–30,205 |
| Warmes Requestobjekt, µs | 14,294; 9,509–31,387 | 16,302; 11,213–17,133 |
| Working-Set-Zuwachs Import, Bytes | 15.503.360; 15.458.304–15.859.712 | 15.667.200; 15.527.936–15.908.864 |
| Working-Set-Zuwachs erste Berechnung, Bytes | 3.158.016; 2.998.272–3.330.048 | 2.105.344; 1.912.832–2.281.472 |

SHA-256 der tatsächlich gemessenen Wheels:
- vorher: `ed2157c2d588deb0e7e73833c73371a258b56332d62bc6c82eb6e66f27f1c035`
- nachher: `13d450836c6cdecc189087779898f99da2f5ad2b41eabafd5ec852f6cfb8595c`

Keine allgemeine Geschwindigkeitszusage: starke Streuung, in diesem Lauf schlechtere
Import-/Warm-Mediane. Die Struktur vermeidet nachweisbar fremde Providerdaten.
Dafür steigt die komprimierte Gesamtdatenmenge von 75.518 auf 190.119 B.
Der Ressourcenvertrag wird ohne absolute Zeitgrenzen getestet. Kein Merge erfolgt.
