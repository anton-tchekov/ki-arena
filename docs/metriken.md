# Metriken

Womit wir einen Lauf bewerten. Die Zahlen stehen am Ende in der Konsole und im
`logfile.txt` (`analysis/statistics.py`).

## Quantitativ

- Überlebte Zyklen (Hauptmaß).
- Nachhaltige Population: Schnitt der Kopfzahl über alle Zyklen. Als Schnitt, damit
  Läufe verschiedener Länge vergleichbar sind.
- Peak-Population.
- Durchschnittsalter der Lebenden.
- Tode nach Ursache: Alter / Holzmangel / Fruchtmangel. Zeigt, warum die Gruppe stirbt.
- Geburten und Tode pro Zyklus.
- Bäume am Ende (Zustand des Waldes).

## Qualitativ

- Sterbemuster: Hunger oder Alter? Stabil oder Boom-and-Bust? Sieht man an den
  Todesursachen und am Populations-Graph.
- LLM-Koordination: Reden die Agenten übers Blackboard sinnvoll, oder rennen alle auf
  denselben Baum? Sieht man am Blackboard und an den Plan-Zeilen im Logfile.

LLM-Aufrufe (Prompt, Antwort, Latenz, Tokens) landen über die Mistral-API in
`llm_calls.jsonl` (`analysis/llm_logger.py`). Ein Beispiel-Lauf und die Beobachtungen
dazu stehen in `docs/labnotebook.md`.
