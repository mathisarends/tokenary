# 006 — Runtime vom globalen Katalog entkoppeln

- Status: done
- Umsetzung: [PR #1](https://github.com/mathisarends/tokenary/pull/1), `facde09`
- Verifiziert: 01.11.2026, Python 3.14 und isoliertes Wheel
- Ablauf und Nachweise: [Index](README.md), [Prüfbericht](VERIFICATION.md)

## Abgleich und verbindliche API

Das Ziel ist durch `PricingCatalog` und `calculate(..., catalog=...)` umgesetzt.
Keine zusätzliche `Catalog`-/`Calculator`-API einführen. `from_file` liest einen
versionierten Katalog mit Prüfsummen; rohe LiteLLM-Mappings werden explizit über
`from_raw_prices` geladen. Diese Formate nicht nachträglich vermischen.

```python
from tokenary import PricingCatalog, calculate
catalog = PricingCatalog.from_file("prices.json")
result = calculate(model="custom-model", input_tokens=4, catalog=catalog)
```

## Verifizierte Kriterien

- [x] String-IDs werden gegen den ausgewählten Katalog geprüft, nicht gegen ein globales Enum.
- [x] Eigene, im Standardkatalog unbekannte Modelle lassen sich berechnen.
- [x] Mehrere Kataloge mit unterschiedlichen Preisen bleiben unabhängig.
- [x] Reiner Import und eigene Berechnung benötigen keinen Defaultkatalog.
- [x] Standardberechnung, Requestobjekte und explizites `ModelName` bleiben nutzbar.
- [x] Preisobjekte werden pro verwendetem Modell validiert und wiederverwendet.
- [x] Version, Struktur, Prüfsummen und Metadaten werden geprüft; fehlerhafte
  einzelne Preise scheitern bei Verwendung (bewusst verzögerte Validierung).
- [x] Regeln für Verbrauch und fehlende Preise gelten auch für eigene Kataloge.

## Verifikation und Restauftrag

`tests/test_runtime_catalog.py`, `tests/test_generator_selection.py`, zusätzliche
Isolation mit zwei eigenen Preisen und Wheel-Smoke bestanden. Gesamtsuite: 86 Tests.
Kein Implementierungs-PR nötig. Vollständiges Einlesen des Standard-Rohkatalogs und
Namenshistorie bei CLI-Generierung sind ausdrücklich Restumfang von 009.
