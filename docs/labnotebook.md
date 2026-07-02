# Lab Notebook

Standard-Konfig (`config.py`): Grid 20x20, 3 Collector + 2 Cutter, Start Holz 50 /
Frucht 100, tree_spawn_rate 0.5, wood_per_tree 5, Verbrauch 0.2 pro Agent/Zyklus,
Spawn-Schwelle 150 (Holz und Frucht), max_age 200.

## Termin 3

### Durchläufe

Gleiche Konfig, nur anderer Seed:

| Seed | Zyklen | Peak-Pop | Schnitt-Pop | Spawns | Tode (Alter) | Tode (Hunger) | Bäume Ende |
|------|--------|----------|-------------|--------|--------------|---------------|------------|
| 1    | 366    | 11       | 6.0         | 6      | 11           | 0             | 17         |
| 2    | 600    | 11       | 6.0         | 13     | 18           | 0             | 20         |
| 3    | 435    | 11       | 6.0         | 8      | 13           | 0             | 20         |

### Was uns aufgefallen ist

- Die Laufdauer schwankt stark (366 bis 600), nur durch den Seed. Schnitt-Pop und
  Peak bleiben dagegen stabil.
- Niemand verhungert. Bei Standard-Werten sterben alle an Alter. Der Engpass ist
  also die Fortpflanzung, nicht das Essen.
- Frucht pendelt um ~110 und kommt selten über die Schwelle 150, also kaum Nachwuchs.
  Die Alten werden 200 und sterben fast gleichzeitig, die Gruppe stirbt aus.
- Holz häuft sich an (Ende ~360). Frucht ist knapp, Holz nicht.
- Bei niedriger tree_spawn_rate (0.1) kippt es: Wald wächst nicht nach, Cutter holzen
  ab, Tod durch Holzmangel nach ~105 Zyklen. Mehr dazu in `experiment.md`.
