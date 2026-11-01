# 009 — Providerdaten und Namenshistorie getrennt laden

- Status: partial
- Priorität des Rests: P1
- Bereits umgesetzt: [PR #1](https://github.com/mathisarends/tokenary/pull/1), `facde09`
- Offene Abhängigkeiten: 008
- Branch für Rest: `codex/ticket-009-lazy-bundled-catalog`
- Rest-PR: noch nicht erstellt
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

- [ ] Modell-ID-/Enum-Historienindex ohne Preise separat bereitstellen.
- [ ] Gebündelte Preise nach Provider in getrennten Ressourcen ablegen; nur benötigte
  Providerdatei lesen, dann wie bisher nur verwendete Preisobjekte validieren/cachen.
- [ ] Reiner Import, eigene Kataloge und Generierung aus lokaler Quelle lesen keine
  gebündelten Preisdateien. Namenshistorie darf separat geladen werden.
- [ ] Explizites `ModelName` benötigt nur Namen, keine Rohpreise.
- [ ] Wiederholte Lookups laden dieselbe Providerdatei nicht erneut; andere Provider
  bleiben ungelesen, bis tatsächlich verwendet.
- [ ] Sichere kollisionsfreie Dateinamen, fehlender Provider, Paketressourcen und
  reproduzierbare Erzeugung aller Artefakte sind berücksichtigt.
- [ ] Öffentliche API, eigene Einzeldatei-Kataloge und Enum-Aliase bleiben kompatibel.

## Verifikation des Rest-PRs

In frischen Prozessen Ressourcenlesen sowie Validierungen zählen: Import,
Standardmodell, Wiederholung, zweites Modell gleichen Providers, anderer Provider,
eigener Katalog, explizites Enum und Generierung. Wheel-Smoke und Driftprüfung
an neue gebündelte Struktur anpassen. Vorher/nachher unter gleichen Bedingungen
messen; keine absoluten Timing-Gates. Aktuelle Messung im Prüfbericht.
Befehle, Ergebnisse und Ressourcenstruktur im PR nachtragen.
