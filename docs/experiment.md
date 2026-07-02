# Experiment: Was hält die Population am Leben?

## Hypothese

Wie schnell der Wald nachwächst (`tree_spawn_rate`) entscheidet über das Überleben.
Wächst er zu langsam, holzen die Cutter ihn ab und die Gruppe stirbt früh. Wächst er
schnell, reicht es zum Fortpflanzen und die Gruppe hält länger durch.

## Aufbau

Standard-Konfig, nur `tree_spawn_rate` variiert: 0.1, 0.3, 0.5, 0.9. Pro Wert 3 Läufe
(Seed 1–3), headless, Regel-Agenten. Tabelle zeigt den Mittelwert.

## Ergebnisse

| tree_spawn_rate | Zyklen | Peak-Pop | Schnitt-Pop | Spawns | Tode Alter | Tode Holz | Bäume Ende |
|-----------------|--------|----------|-------------|--------|------------|-----------|------------|
| 0.1             | 105    | 5.0      | 5.0         | 0      | 0          | 5         | 4.7        |
| 0.3             | 200    | 5.0      | 5.0         | 0      | 5          | 0         | 12.7       |
| 0.5 (Standard)  | 467    | 11.0     | 6.0         | 9      | 14         | 0         | 19.0       |
| 0.9             | 688    | 15.7     | 7.3         | 21     | 26         | 0         | 20.0       |

Hypothese bestätigt: mehr Wald-Nachwuchs = längeres Überleben (105 bis 688 Zyklen).
Bei 0.1 stirbt die Gruppe an Holzmangel, der Wald kommt nicht nach. Ab 0.3 verhungert
niemand mehr, die Agenten sterben an Alter. Ab 0.5 reicht es für neue Agenten.

## Iteration

Schwäche ist der Kollaps bei 0.1. Wir haben zwei Fixes getestet, je bei 0.1, 3 Seeds.

### A: Cutter schonen den Wald

Cutter hören auf zu fällen, wenn nur noch `forest_reserve` Bäume da sind
(`config.CUTTER_FOREST_RESERVE`).

| forest_reserve | Zyklen | Tode Holz |
|----------------|--------|-----------|
| 0 (aus)        | 105    | 5         |
| 2              | 125    | 5         |
| 4              | 110    | 5         |
| 6              | 95     | 5         |

Bringt fast nichts. Das Problem ist nicht die Zahl der Bäume, sondern wie viel Holz
reinkommt. Weniger fällen heißt weniger Holz, also verhungern sie genauso.

### B: Mehr Holz pro Baum

Höheres `wood_per_tree`:

| wood_per_tree | Zyklen | Tode Holz | Tode Alter |
|---------------|--------|-----------|------------|
| 5 (Standard)  | 105    | 5         | 0          |
| 10            | 200    | 0         | 5          |
| 20            | 229    | 0         | 5          |
| 40            | 229    | 0         | 5          |

Das hilft. Schon bei 10 verhungert niemand mehr, die Gruppe wird stattdessen alt.
Über 10 bringt wenig, dann bremsen Alter und Frucht.

Lehre: den echten Engpass beheben (Holz-Durchsatz), nicht den scheinbaren (Bäume).
