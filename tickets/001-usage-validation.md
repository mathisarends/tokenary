# 001 — Verbrauchswerte validieren

- Status: done
- Umsetzung: [PR #1](https://github.com/mathisarends/tokenary/pull/1), `facde09`
- Verifiziert: 01.11.2026, Python 3.14
- Ablauf und Nachweise: [Index](README.md), [Prüfbericht](VERIFICATION.md)

## Abgleich

Der ursprüngliche Fehler ist behoben. `UsageCostRequest` in
`tokenary/views.py` verwendet für alle Mengen `Field(ge=0)` und global
`allow_inf_nan=False`. Die Validierung erfolgt vor dem Katalogzugriff.
Zusätzlich sind Requests unveränderlich, unbekannte Felder verboten und
Token-Teilmengen gegen die inklusiven Gesamtmengen geprüft.

## Verifizierte Kriterien

- [x] Negative Werte werden für alle 13 Verbrauchsfelder abgewiesen.
- [x] Beide GB-Tage-Felder lehnen NaN und beide Unendlichkeiten ab.
- [x] Requestkonstruktion und Keywordberechnung verhalten sich gleich.
- [x] Ungültige Requests benötigen keinen Defaultkatalog.
- [x] Null und positive gültige Mengen funktionieren in der bestehenden Suite.
- [x] README beschreibt nichtnegative, endliche Mengen und inklusive Tokenzahlen.

## Verifikation und Restauftrag

38 zusätzliche ungültige Request-/Keyword-Fälle wurden ausgeführt; alle wurden
korrekt abgewiesen. Bestehende Verbrauchs- und Teilmengentests sowie die gesamte
Suite bestanden (86 Tests). Kein Implementierungs-PR nötig. Die zusätzlichen
Abgleichproben waren keine neu eingecheckten Tests.
