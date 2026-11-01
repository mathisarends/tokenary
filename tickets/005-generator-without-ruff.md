# 005 — Generator ohne Ruff ausführen

- Status: done
- Umsetzung: [PR #1](https://github.com/mathisarends/tokenary/pull/1), `facde09`
- Verifiziert: 01.11.2026, isoliertes Wheel mit Python 3.14
- Ablauf und Nachweise: [Index](README.md), [Prüfbericht](VERIFICATION.md)

## Abgleich

`tokenary/generator/__main__.py` ruft Ruff nicht mehr auf. Der Renderer in
`tokenary/generator/generator.py` erzeugt deterministischen Pythoncode selbst.
Ruff bleibt ein Entwicklungswerkzeug und wird nicht zur Laufzeitabhängigkeit.

## Verifizierte Kriterien

- [x] Generierung und Driftprüfung funktionieren ohne installierte Ruff-/Providerpakete.
- [x] Generiertes Pythonmodul lässt sich tatsächlich importieren und berechnen.
- [x] Gleiche Daten mit unterschiedlicher Eingabereihenfolge ergeben gleiche Ausgabe.
- [x] README dokumentiert die normale Installation ohne Ruff.

## Verifikation und Restauftrag

`tests/test_generator_selection.py` prüft Reproduzierbarkeit und importiert ein
Teilmodul in einem frischen Prozess. `scripts/smoke_installed.py` wurde gegen das
neu gebaute Wheel isoliert ausgeführt: erfolgreich, Runtimequellen 35.614 Bytes,
Einmodell-Artefakt 789 Bytes. Gesamte Suite: 86 bestanden.
Kein Implementierungs-PR nötig.
