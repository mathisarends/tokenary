# 007 — Implizites Ausgabeziel absichern

- Status: partial
- Priorität des Rests: P2
- Bereits umgesetzt: [PR #1](https://github.com/mathisarends/tokenary/pull/1), `facde09`
- Offene Abhängigkeiten: keine
- Branch für Rest: `codex/ticket-007-explicit-generator-output`
- Rest-PR: noch nicht erstellt
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

- [ ] `--output` verpflichtend machen; Migration gegenüber 0.2 dokumentieren.
- [ ] Fehlendes Ziel sowie Argumentfehler vor Download, Katalogladen und Schreiben abweisen.
- [ ] Bestehende Formate, `--check`, Modellselektion und atomaren Austausch erhalten.
- [ ] CLI-Hilfe, README und Hilfsskript konsistent halten.
- [ ] Simulierten Austauschfehler testen: vorhandenes Ziel bleibt erhalten,
  temporäre Datei wird entfernt, CLI meldet Fehlercode.

## Verifikation des Rest-PRs

Argumentfehler ohne Seiteneffekte und vorhandenes Ziel bei `os.replace`-Fehler testen.
CLI als Modul und Console Script prüfen. Gesamtsuite ausführen und Ergebnisse
hier nachtragen. Kein Umbau des existierenden Katalogformats.
