# 004 — Staffelvarianten absichern und Semantik belegen

- Status: partial
- Priorität des Rests: P2
- Bereits umgesetzt: [PR #1](https://github.com/mathisarends/tokenary/pull/1), `facde09`
- Offene Abhängigkeiten: keine
- Branch für Rest: `codex/ticket-004-context-price-tiers`
- Rest-PR: noch nicht erstellt
- Ablauf und Nachweise: [Index](README.md), [Prüfbericht](VERIFICATION.md)

## Bereits erledigt und verifiziert

- [x] `tokenary/pricing.py::ModelPricing.rate` berücksichtigt kontextabhängige Tarife.
- [x] Numerische Schwellen mit optionalem kleinem `k` oder `m` werden indexiert.
- [x] Es gilt strikt `input_tokens > threshold`; der höchste erreichte Tarif gewinnt.
- [x] Der Tarif gilt für die ganze Kategorie; Output verwendet die Input-Kontextlänge.
- [x] Cache- und einstündige Cache-Write-Tarife sind ebenfalls berücksichtigt.
- [x] Grenzwert-, Mehrfachstaffel- und Cachetests bestehen; Gesamtsuite: 86 Tests.

## Restbefund

Das ursprüngliche Hauptproblem, immer den Basispreis zu verwenden, ist behoben.
Nicht erkannte Staffel-Schreibweisen bleiben aber als Extra-Felder erhalten und
werden bei der Ratenauswahl ignoriert. Synthetische Probe:
`input_cost_per_token=1` plus `input_cost_per_token_above_200K_tokens=2` ergibt
bei 200.001 Inputtokens weiterhin Rate 1. Dies ist ein Robustheitsfall für eigene
oder zukünftige Daten, kein Nachweis dieses Feldes im gebündelten Katalog.
Die README erläutert die implementierte Semantik, belegt die Langkontextregeln
aber noch nicht mit spezifischen Primärquellen.

## Restauftrag und Akzeptanzkriterien

- [ ] Erkennbare, aber nicht unterstützte Token-Staffelfelder beim Validieren oder
  bei relevanter Nutzung verständlich abweisen, statt unbemerkt den Basistarif zu nutzen.
- [ ] Gültige andere Preiskategorien wie `above_1hr` und zukünftig unbekannte,
  nicht kontextbezogene Preisfelder weiterhin sauber unterscheiden.
- [ ] Semantik der unterstützten Kontextstaffeln anhand primärer Quellen belegen;
  Feldformen, Bezugsmenge und Grenzen dokumentieren.
- [ ] Unterhalb/gleich/oberhalb, mehrere Schwellen und explizite Nullpreise mit
  kleinen lokalen Fixtures absichern. Keine neuen Tarife ohne fachlichen Nachweis.

## Verifikation des Rest-PRs

Bestehende Staffellogik erhalten. Regression für nicht unterstützte Tokenstaffel
und unveränderte gültige Cache-Tarife ergänzen, dann gesamte Suite ausführen.
Befehle, Ergebnisse und Quellen hier im PR nachtragen.
