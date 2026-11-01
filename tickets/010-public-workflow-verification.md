# 010 — Restfunktionen in Doku und Wheel-Test integrieren

- Status: partial
- Priorität des Rests: P2
- Bereits umgesetzt: [PR #1](https://github.com/mathisarends/tokenary/pull/1), `facde09`
- Offene Abhängigkeiten: 004, 007, 008, 009
- Branch für Rest: `codex/ticket-010-workflow-verification`
- Rest-PR: noch nicht erstellt
- Ablauf und Nachweise: [Index](README.md), [Prüfbericht](VERIFICATION.md)

## Bereits erledigt und verifiziert

- [x] README erklärt Standardberechnung, Requests, Modellfilter, eigene Python-/JSON-
  Kataloge, Fehler, Migration zu inklusiven Tokenmengen und Reproduzierbarkeit.
- [x] Wheel-Smoke prüft ohne Ruff/Provider-SDKs tatsächlichen Paketimport, Generierung,
  Driftprüfung, eigene Berechnung und danach den Standardkatalog.
- [x] CI enthält Python 3.13/3.14, Tests, Lint, Driftprüfung, Wheel-Build und Smoke-Test.
- [x] Reproduzierbarer Benchmarkbefehl ist vorhanden und wurde lokal ausgeführt.

## Restbefund

Providerfilter und getrenntes Laden fehlen noch und können noch nicht vollständig
beschrieben/getestet werden. Der vorhandene Wheel-Smoke erzeugt nur Python und
verwendet `gpt-4o`, also eine bereits bekannte Modell-ID. Er ruft nur
`python -m tokenary.generator` auf, nicht das installierte Console Script.
JSON-Roundtrips und eigene IDs sind in Unit-Tests vorhanden, aber noch nicht in
allen entsprechenden Wheel-Integrationspfaden.

## Restauftrag und Akzeptanzkriterien

- [ ] README/Beispiele um Provider-only und kombinierte Filter sowie das endgültige
  Ausgabe-/Staffelfehlerverhalten ergänzen. Bestehende öffentliche API erhalten.
- [ ] Installiertes Wheel mit eigener, nicht gebündelter Modell-ID durchspielen:
  lokale Quelle, Reduktion, JSON/gzip laden, korrekte Berechnung.
- [ ] Nicht ausgewählte Modelle ablehnen; keine gebündelten Preise bei eigener Nutzung laden.
- [ ] Installiertes Console Script und Modulaufruf abdecken.
- [ ] Ressourcen-Ladegarantien aus 009 im integrierten Workflow absichern.
- [ ] Aktualisierte Suite und Wheel-Smoke auf beiden CI-Pythonversionen nachweisen.
- [ ] Messbedingungen und Performancegrenzen ehrlich dokumentieren; den jeweiligen
  Code-Stand der gemessenen Wheel-Version angeben.
- [ ] Ticketindex mit tatsächlichen Rest-PRs und Merge-Status aktualisieren.

## Verifikation des Rest-PRs

Offline-Fixtures, Wheelinstallation außerhalb des Checkouts und ohne Ruff/SDKs.
Alle geänderten Beispiele ausführen. Gesamtsuite und Wheel-Smoke ausführen;
CI-Links für beide Pythonversionen ergänzen. Beim aktuellen Abgleich wurde lokal
nur Python 3.14 ausgeführt; die CI-Konfiguration ist kein Nachweis eines grünen Laufs.
