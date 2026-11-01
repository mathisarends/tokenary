# Tokenary: verifizierte Review-Tickets

Abgleich am 01.11.2026 gegen `facde09` (v0.2.0), den Merge von
[PR #1](https://github.com/mathisarends/tokenary/pull/1). Die Tickets wurden nach
Codeprüfung, 86 bestandenen Tests und einem erfolgreichen isolierten Wheel-Test
aktualisiert. Einzelheiten und Grenzen stehen im [Prüfbericht](VERIFICATION.md).

**Fünf Tickets sind erledigt, fünf haben einen begrenzten Restumfang.**
`done` bedeutet durch den bereits gemergten PR umgesetzt und lokal verifiziert.
`partial` bedeutet: nur den beschriebenen Rest bearbeiten, keine Neuimplementierung.
Die ursprünglichen Architekturvorschläge sind durch die tatsächlich vorhandene
öffentliche API ersetzt. Insbesondere keine parallele `Catalog`/`Calculator`-API
oder Umbenennung von `MissingPriceError` einführen.

## Status und Reihenfolge

| Ticket | Priorität des Rests | Verbleibende Aufgabe | Offene Abhängigkeiten | Status |
| --- | --- | --- | --- | --- |
| [001](001-usage-validation.md) | — | Verbrauchswerte bereits validiert | keine | done |
| [002](002-zero-reasoning-rate.md) | — | Reasoningpreis null bereits korrekt | keine | done |
| [003](003-missing-pricing.md) | — | Fehlende Preise werden explizit gemeldet | keine | done |
| [004](004-context-price-tiers.md) | P2 | Unbekannte Staffelvarianten abgesichert und Semantik belegt | keine | in_review |
| [005](005-generator-without-ruff.md) | — | Generator funktioniert ohne Ruff | keine | done |
| [006](006-explicit-catalog-runtime.md) | — | Eigene Kataloge und entkoppelte Runtime vorhanden | keine | done |
| [007](007-explicit-generator-output.md) | P2 | Explizites Ausgabeziel abgesichert | keine | in_review |
| [008](008-provider-model-selection.md) | P1 | Providerfilter und kombinierte Auswahl ergänzt | keine | in_review |
| [009](009-lazy-bundled-catalog.md) | P1 | Providerdaten und Namenshistorie getrennt geladen | 008 | in_review |
| [010](010-public-workflow-verification.md) | P2 | Restfunktionen in Doku und Wheel-Test integrieren | 004, 007, 008, 009 | partial |

Empfohlene Bearbeitungsfolge: **008 → 009 → 004 → 007 → 010**.
Auf ausdrücklichen Nutzerauftrag vom 01.11.2026 werden diese Rest-PRs seriell
als Stack gebaut: 008 gegen `main`, jeder weitere gegen den vorherigen Branch.
Die Vorgaben „gegen main“ und „erst nach Merge beginnen“ gelten für diesen Stack
entsprechend erst nach dem Retargeting. Kein automatischer Merge; die Status
bleiben bis zum tatsächlichen Merge `in_review`. CI prüft auch gestapelte PRs.
Der Modellfilter und die explizite Katalogverwendung existieren bereits; 008 muss
nicht auf einen erneuten Bau dieser Funktionen warten. Erledigte Voraussetzungen
aus PR #1 gelten als erfüllt. Keine PRs nur zum Wiederholen erledigter Tickets.

## Ablauf für Agents

1. Dieses Dokument, den Prüfbericht, das gewählte Ticket und geltende `AGENTS.md`
   lesen. Auf aktuellem `main` prüfen, ob seit dem Abgleich weitere Teile erledigt sind.
2. Vor Arbeitsbeginn vorhandene PRs zur Ticket-ID prüfen. Bestehenden PR fortführen
   oder die Belegung klären; keine doppelte Umsetzung starten.
3. Eigener Branch `codex/ticket-NNN-kurzname` vom aktuellen `main`, möglichst eigener
   Worktree. Nicht direkt auf `main` implementieren. Fremde Änderungen erhalten.
   Beim Abgleich war im ursprünglichen Checkout `uv.lock` bereits lokal verändert.
4. Nur den Restauftrag des Tickets umsetzen, mit gezieltem Regressionstest. Zusätzliche
   Befunde als Folgeticket erfassen. Ohne Parallelauftrag nur ein Ticket bearbeiten.
5. Akzeptanzkriterien, gezielte Tests und danach die ganze Suite ausführen. Offline-
   Fixtures verwenden; keine aktuellen Providerpreise als Testgrundlage.
6. Im selben PR Ticketstatus auf `in_review` setzen, Kriterien und konkrete Befehle/
   Ergebnisse dokumentieren. Nicht ausgeführte Prüfungen ausdrücklich kennzeichnen.
7. Ein isolierter PR gegen `main`, Titel `[NNN] Konkretes Ergebnis`. Beschreibung:
   Problem, Verhalten danach, Ticketlink, Verifikation. Nur zugehörige Dateien.
   Kein automatischer Merge. Bei fehlendem Push-/PR-Zugriff Branch und Blocker melden.
8. Nach tatsächlichem Merge Status `done` und PR-Link ergänzen, bei Bedarf beim Start
   des nächsten Tickets. Abhängige Tickets beginnen erst nach Merge ihrer Restarbeiten.

## Tatsächliche öffentliche Schnittstelle

```python
from tokenary import PricingCatalog, calculate

catalog = PricingCatalog.from_file("./prices.json")
result = calculate(
    model="gpt-4o-mini", input_tokens=1000, output_tokens=500, catalog=catalog
)
```

```bash
# Bereits vorhanden: genaue Modell-IDs; auch --model ist ein Alias.
tokenary-generate --models gpt-4o gpt-4o-mini --output ./prices.json
# Bereits vorhanden: bewusste Vollauswahl und lokale Quelle.
tokenary-generate --input prices.lock.json --all --output ./prices.json.gz
# Geplant in 008: Provider und Kombination mit Modell-IDs.
tokenary-generate --provider openai --models gpt-4o --output ./prices.json
```

JSON-Ausgaben sind versionierte, mit Prüfsummen versehene Kataloge. Rohe LiteLLM-
Mappings werden mit `PricingCatalog.from_raw_prices(...)` geladen, nicht mit
`from_file(...)`. Generierte Pythonmodule exportieren `CATALOG` und `ModelName`.
Runtimeberechnung bleibt in `tokenary.calculate(..., catalog=...)`.

Input-/Outputtokens sind seit 0.2 **inklusive Gesamtmengen**. Reasoning, Audio und
Cache sind Teilmengen und dürfen nicht noch einmal zum Gesamtpreis addiert werden.
Neue Tests und Beispiele müssen diesen bestehenden Vertrag beachten.

## Gemeinsame Verifikation

- CI konfiguriert Python 3.13 und 3.14; Standardbefehl: `uv run pytest`.
- Importverhalten in frischen Subprozessen prüfen. `loaded_model_count` misst nur
  validierte Preisobjekte, nicht eingelesene Rohdaten. Für 009 zusätzlich Datei- und
  Ressourcenlesen beobachten; `sys.modules` erfasst JSON-Lesen nicht.
- Wheel-Tests außerhalb des Checkouts, ohne dessen `PYTHONPATH`, ohne Ruff und ohne
  Provider-SDKs. Vorhanden: `scripts/smoke_installed.py`.
- Bei Windows-Temp-Problemen `.pytest_cache` vorher anlegen und einen neuen Pfad
  darin als `--basetemp` nutzen. Pytest kann bestehende Basetemp-Inhalte löschen;
  niemals einen Ordner mit Nutzdaten angeben.
- Jede PR liefert eigene Tests und Dokumentation. 010 ergänzt die Integration,
  ersetzt aber keine Einzelverifikation.
- Performancemessungen mit gleicher Umgebung wiederholen; keine plattformübergreifenden
  Grenzwerte aus einzelnen lokalen Laufzeiten ableiten.
