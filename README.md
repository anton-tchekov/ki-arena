# ki-arena
SoSe2026 KI Praktikum Agent Arena Projekt

![Alt Text](sim.gif)

## Gruppenteilnehmer

- Daniil Khoma
- Haron Nazari
- Anton Tchekov

## Bedienungsanleitung

### Projektorientierung

Der gesamte Code liegt unter `src/sim/`, Einstiegspunkt ist `main.py`.

- **`environment/`** – Simulationsumgebung: Spielwelt, Regeln, Ressourcen und Visualisierung.
- **`agents/`** – Die Agententypen: regelbasiert, RL und LLM.
- **`arena/`** – Ablaufsteuerung der Simulation (Phasen und Episoden).
- **`analysis/`** – Auswertung und Protokollierung der Läufe.
- **`llm/`** – Anbindung an ein lokales Sprachmodell über Ollama oder Mistral API.

### Projekt starten

Richtiges Verzeichnis betreten:
```
cd src/sim
```

Gegebenenfalls Abhängigkeiten installieren:
```
pip install pettingzoo
```

Wenn im code eine LLM genutzt wird, dann muss Model mit Ollama im Hintergrund laufen:
```
ollama run ministral-3:3b
```

Ausführen:
```
python main.py
```

## Projektbeschreibung

Im Projekt soll ein Spiel umgesetzt werden, in dem mehrere
gleich große Teams, bestehend aus mehreren KI-Agenten in
einer Arena Ressourcen verwenden müssen. Das Spielfeld ist eine
Top-Down Karte mit einem rechteckigem Grid, auf dem sich
die Agenten bewegen können.

Die Felder auf dem Spielfeld haben verschiedene Eigenschaften,
unter anderem Ressourcenfelder, die Agenten erreichen und
je nach ihrer Rolle verwenden müssen.

Die Agenten haben eine begrenzbare Sicht auf das Spielfeld,
und verschiedene Ziele. Das Ziel ist das in der Simulation
alle Teams in einem bestimmten Maße kooperativ handeln,
und sich eine Balance herausbildet, jedoch jede Gruppe
von Agenten trotzdem ihre eigenen Interessen verfolgt.

### Agenten

Es sollen einfache Regelbasierte Agenten, RL-Agenten und LLM-Agenten
miteinander verglichen werden.

Es gibt aktuell zwei Gruppen von Agenten in der Simulation, einmal die
Holzfäller, die Bäume fällen, und die Früchtesammler, die von den Bäumen
Früchte sammeln. Das Ziel ist, dass idealerweise die Agenten so handeln,
dass die Ressourcen der Spielwelt erhalten bleiben, und gleichermaßen
die Bedürfnisse der Agenten an Holz und Früchten erfüllt sind.

Zudem sollen in einer Weiterentwicklung weitere Agenten hinzugefügt werden,
welche andere Ziele verfolgen, die auch (teilweise) in Konflikt zu den Zielen
der anderen Agenten stehen.

### Architektur

![architektur](docs/diagrams/Architekturdiagramm.png)