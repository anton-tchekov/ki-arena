# Experiment: Was hält die Population am Leben?

## Hypothese

- `tree_spawn_rate` entscheidet über das Überleben
- zu langsam, Cutter holzen ab, früher Tod. Schnell genug, Fortpflanzung trägt die Gruppe länger

## Aufbau

- Standard-Konfig (Schwelle 100, max_age 250), nur `tree_spawn_rate` variiert: 0.1, 0.3, 0.5, 0.9
- je 3 Läufe (Seed 1-3), headless, Regel-Agenten, Tabelle = Mittelwert
- reproduzierbar über `src/sim/run_headless.py` (Einstellungen: `src/sim/simulation_parameters.txt`)

```
python run_headless.py --agents greedy --seeds 1-3 --set tree_spawn_rate=0.9
```

## Ergebnisse

| tree_spawn_rate | Zyklen | Peak-Pop | Schnitt-Pop | Spawns | Tode Alter | Tode Holz | Bäume Ende |
|-----------------|--------|----------|-------------|--------|------------|-----------|------------|
| 0.1             | 105    | 5.0      | 5.0         | 0      | 0          | 5.0       | 4.7        |
| 0.3             | 1131*  | 7.0      | 4.8         | 17     | 20.7       | 0         | 16.0       |
| 0.5 (Standard)  | 527    | 11.0     | 6.8         | 9.7    | 14.7       | 0         | 20.0       |
| 0.9             | 619    | 12.3     | 7.7         | 15.0   | 19.0       | 0         | 18.7       |

- Hypothese stimmt teilweise: bei 0.1 sterben alle an Holzmangel, ab 0.3 verhungert niemand mehr (nur Alter). Peak-Pop und Spawns steigen monoton mit der Rate
- Laufdauer selbst ist mit aktueller Konfig nicht monoton, 0.3 überlebt im Mittel länger als 0.5/0.9

\* 0.3 mit Vorsicht lesen, Ausgang ist bimodal. 6 Seeds: 1153, 1990, 250, 662,
250, 401, Mittel ~784, riesige Streuung.
- entweder erreicht Holz früh die Spawn-Schwelle, dann trägt sich die Kolonie 1000-2000 Zyklen (Boom)
- oder es spawnt nie, dann sterben die 5 Gründer gemeinsam bei exakt Zyklus 250 an Alter (Bust). Holz hängt bei 55 unter der Schwelle trotz 372 Frucht, Fortpflanzung ist hier holz-limitiert
- gleiche Konfig, nur der Seed entscheidet: `saves/greedy-0.3-boom.bin` / `saves/greedy-0.3-bust.bin`

## Iteration

Schwäche: Kollaps bei 0.1. Zwei Fixes getestet (je 0.1, 3 Seeds).

### A: Cutter schonen den Wald

Cutter stoppen ab `forest_reserve` Bäumen (`config.CUTTER_FOREST_RESERVE`).

| forest_reserve | Zyklen | Tode Holz |
|----------------|--------|-----------|
| 0 (aus)        | 105    | 5         |
| 2              | 122    | 5         |
| 4              | 110    | 5         |
| 6              | 75     | 5         |

- bringt nichts (bei 6 sogar schlechter). Problem ist Holz-Durchsatz, nicht Baumzahl

### B: Mehr Holz pro Baum

| wood_per_tree | Zyklen | Tode Holz | Tode Alter |
|---------------|--------|-----------|------------|
| 5 (Standard)  | 105    | 5         | 0          |
| 10            | 250    | 0         | 5          |
| 20            | 371    | 0         | 5          |

- hilft: ab 10 kein Hungertod mehr, Gruppe stirbt stattdessen an Alter
- `saves/greedy-0.1-collapse.bin` (Kollaps, wood_per_tree=5) vs. `saves/greedy-0.1-woodfix.bin` (Fix, wood_per_tree=10)
- Lehre: echten Engpass beheben (Holz-Durchsatz), nicht den scheinbaren (Baumzahl)

## Nebenbefund: RL schlägt die Regel nicht

- `python run_headless.py --agents rl --train-episodes 300 --seeds 1` gibt 60 Zyklen (Regel auf gleichem Seed: 461), Tod durch Holzmangel bei vollem Wald (20 Bäume)
- RL-Cutter lernen das Fällen nicht zuverlässig. Details: `docs/labnotebook.md`, gespeichert als `saves/rl-collapse.bin`

## Zusatzexperiment: LLM-Modellvergleich (Mistral API)

Gleiche Standard-Konfig, Seed 1, Cap 500 Zyklen, verschiedene Mistral-Modelle über
`run_headless.py --agents llm --llm-backend mistral --llm-model <name>`:

| Modell             | Größe                      | Zyklen | Todesursache | API-Calls | Kosten  |
|---------------------|-----------------------------|--------|--------------|-----------|---------|
| ministral-3b-2512   | 3B (dense)                  | 245    | Holzmangel   | 1225      | $0.19   |
| ministral-8b-2512   | 8B (dense)                  | 70     | Holzmangel   | 323       | $0.08   |
| mistral-small-2603  | 119B MoE (~6B aktiv/Token)  | 250    | Alter        | 1250      | $0.29   |
| mistral-medium-3-5  | 128B (dense)                | 500*   | Alter        | 1250      | $2.79   |
| mistral-large-2512  | 675B MoE (~41B aktiv/Token) | 360    | Alter        | 1250      | $0.95   |

\* Cap erreicht statt natürlichem Tod (Spawns glichen Holzverbrauch aus), siehe
Nachtrag unten, mit höherem Cap zeigt sich der echte natürliche Tod.

- Saves: `saves/ministral-3b-2512.bin`, `saves/ministral-8b-2512.bin`, `saves/mistral-small-2603.bin`, `saves/mistral-medium-3-5.bin`, `saves/mistral-large-2512.bin`
- `mistral-large-2512` lief trotz 0.07 RPS Rate-Limit sauber durch, der Retry-Failsafe (Exponential-Backoff) griff mehrfach und fing die 429/Connection-Errors ab
- offen: `ministral-14b-2512` (crashte an Mistral-seitigem 503, seither per Retry-Failsafe in `llmmanager_mistral.py` abgesichert, nicht neu gelaufen)
- `reasoning_effort` (Thinking-Modus) getestet, verworfen: ~250s/~13k Tokens pro Call bei Medium, ~8s/~1.4k Tokens bei Small, für 500 Zyklen unpraktikabel teuer/langsam

**Nachtrag: `mistral-medium-3-5` mit Cap 3000** (statt 500, um die echte Lebensdauer
zu sehen), `saves/mistral-medium-3-5-3000cap.bin`:

| Zyklen | Todesursache | Tode (Alter/Holz/Frucht) | Bäume Ende | API-Calls | Kosten |
|---|---|---|---|---|---|
| 795 (natürlicher Tod, Cap nie erreicht) | Alter | 21/0/3 | 15 | 1253 | $3.04 |

- der 500er-Cap hatte die echte Lebensdauer versteckt, mit mehr Raum stirbt die Gruppe bei 795 an Alter, nicht am Cap
- erstmals auch 3 Fruchtmangel-Tode bei diesem Modell (vorher nur Alter), also nicht komplett immun gegen Hungertod, nur seltener als bei 3b/8b

## Wie viel von dem Ergebnis ist eigentlich das Modell, und wie viel ist unser Code?

Beim Bauen vom Prompt ist uns aufgefallen dass wir dem Modell ziemlich viel
vorgeben. `_plan_navigation()` in `llm_agent.py` rechnet den nächstgelegenen
Baum in Python aus, gibt genau die Richtung an ("choose RIGHT") und übernimmt
sogar die Fallback-Aktion falls die Antwort kaputt ist. Das Modell muss dem
eigentlich nur noch zustimmen. Also haben wir eine `--llm-no-guidance` Option
gebaut die das komplett abschaltet, um zu sehen was das Modell wirklich selbst
hinkriegt.

**Ohne jede Guidance** (`--llm-no-guidance`), gleiche Konfig/Cap/Seed:

| Modell             | Zyklen (mit Guidance) | Zyklen (ohne Guidance) | Todesursache (ohne) |
|---------------------|:---:|:---:|---|
| ministral-3b-2512   | 245 | 50  | Holzmangel |
| ministral-8b-2512   | 70  | 50  | Holzmangel |
| mistral-small-2603  | 250 | 50  | Holzmangel |
| mistral-medium-3-5  | 500*/795** | 55 | Holzmangel |
| mistral-large-2512  | 360 | 50  | Holzmangel |

\* Cap bei 500, \*\* natürlicher Tod bei Cap 3000 (Alter, siehe Nachtrag oben).

Alle 5 Modelle sterben nach 50-55 Zyklen an Holzmangel, komplett egal wie groß
das Modell ist. Beim Reinschauen in die Replays (Positionsverlauf +
Blackboard) sieht man auch warum: die Cutter haben teilweise Baumkoordinaten
benutzt die es auf der Karte gar nicht gab, und selbst wenn das Ziel echt war
sind sie zwischen zwei Nachbarfeldern hin und her gelaufen statt sich stetig
anzunähern. Kein Wunder eigentlich, jede Runde wird "nächster Baum" komplett
neu berechnet, das Modell hat kein Gedächtnis was es letzte Runde vorhatte.
Damit ist auch klar dass die Adjazenz-Tabelle weiter unten hauptsächlich
zeigt wie gut unsere Guidance ist, und nicht wie gut das Modell selbst
navigieren kann.

Saves: `saves/ministral-3b-2512-noguidance.bin`, `saves/ministral-8b-2512-noguidance.bin`,
`saves/mistral-small-2603-noguidance.bin`, `saves/mistral-medium-3-5-noguidance.bin`,
`saves/mistral-large-2512-noguidance.bin`


## Blackboard- und Bewegungsanalyse (Standard-Modus mit Guidance)

Aus den Save-Dateien, `blackboard_at()` + Positionsverlauf:

- Engpass ist nicht Baumknappheit (Bäume liegen immer bei ~20) und auch nicht schlechte Koordination (die Claims sind sinnvoll)
- Engpass ist dass Cutter selten Adjazenz zu einem Baum erreichen. Wenn sie das schaffen, interagieren sie aber in 100% der Fälle korrekt:

| Modell              | Cutter-Züge | Adjazenz erreicht | Bei Adjazenz interagiert |
|----------------------|-------------|--------------------|----------------------------|
| ministral-3b-2512    | 860         | 3.0%               | 100%                        |
| ministral-8b-2512    | 550         | 1.8%               | 100%                        |
| mistral-small-2603   | 1507        | 5.9%               | 100%                        |
| mistral-medium-3-5   | 818         | 13.6%              | 100%                        |
| mistral-large-2512   | 512         | 16.2%              | 100%                        |

- Adjazenz-Rate folgt der Modellgröße und erklärt die Todesursache direkt: niedrigste Rate führt zu Holzmangel, höhere Rate zu Alter statt Hunger
- (siehe Abschnitt oben) diese Tabelle ist mit Guidance gemessen, ohne Guidance verschwindet der Größenunterschied komplett
- Bug (offen): Blackboard-Notizen von Agenten die an Alter/Hunger sterben werden nie entfernt, dieser Tod-Pfad läuft an `shared_blackboard.remove()` vorbei (nur reguläre `is_done`-Züge rufen das auf). Bei `mistral-medium-3-5` stand die Notiz eines toten Cutters 250 Zyklen unverändert im Log
