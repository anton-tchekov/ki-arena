# Experiment: Was hält die Population am Leben?

## Hypothese

- `tree_spawn_rate` entscheidet über das Überleben
- zu langsam → Cutter holzen ab → früher Tod; schnell genug → Fortpflanzung trägt die Gruppe länger

## Aufbau

- Standard-Konfig (Schwelle 100, max_age 250), nur `tree_spawn_rate` variiert: 0.1, 0.3, 0.5, 0.9
- je 3 Läufe (Seed 1–3), headless, Regel-Agenten, Tabelle = Mittelwert
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

- Hypothese hält **teilweise**: bei 0.1 Holzmangel-Tod, ab 0.3 verhungert niemand mehr (nur Alter); Peak-Pop/Spawns steigen monoton mit der Rate
- Laufdauer selbst ist mit aktueller Konfig **nicht mehr monoton** – 0.3 überlebt im Mittel länger als 0.5/0.9

\* **0.3 mit Vorsicht lesen** – Ausgang ist **bimodal**. 6 Seeds: 1153, 1990, 250, 662,
250, 401 → Mittel ~784, riesige Streuung.
- entweder erreicht Holz früh die Spawn-Schwelle → Kolonie trägt sich 1000–2000 Zyklen (Boom)
- oder es spawnt nie → 5 Gründer sterben gemeinsam bei exakt Zyklus 250 an Alter (Bust); Holz hängt bei 55 unter der Schwelle trotz 372 Frucht → Fortpflanzung holz-limitiert
- gleiche Konfig, nur Seed entscheidet: `saves/greedy-0.3-boom.bin` / `saves/greedy-0.3-bust.bin`

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

- bringt nichts (bei 6 sogar schlechter) – Problem ist Holz-Durchsatz, nicht Baumzahl

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

- `python run_headless.py --agents rl --train-episodes 300 --seeds 1` → 60 Zyklen (Regel auf gleichem Seed: 461), Tod durch Holzmangel bei vollem Wald (20 Bäume)
- RL-Cutter lernen das Fällen nicht zuverlässig. Details: `docs/labnotebook.md`, gespeichert als `saves/rl-collapse.bin`
