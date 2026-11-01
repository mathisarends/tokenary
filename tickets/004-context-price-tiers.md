# 004 — Staffelvarianten absichern und Semantik belegen

- Status: in_review
- Priorität des Rests: P2
- Bereits umgesetzt: [PR #1](https://github.com/mathisarends/tokenary/pull/1), `facde09`
- Offene Abhängigkeiten: keine
- Branch für Rest: `codex/ticket-004-context-price-tiers`
- Rest-PR: [#4](https://github.com/mathisarends/tokenary/pull/4)
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

- [x] Erkennbare, aber nicht unterstützte Token-Staffelfelder beim Validieren oder
  bei relevanter Nutzung verständlich abweisen, statt unbemerkt den Basistarif zu nutzen.
- [x] Gültige andere Preiskategorien wie `above_1hr` und zukünftig unbekannte,
  nicht kontextbezogene Preisfelder weiterhin sauber unterscheiden.
- [x] Semantik der unterstützten Kontextstaffeln anhand primärer Quellen belegen;
  Feldformen, Bezugsmenge und Grenzen dokumentieren.
- [x] Unterhalb/gleich/oberhalb, mehrere Schwellen und explizite Nullpreise mit
  kleinen lokalen Fixtures absichern. Keine neuen Tarife ohne fachlichen Nachweis.

## Verifikation des Rest-PRs

Bestehende Staffellogik erhalten. Regression für nicht unterstützte Tokenstaffel
und unveränderte gültige Cache-Tarife ergänzen, dann gesamte Suite ausführen.
Befehle, Ergebnisse und Quellen hier im PR nachtragen.

## Verifikation der Umsetzung

- Vorher: gezielte Tests `tests/test_context_tier_validation.py` ergaben
  6 Fehler/10 Erfolge; alle sechs unbekannten Tokenstaffelformen wurden ignoriert.
- Nachher: `C:/code/tokenary/.venv/Scripts/python.exe -m pytest --basetemp=.pytest_cache/tiers-after`:
  **123 passed** auf Python 3.14.0. Ruff-Lint/-Format, `git diff --check` und
  vollständige Bundledaten-Driftprüfung erfolgreich.
- Validierung weist erkennbare unbekannte `*_above_*_tokens`-Felder einschließlich
  Großschreibung und unbekannter Suffixe verständlich mit dem Feldnamen ab.
  Das gilt bei Generierung und erster Runtimevalidierung, auch für eigene Daten.
- Regressionsfälle: nackte Integer, kleines `k` und `m`, jeweils unter/gleich/über
  Schwelle, Nullpreis, Input/Output, bestehende Mehrfachstaffeln und Cache-TTLs.
- `above_1hr`, zukünftige nicht kontextbezogene Preise und bekannte separate
  `_priority`/`_batches`/`_flex`-Staffeln bleiben als eigene Kategorien erhalten.
  Diese Änderung implementiert keine zusätzliche Service-Tier-Abrechnung.
- Im gepinnten Snapshot vorkommende Standardschwellen: 128k, 200k, 256k, 272k,
  512k. Input/Output und Cache sind relevant; vorhandene Zeichen-/Bild-/Dauerfelder
  führen keine neuen Abrechnungseinheiten in die Runtime ein.

### Primärquellen zur Semantik (geprüft am 01.11.2026)

- [LiteLLM Model Cost Map](https://docs.litellm.ai/docs/proxy/model_cost_map):
  Langkontextsuffixe sind Varianten desselben Einheitspreises. Service-Tier-Suffixe
  und Cache-TTL (`above_1hr`) sind getrennte Bedeutungen.
- [Google Gemini API Pricing, Gemini 2.5 Pro](https://ai.google.dev/gemini-api/docs/pricing#gemini-2.5-pro):
  Input, Output und Cache haben nach Promptlänge gewählte Bänder für `<= 200k`
  und `> 200k`. Daraus folgt die hier verwendete Ratenauswahl pro Kategorie anhand
  des gesamten Inputs; keine progressive Teilmengenabrechnung.
- [Anthropic Long context pricing](https://platform.claude.com/docs/en/about-claude/pricing#long-context-pricing):
  Gesamter Prompt inklusive Cache-Reads/-Writes bestimmt das Band pro Request.
  Die aktuelle Seite beschreibt auch Modelle ohne Langkontextaufschlag. Daher
  wird keine universelle 200k-Regel angenommen: nur Felder des gewählten Snapshots
  werden angewandt. Dieser PR aktualisiert keine Snapshotpreise.

Tests sind kleine Offline-Fixtures und brauchen keine dieser Seiten oder Livepreise.
Python 3.13 und Remote-CI sind im lokalen Nachweis dieses Tickets noch nicht
enthalten. Kein Merge durchgeführt; Stackbasis ist Ticket 009 / PR #3.
