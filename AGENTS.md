# AGENTS.md

# Dokumentation
dokumentera ditt arbete i ~/dev/developer-notex/weekly-research-agent.md

-  en logg med ändringar
- skapa sidor och mappar för att beskriva vad som gjorts, vad som är kvar och vad appen föreställer.
- indexera i index.md

## Projektets mål

Detta repo bygger en CLI-baserad “Weekly Stock Market Science Agent” i Python med LangGraph.

Systemet ska producera en veckorapport som släpps varje söndag kväll eller måndag morgon, för att hjälpa traders att:
- förstå hur de bör positionera sig inför veckan
- se vilka teman/sektorer/momentumkluster som leder eller släpar
- förstå vilka signaler som stöder eller motsäger caset
- få en bild av vad som hänt under helgen
- förstå vad som bör bevakas under veckan
- se osäkerhet, risker och vad som skulle ändra grundcaset

Rapporten ska vara praktiskt användbar, spårbar och testbar.

---

## Arkitekturprinciper

Behåll tydlig separation mellan:

1. **Ingestion**
   - hämta marknadsinput från interna API:er, signals, sector rotation, momentum, web research och eventuella manuella notes
   - adapters ska returnera `ok/data/error/source`

2. **Retrieval / traceability**
   - alla källor ska lagras som source objects
   - source summaries ska sparas
   - packet och rapport ska stödja tydlig spårbarhet från påstående till källa

3. **Normalisering**
   - rådata omvandlas till jämförbara interna format i Python
   - momentum, sector rotation och signals ska normaliseras före LLM-syntes

4. **Syntes**
   - LLM används först efter att data reducerats och strukturerats
   - undvik att skicka stora råpayloads till modellen

5. **Workflow**
   - använd LangGraph med explicita noder och edges
   - föredra deterministiskt workflow framför fri agentloop

---

## Rapportens målbild

Rapporten ska vara designad för söndag kväll / måndag morgon.

Den ska innehålla:

1. Executive summary
2. Facts
3. Interpretation
4. Positioning for the week
5. Sector / theme rotation
6. Momentum leaders and laggards
7. Signals in focus
8. Weekend context / what happened
9. What to watch this week
10. Risks / uncertainty
11. What would change my mind
12. Sources / citations

---

## Guardrails

Detta är obligatoriskt:

- rapporten måste separera **facts** från **interpretation**
- rapporten måste ha tydliga källor/source references
- rapporten måste innehålla `what would change my mind`
- om data saknas ska det visas som data gaps, inte döljas
- rapporten får inte hitta på fakta som inte stöds av sources eller packet-data

---

## Signals

`signal_api.py` ska integreras som ett eget signalblock.

Krav:
- signals ska normaliseras
- de ska användas som stöd eller motvikt till momentum
- bygg `signal_summary` och gärna `signal_table`
- om signal-API saknas ska detta visas som data gap

---

## Web search

Websearch ska användas sparsamt men målmedvetet.

Primära användningar:
- weekend context
- viktiga händelser som hänt sedan fredagens close
- vad som väntas under veckan
- större katalysatorer som påverkar positioning

Websearch är inte primär källa för momentum eller sector rotation.

---

## Retrieval / source model

Varje viktig datapunkt eller slutsats ska kunna spåras till:
- source_id
- source_type
- title
- url om tillgänglig
- kort source summary om möjligt

Spara gärna:
- `sources.json`
- `source_summaries.json`
- `final_packet.json`
- `weekly_report.md`

---

## Eval

Lägg till regressionstester för minst:

- rapporten innehåller sources
- rapporten innehåller facts och interpretation som separata sektioner
- rapporten innehåller `what would change my mind`
- data gaps visas när endpoints saknas
- packet-/normaliseringslogik fungerar för momentum och sector rotation
- rapporten saknar inte citations/source refs i sektioner där externa claims görs

Målet är inte perfekt sanningskontroll, utan att reducera hallucinationsrisk genom struktur.

---

## Ops

Scheduling behöver inte byggas fullt nu, men koden ska förberedas för veckokörning.

Krav nu:
- tydlig CLI-entrypoint för veckorapport
- outputs ska sparas till filer
- loggar/debug-output ska finnas
- om möjligt, spara enkel run metadata:
  - timestamp
  - vilka källor som användes
  - eventuella data gaps
  - enkel modell-/token-/kostnadsinfo om lätt tillgängligt

Scheduling kan implementeras senare.

---

## Prioritet

1. Få en fungerande veckorapport
2. Integrera signaler
3. Integrera websearch för weekend context / weekly watchlist
4. Lägg till source traceability
5. Lägg till evals
6. Lägg till loggar / debug outputs / cost visibility
7. Scheduling sist

---

## Kodprinciper

- Gör små, säkra ändringar
- Behåll fungerande kod om inte omskrivning verkligen behövs
- Lägg inte domänlogik i `main.py`
- Alla externa fel ska fångas och returneras som data gaps eller felobjekt
- Inga tysta fel
- Spara debugbar state till filer i t.ex. `debug_output/`

---

## Definition of done

Uppgiften är klar när:

- `PYTHONPATH=src python -m agent_lab.research_main` fungerar
- programmet producerar både:
  - ett Research Packet
  - en färdig veckorapport
- rapporten innehåller momentum, sector rotation, signals och web context
- rapporten separerar facts och interpretation
- rapporten innehåller what would change my mind
- rapporten visar sources / citations / source refs
- data gaps syns tydligt
- minst några tester finns
- outputs sparas till filer
- README eller DEVELOPING.md beskriver hur man kör

---

## Förbjudna genvägar

- Mata inte stora råpayloads direkt till LLM om Python kan komprimera dem först
- Låt inte modellen själv lista ut API-shapes som redan kan kodas explicit
- Gör inte hela systemet till en fri agent om ett workflow räcker
- Dölj inte data gaps för att få snyggare output