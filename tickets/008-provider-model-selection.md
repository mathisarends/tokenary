# 008 — Providerfilter und kombinierte Auswahl ergänzen

- Status: partial
- Priorität des Rests: P1
- Bereits umgesetzt: [PR #1](https://github.com/mathisarends/tokenary/pull/1), `facde09`
- Offene Abhängigkeiten: keine
- Branch für Rest: `codex/ticket-008-provider-model-selection`
- Rest-PR: noch nicht erstellt
- Ablauf und Nachweise: [Index](README.md), [Prüfbericht](VERIFICATION.md)

## Bereits erledigt und verifiziert

- [x] `--models`/`--model` und Pythonparameter `models=` wählen genaue Modell-IDs.
- [x] CLI fordert bewusste Modellauswahl oder `--all`; ungültige und leere Auswahl scheitern.
- [x] Python-, JSON- und gzip-Ausgaben enthalten nur ausgewählte Modelle.
- [x] Namenskollisionen werden stabil aufgelöst; Teilkataloge stimmen mit Vollauswahl überein.
- [x] Ausgabe ist reproduzierbar und direkt mit der existierenden Runtime verwendbar.
- [x] `sample_spec` ist kein Modell; das kompakte Zielformat lässt es bewusst weg.
  Keine Wiedereinführung in den Runtimekatalog nötig.

## Restbefund

CLI und `build_catalog_payload` besitzen keinen Providerfilter. Die von Nutzern
gewünschte Auswahl nach Providern und deren Kombination mit Modell-IDs fehlt.
Der vorhandene Modellfilter soll erweitert, nicht durch eine zweite Pipeline ersetzt werden.

## Restauftrag und Akzeptanzkriterien

- [ ] Wiederholbares `--provider` und `providers=` an der bestehenden Generator-API ergänzen.
- [ ] Provider anhand `litellm_provider` auswählen, nicht anhand Modell-ID-Präfixen.
- [ ] Innerhalb einer Filterart ODER, zwischen Provider- und Modellfilter UND.
- [ ] Unbekannte Werte einzeln melden, leere Schnittmenge ablehnen; Duplikate unschädlich.
- [ ] Ohne Providerfilter bleiben Modelle ohne Provider per ID auswählbar.
- [ ] Provider-only ist eine vollständige Auswahl; `--all` nicht mit Filtern kombinieren.
  Bei der Python-API bedeutet `None` kein Filter, eine explizit leere Liste bleibt Fehler.
- [ ] Vollquelle weiterhin zur stabilen Namenszuordnung nutzen; nur Auswahl exportieren.
- [ ] Keine Eingabemutation; alle Ausgabeformate und Driftprüfung bleiben konsistent.
- [ ] CLI und README zeigen Provider-only und kombinierte Auswahl.

## Verifikation des Rest-PRs

Fixture mit zwei Providern, fehlender Providerangabe und kollidierenden Enum-Namen.
Provider-only, Modell-only, Kombination, unbekannte Werte, Duplikate, leere Auswahl
und `--all` prüfen. Bestehende Selektions-/Drifttests und Gesamtsuite erhalten.
Befehle und Ergebnisse im Ticket nachtragen.
