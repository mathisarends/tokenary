# 003 — Fehlende Preise explizit melden

- Status: done
- Umsetzung: [PR #1](https://github.com/mathisarends/tokenary/pull/1), `facde09`
- Verifiziert: 01.11.2026, Python 3.14
- Ablauf und Nachweise: [Index](README.md), [Prüfbericht](VERIFICATION.md)

## Abgleich

`tokenary/tokenary.py::_unit_cost` liefert bei Menge null unmittelbar null;
bei positiver Menge ohne Preis wirft es den öffentlichen `MissingPriceError`.
`tokenary/errors.py` enthält Modell-ID und Preisfeld in Ausnahme und Meldung.
Der ursprünglich vorgeschlagene Name `UnsupportedPricingError` ist überholt;
die vorhandene öffentliche Ausnahme nicht umbenennen.

## Verifizierte Kriterien

- [x] Fehlende Preise für positive Nutzung werden nicht mehr als kostenlos behandelt.
- [x] Unbenutzte Kategorien brauchen keinen Preis.
- [x] Explizite Nullpreise sind gültig und der Reasoning-Fallback bleibt erhalten.
- [x] Pixelpreis mit `generated_images=1` führt zu `MissingPriceError`.
- [x] README nennt unterstützte Einheiten und Fehlerverhalten.

## Verifikation und Restauftrag

Zusätzlich zur Suite wurden alle 13 aktuellen Abrechnungskategorien mit fehlendem
und mit kostenlosem Preis geprüft, einschließlich Audioausgabe und Cachevarianten.
Die Pixelregression in `tests/test_billing_regressions.py` besteht. Gesamte Suite:
86 bestanden. Kein Implementierungs-PR nötig.
