# Agenten

Alle drei Typen nutzen dieselbe `act()`-Schnittstelle und sind damit
austauschbar. Jeder Typ existiert in beiden Rollen (Cutter und Collector).
Code liegt unter `src/sim/agents/`.

| Agent | Taxonomie | Memory | Planning |
|---|---|---|---|
| Regel | Simple Reflex | keins | feste Regeln |
| RL | Learning | Q-Tabelle | gelernt im Training |
| LLM | Learning | Blackboard und Kontext | Prompt-Reasoning |

## Regelbasiert (Greedy)

`rule_agent.py`. Fest verdrahtete Regeln, kein Memory, deterministisch bei
festem Seed. Der Agent sucht den nächsten Baum, für den kein anderer Agent
näher dran ist (`_pick_uncontested_tree`), läuft hin und interagiert. So
verteilen sich die Agenten von selbst auf verschiedene Bäume. Gibt es keinen
freien Baum, wandert er zufällig. Braucht keine API und ist schnell, deshalb
ist er unsere Messlatte für alle Experimente.

## RL (Q-Learning)

`rl_agent.py`. Tabellarisches Q-Learning, kein neuronales Netz. Die
Beobachtung (Position, Richtung zum nächsten Baum, Ressourcenstände) wird in
grobe Buckets diskretisiert und als Key in die Q-Tabelle gesteckt. Training
läuft über mehrere Episoden mit Epsilon-Greedy-Exploration, die Belohnung
kommt aus konfigurierbaren Reward-Funktionen (`CompositeRewardFn`). Nach dem
Training wird mit der gelernten Tabelle gespielt.

## LLM (Mistral API)

`llm_agent.py`. Jeder Zug ist ein API-Call: Der Prompt enthält Rolle,
Position, eine ASCII-Karte, die Baumliste und das Blackboard. Das Modell
antwortet mit `ACTION:` (Bewegung oder INTERACT) und `PLAN:` (kurze Nachricht
ans Team). Details und ein echter Beispiel-Prompt stehen in
[detailiertedoku/promptdoc.md](detailiertedoku/promptdoc.md).

- **Blackboard** (`blackboard.py`): gemeinsame Tafel als Klartext, der einzige
  Kommunikationsweg zwischen den Agenten. Dort claimen sie Bäume, warnen vor
  Knappheit oder geben sich gegenseitig Anweisungen.
- **Guidance** (Standard): Weil kleine Modelle ein Grid schlecht navigieren,
  rechnen wir die Geometrie in Python vor und geben dem Modell einen fertigen
  Hinweis ("choose RIGHT"). Bereits geclaimte Bäume werden aus der Zielwahl
  gefiltert. Mit `--llm-no-guidance` schalten wir das komplett ab, dann muss
  das Modell selbst navigieren.
- **Robustes Parsing**: Bei kaputter Antwort greift eine Fallback-Aktion, die
  Umgebung bekommt nie eine ungültige Aktion.
