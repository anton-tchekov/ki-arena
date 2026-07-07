# Ki-Arena – Projektdokumentation

Gruppe HAD · Anton Tchekov, Daniil Khoma, Haron Nazari · HAW Hamburg

## 1. Motivation und Zielsetzung

- Grid-Welt, KI-Agenten leben von geteilten Ressourcen
- Zwei Rollen teilen sich einen Wald: Collector sammeln Frucht, Cutter fällen Holz
- Jeder Agent braucht beides, beides kommt aus demselben Wald → Zielkonflikt
- Frage: ergibt sich aus einfachen Regeln eine Balance? Wie schlagen sich Regel-, RL- und LLM-Agenten?
- Ziel: lauffähige Simulation, drei vergleichbare Agenten-Typen, Werkzeuge zur Ursachenanalyse (Logs, Graphen, Metriken)

## 2. Architekturüberblick

![Architektur](diagrams/Architekturdiagramm.png)

Code unter `src/sim/`, Einstieg `main.py`:

- **environment/** – `world_grid.py` (Positionen/Bäume/Bewegung), `resource_manager.py` (Holz/Frucht/Verbrauch), `env_grid.py` (PettingZoo-Env: Schritte, Spawn, Tod), `config.py` (Stellschrauben), `renderer.py` + `control_panel.py` (Anzeige)
- **agents/** – `rule_agent.py`, `rl_agent.py` (Q-Learning), `llm_agent.py`, `blackboard.py` (gemeinsame Tafel für LLM-Kommunikation)
- **arena/** – `runner.py` (Episode ausführen), `phases.py` (Training/Ausführung)
- **analysis/** – `statistics.py`, `run_logger.py`, `llm_logger.py`, CSV-Logger
- **llm/** – Anbindung an die Mistral-API

Ablauf: Runner fragt jeden Agenten reihum (`act`) → Umgebung führt Aktion aus + vergibt Belohnung → globaler Schritt (Bäume wachsen, Ressourcen verbraucht, Spawn bei genug Vorrat, Tod an Alter/Mangel).

Bezug zur Vorlesung: Regel-Agent = Simple Reflex, RL/LLM = lernend. Memory: Q-Tabelle (RL) bzw. Blackboard/Kontext (LLM). Action: Bewegen/Interagieren.

## 3. Designentscheidungen

- PettingZoo (AEC) als Standard für Multi-Agenten – Reihenfolge, Termination und Spaces gibt es damit gratis
- ResourceManager getrennt von der Welt – Ressourcen-Bilanz an einer Stelle, Grid bleibt schlank
- alles über `config.py` – eine Konstante ändern reicht für ein Experiment
- gleiche `act()`-Schnittstelle für alle Agenten – Regel, RL, LLM sind austauschbar
- Blackboard als Klartext – lesbar für Mensch und Modell
- Geometrie fürs LLM vorberechnen – kleine Modelle navigieren Grids schlecht, daher konkreter Hinweis plus Fallback-Aktion
- robustes Parsing – bei ungültiger Antwort greift die Fallback-Aktion
- ein Matplotlib-Fenster für Grid und Control Panel, weil sich zwei Fenster unter Wayland nicht positionieren ließen
- Logfile wird pro Lauf überschrieben – Konfig-Kopf einmal, dann knappe Ereignisse

## 4. Evaluation und Ergebnisse

Details in `docs/experiment.md`, Metriken in `docs/metriken.md`.

Hypothese: `tree_spawn_rate` entscheidet über das Überleben. Vier Werte, je 3 Seeds, Regel-Agenten, headless (`src/sim/run_headless.py`):

| tree_spawn_rate | Zyklen | Schnitt-Pop | Todesursache      |
|-----------------|--------|-------------|-------------------|
| 0.1             | 105    | 5.0         | Holzmangel        |
| 0.3             | ~784*  | 4.7         | Alter (bimodal)   |
| 0.5 (Standard)  | 527    | 6.8         | Alter             |
| 0.9             | 619    | 7.7         | Alter             |

Am Rand bestätigt sich das: bei 0.1 kollabiert das System durch Holzmangel, ab 0.3
sterben alle an Alter, und Peak-Population und Spawns steigen monoton mit der Rate.
Die Laufdauer selbst ist mit der aktuellen Konfig aber nicht mehr monoton.

\* Bei 0.3 ist der Ausgang bimodal (Boom-oder-Bust) – gleiche Konfig, nur der Seed
entscheidet zwischen 1000–2000 Zyklen (Boom) oder Aussterben bei exakt Zyklus 250
(Bust, nie ein Spawn). Details in `docs/experiment.md`, Läufe: `saves/greedy-0.3-boom.bin`
und `saves/greedy-0.3-bust.bin`.

Iteration: eine Cutter-Schonregel half gegen den Kollaps nicht, weil der Engpass der
Holz-Durchsatz war, nicht die Baumzahl. Mehr Holz pro Baum (5→10) half dagegen, kein
Hungertod mehr. Überraschung dabei: bei Standard-Werten stirbt die Gruppe an Alter,
nicht an Hunger, weil die Frucht selten über die Spawn-Schwelle kommt.

### Agenten-Vergleich: Regel vs. RL vs. LLM

Gleiche Standard-Konfig (3 Collector + 2 Cutter), Seed 1, bis zum natürlichen Tod
(kein Zyklen-Cap); LLM über Mistral-API (`magistral-small-latest`):

| Agenten-Typ             | Überlebt (Seed 1) | Todesursache | Holz Ende  | Frucht Ende | Bäume Ende |
|-------------------------|--------------------|--------------|------------|-------------|------------|
| RL (Q-Learning, 300 Ep) | 60 Zyklen          | Holzmangel   | 0          | 52          | 20 (unberührt) |
| LLM (Mistral)           | 172 Zyklen         | Fruchtmangel | ~260       | 0           | 12         |
| Regel (Greedy)          | 461 Zyklen         | Alter        | balanciert | balanciert  | 20         |

3-Seed-Mittel: Greedy 527, RL 60. Der LLM-Lauf ist ein Einzellauf, teuer und wegen der
API nicht deterministisch. Ergebnis: Regel schlägt LLM schlägt RL, und die beiden
Lern-Agenten scheitern an entgegengesetzten Enden derselben Holz/Frucht-Balance.

Der RL-Agent verliert klar – seine Cutter lernen das Fällen nicht, der Wald bleibt
unberührt bei 20 Bäumen, Holz auf 0, alle verhungern. Das gilt auch mit korrekt
verdrahteter, geshapeter Belohnung (wir hatten einen Reward-Caching-Bug gefunden und
gefixt, es änderte nichts am Ergebnis) und mit mehr Training. Der LLM-Agent macht das
Gegenteil: seine Cutter fällen zu eifrig, das Holz häuft sich auf ~260, während die
Frucht auf 0 fällt. Er koordiniert zwar explizit über das Blackboard, zielt aber
trotzdem oft mit allen Collectoren auf denselben reichsten Baum. Der Regel-Agent
bleibt die robuste Messlatte: balancierte Ökonomie, Tod erst an Alter.

Details in `docs/labnotebook.md`, Replays: `saves/rl-collapse.bin`, `saves/llm-coordination.bin`.

## 5. Limitationen und Failure Modes

- Kein Fallback, wenn Mistral-API-Key fehlt (nur LLM-Läufe betroffen)
- Volle Sicht statt Teilwissen – noch kein echtes POMDP
- Sehr config-empfindlich, kleine Änderungen → große Wirkung
- LLM-Läufe langsam/teuer → Evaluation primär mit Regel-Agenten
- Edge Cases + Lösungen: `docs/edgecases.md`

## 6. Mit mehr Zeit

- Teilwissen (Sichtradius) einbauen
- LLM, RL und Regel direkt im selben Lauf vergleichen
- API robuster machen (Timeout, Retry, Fallback)
- Mehr Rollen mit gegensätzlichen Zielen für echte Aushandlung
- Experiment-Runner, der Varianten selbst fährt und Tabellen erzeugt
