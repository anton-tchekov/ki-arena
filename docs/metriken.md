# Metriken

Womit wir einen Lauf bewerten. Die Zahlen berechnet `analysis/statistics.py`,
sie stehen am Ende in der Konsole und im `logfile.txt`. Für
Multi-Seed-Vergleiche liefert `run_headless.py` dieselben Zahlen als
Mittelwert über die Seeds.

## Pro Lauf

- **Überlebte Zyklen**: unser Hauptmaß.
- **Nachhaltige Population**: Kopfzahl im Schnitt über alle Zyklen, damit
  verschieden lange Läufe vergleichbar sind.
- **Peak-Population** und **Durchschnittsalter** der Lebenden.
- **Tode nach Ursache** (Alter, Holzmangel, Fruchtmangel): zeigt, warum eine
  Gruppe stirbt, nicht nur dass sie stirbt.
- **Geburten und Tode pro Zyklus**.
- **Bäume am Ende**: Zustand des Waldes.

## Für LLM-Läufe zusätzlich

- Jeder API-Call landet in `llm_calls.jsonl` (`analysis/llm_logger.py`):
  Prompt, Antwort, Latenz, Tokens, Retries, Rolle, Guidance-Modus, Run-ID und
  Zyklus. `analysis/llm_call_stats.py` aggregiert das pro Modell (Latenz als
  Mittel/p50/p95, Tokens, optional Kosten).
- **Blackboard-Konflikte** (`analysis/coordination.py`): zählt, wie oft zwei
  Agenten denselben Baum claimen. Macht "Koordination nicht perfekt" zu einer
  Zahl.

## Qualitativ

- **Sterbemuster**: Hunger oder Alter? Stabil oder Boom-and-Bust? Sieht man an
  den Todesursachen und am Populations-Graph.
- **Koordination**: Reden die Agenten übers Blackboard sinnvoll, oder rennen
  alle auf denselben Baum? Sieht man im Replay und an den Plan-Zeilen im
  Logfile.

## Grenzen

Wir rechnen nur Mittelwerte, keine Konfidenzintervalle. LLM-Vergleiche sind
Einzelläufe, weil mehrere zu teuer wären. Mehr dazu in
[detailiertedoku/metrics.md](detailiertedoku/metrics.md).
