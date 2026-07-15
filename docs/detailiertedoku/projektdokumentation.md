# Ki-Arena - Projektdokumentation

Gruppe HAD, Anton Tchekov, Daniil Khoma, Haron Nazari, HAW Hamburg

## 1. Motivation und Zielsetzung

- Grid-Welt, Agenten leben von geteilten Ressourcen
- zwei Rollen, ein Wald: Collector sammeln Frucht, Cutter fällen Holz
- jeder Agent braucht beides, also Zielkonflikt zwischen eigenem Überleben und gemeinsamem Wald
- Frage: ergibt sich aus einfachen Regeln eine Balance? Wie schlagen sich Regel-, RL- und LLM-Agenten dabei?
- Ziel: lauffähige Simulation, drei vergleichbare Agenten-Typen, Werkzeuge zur Ursachenanalyse (Logs, Graphen, Metriken)

## 2. Architekturüberblick

![Architektur](../diagrams/Architekturdiagramm.png)

Code unter `src/sim/`, Einstieg `main.py`:

| Modul | Inhalt |
|---|---|
| `environment/` | `world_grid.py` (Positionen/Bäume/Bewegung), `resource_manager.py` (Holz/Frucht/Verbrauch), `env_grid.py` (PettingZoo-Env: Schritte, Spawn, Tod), `config.py` (Stellschrauben), `renderer.py` + `control_panel.py` (Anzeige) |
| `agents/` | `rule_agent.py`, `rl_agent.py` (Q-Learning), `llm_agent.py`, `blackboard.py` (gemeinsame Tafel für LLM-Kommunikation) |
| `arena/` | `runner.py` (Episode ausführen), `phases.py` (Training/Ausführung) |
| `analysis/` | `statistics.py`, `run_logger.py`, `llm_logger.py`, CSV-Logger |
| `llm/` | Anbindung an die Mistral-API |

Ablauf pro Zyklus:

1. Runner fragt jeden Agenten reihum (`act`)
2. Umgebung führt Aktion aus, vergibt Belohnung
3. globaler Schritt: Bäume wachsen, Ressourcen werden verbraucht, Spawn bei genug Vorrat, Tod an Alter/Mangel

Bezug zur Vorlesung:

| Agent | Taxonomie | Memory | Planning | Action |
|---|---|---|---|---|
| Regel | Simple Reflex | keins | feste Thresholds | bewegen/interagieren |
| RL | Learning | Q-Tabelle | gelernt aus Training | bewegen/interagieren |
| LLM | Learning | Blackboard/Kontext | Prompt-Reasoning | bewegen/interagieren |

## 3. Designentscheidungen

- PettingZoo (AEC) als Standard für Multi-Agenten, Reihenfolge/Termination/Spaces gibt es damit gratis
- ResourceManager getrennt von der Welt, Ressourcen-Bilanz an einer Stelle, Grid bleibt schlank
- alles über `config.py`, eine Konstante ändern reicht für ein Experiment
- gleiche `act()`-Schnittstelle für alle Agenten, Regel/RL/LLM sind austauschbar
- Blackboard als Klartext, lesbar für Mensch und Modell
- Geometrie fürs LLM standardmäßig vorberechnen, kleine Modelle navigieren Grids schlecht, daher konkreter Hinweis + Fallback-Aktion (per `--llm-no-guidance` abschaltbar, siehe Kapitel 4)
- robustes Parsing, bei ungültiger Antwort greift die Fallback-Aktion
- ein Matplotlib-Fenster für Grid + Control Panel, zwei Fenster ließen sich unter Wayland nicht positionieren
- Logfile wird pro Lauf überschrieben, Konfig-Kopf einmal, dann knappe Ereignisse

## 4. Evaluation und Ergebnisse

Details: `docs/experiment.md` (Hypothese, Aufbau, Rohdaten), `docs/metriken.md` (Metrik-Definitionen).

**Hypothese:** `tree_spawn_rate` entscheidet über das Überleben. Vier Werte, je 3 Seeds, Regel-Agenten, headless.

| tree_spawn_rate | Zyklen | Schnitt-Pop | Todesursache |
|---|---|---|---|
| 0.1 | 105 | 5.0 | Holzmangel |
| 0.3 | ~784* | 4.7 | Alter (bimodal) |
| 0.5 (Standard) | 527 | 6.8 | Alter |
| 0.9 | 619 | 7.7 | Alter |

\* bimodal (Boom oder Bust): 1000-2000 Zyklen (Boom) oder Aussterben bei exakt Zyklus
250 (Bust, nie ein Spawn), gleiche Konfig, nur der Seed entscheidet. Details:
`docs/experiment.md`, Saves: `saves/greedy-0.3-boom.bin`, `saves/greedy-0.3-bust.bin`.

- Ränder bestätigen Hypothese: bei 0.1 Holzmangel-Kollaps, ab 0.3 nur noch Alterstod
- Peak-Population und Spawns steigen monoton mit der Rate
- Laufdauer selbst ist nicht monoton (0.3 überlebt im Schnitt länger als 0.5/0.9, wegen der Streuung)

**Iteration gegen den 0.1-Kollaps:**

| Fix | Ergebnis |
|---|---|
| Cutter schonen den Wald (`forest_reserve`) | bringt nichts, Engpass ist Holz-Durchsatz, nicht Baumzahl |
| mehr Holz pro Baum (5 auf 10) | hilft, kein Hungertod mehr, Gruppe stirbt an Alter |

**Agenten-Vergleich** (Standard-Konfig, Seed 1, natürlicher Tod, LLM über `magistral-small-latest`):

| Agent | Zyklen | Todesursache | Holz Ende | Frucht Ende | Bäume Ende |
|---|---|---|---|---|---|
| RL (Q-Learning, 300 Ep) | 60 | Holzmangel | 0 | 52 | 20 (unberührt) |
| LLM (Mistral) | 172 | Fruchtmangel | ~260 | 0 | 12 |
| Regel (Greedy) | 461 | Alter | balanciert | balanciert | 20 |

- 3-Seed-Mittel: Greedy 527, RL 60 (LLM war nur ein Einzellauf, zu teuer für mehrere und eh nicht deterministisch)
- Ranking: Regel schlägt LLM schlägt RL
- RL und LLM scheitern an entgegengesetzten Enden derselben Holz/Frucht-Balance:
  - RL-Cutter lernen das Fällen nicht, auch mit korrekt verdrahtetem Reward und mehr Training nicht. Ist eine echte Lerngrenze, kein Reward-Bug
  - LLM-Cutter fällen zu eifrig, Collectoren kommen nicht hinterher, deshalb Fruchtmangel trotz Holz-Überschuss
- Details: `docs/labnotebook.md`, Saves: `saves/rl-collapse.bin`, `saves/llm-coordination.bin`

**Zusatzexperiment: Mistral-Modelle im Vergleich** (5 von 6, `ministral-14b-2512`
noch offen, Details + Blackboard-Analyse in `docs/experiment.md`)

| Modell | Größe | Zyklen | Todesursache | Kosten |
|---|---|---|---|---|
| ministral-3b-2512 | 3B | 245 | Holzmangel | $0.19 |
| ministral-8b-2512 | 8B | 70 | Holzmangel | $0.08 |
| mistral-small-2603 | 119B MoE (~6B aktiv) | 250 | Alter | $0.29 |
| mistral-medium-3-5 | 128B | 500 (Cap)* | Alter | $2.79 |
| mistral-large-2512 | 675B MoE (~41B aktiv) | 360 | Alter | $0.95 |

\* mit höherem Cap (3000) stirbt `mistral-medium-3-5` natürlich bei 795 Zyklen
an Alter (21 Alter/0 Holz/3 Frucht), $3.04. Der 500er-Cap hatte die echte
Lebensdauer versteckt. Save: `saves/mistral-medium-3-5-3000cap.bin`.

Blackboard-/Bewegungsanalyse: Cutter erreichen selten Adjazenz zu einem Baum,
interagieren aber immer korrekt sobald sie adjazent sind. Der Engpass ist also
Navigation, nicht Entscheidung. Adjazenz-Rate folgt der Modellgröße und
erklärt die Todesursache direkt (niedrigste Rate führt zu Holzmangel, höhere
Rate zu Alter):

| Modell | Cutter-Züge | Adjazenz erreicht | Bei Adjazenz interagiert |
|---|---|---|---|
| ministral-3b-2512 | 860 | 3.0% | 100% |
| ministral-8b-2512 | 550 | 1.8% | 100% |
| mistral-small-2603 | 1507 | 5.9% | 100% |
| mistral-medium-3-5 | 818 | 13.6% | 100% |
| mistral-large-2512 | 512 | 16.2% | 100% |

**Aber wie viel davon ist das Modell, und wie viel unser Code?**

`_plan_navigation()` rechnet den nächsten Baum vor und sagt dem Modell praktisch
die Bewegung an ("choose RIGHT"). Um zu sehen was das Modell ohne diese Hilfe
selbst kann, gibt es `--llm-no-guidance` (schaltet Zielberechnung, Claim-Filter
und die feste Fallback-Aktion komplett ab):

| Modell | Zyklen (mit Guidance) | Zyklen (ohne Guidance) |
|---|:---:|:---:|
| ministral-3b-2512 | 245 | 50 |
| ministral-8b-2512 | 70 | 50 |
| mistral-small-2603 | 250 | 50 |
| mistral-medium-3-5 | 500/795* | 55 |
| mistral-large-2512 | 360 | 50 |

\* Cap 500 bzw. natürlicher Tod bei Cap 3000.

Ohne Guidance kollabieren alle 5 Modelle unabhängig von ihrer Größe gleich
schnell (50-55 Zyklen, Holzmangel). Die Adjazenz-Tabelle oben zeigt also
größtenteils wie gut unsere mechanische Hilfe ist, nicht wie gut das Modell
wirklich navigieren kann.

## 5. Limitationen und Failure Modes

- kein Fallback, wenn Mistral-API-Key fehlt (nur LLM-Läufe betroffen)
- volle Sicht statt Teilwissen, noch kein echtes POMDP
- sehr config-empfindlich, kleine Änderungen haben große Wirkung
- LLM-Läufe langsam/teuer, Evaluation läuft deshalb primär mit Regel-Agenten
- `reasoning_effort` (Thinking-Modus) unpraktikabel: ~250s/Call bei Medium, ~8s/Call bei Small
- Blackboard-Notizen toter Agenten (Alter/Hunger) werden nicht aufgeräumt (Bug, offen)
- Edge Cases + Lösungen: `docs/edgecases.md`

## 6. Mit mehr Zeit

- Teilwissen (Sichtradius) einbauen
- LLM, RL und Regel direkt im selben Lauf vergleichen
- API robuster machen (Timeout/Retry vorhanden, noch kein Fallback-Modell)
- Blackboard-Cleanup-Bug fixen (tote Agenten korrekt entfernen)
- Mehr Rollen mit gegensätzlichen Zielen für echte Aushandlung
- Experiment-Runner, der Varianten selbst fährt und Tabellen erzeugt
