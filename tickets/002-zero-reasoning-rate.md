# 002 — Expliziten Reasoningpreis null erhalten

- Status: done
- Umsetzung: [PR #1](https://github.com/mathisarends/tokenary/pull/1), `facde09`
- Verifiziert: 01.11.2026, Python 3.14
- Ablauf und Nachweise: [Index](README.md), [Prüfbericht](VERIFICATION.md)

## Abgleich

`_unit_cost()` in `tokenary/tokenary.py` verwendet ausdrücklich `rate is None`
für den Fallback. Ein expliziter Nullpreis bleibt erhalten. Reasoning ist in der
aktuellen API eine Teilmenge von `output_tokens`; die alte Reproduktion muss deshalb
beide Mengen mit 40 angeben.

## Verifizierte Kriterien

- [x] Reasoningpreis 0 und Outputpreis 0.002 ergeben bei 40 Tokens Kosten 0.
- [x] Reasoningpreis 0.003 hat Vorrang und ergibt 0.12.
- [x] Fehlender Reasoningpreis fällt auf Outputpreis 0.002 zurück: 0.08.
- [x] Fehlender Reasoningpreis und Outputpreis 0 ergeben 0.
- [x] Fehlen beide Preise, greift `MissingPriceError` aus 003.

## Verifikation und Restauftrag

Die vier Preisvarianten wurden zusätzlich zur bestehenden Regression in
`tests/test_billing_regressions.py` ausgeführt. Gesamte Suite: 86 bestanden.
Kein Implementierungs-PR nötig.
