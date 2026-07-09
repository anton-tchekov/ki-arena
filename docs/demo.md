# Live-Demo

## Use Case

- Live-Lauf: Collector sammeln Früchte, Cutter fällen Bäume, beide brauchen die Ressourcen
- man sieht live Population/Ressourcen-Entwicklung und Todesursache
- Dauer ca. 3–4 Minuten

Ablauf:

1. `python main.py` starten (Grid links, Control Panel rechts).
2. Welt kurz erklären (Bäume, Agenten, Farben).
3. Pause, dann die Graphen zeigen (Holz/Frucht, Population, Alter).
4. Mit Prev/Next oder Klick in den Graph durch die Historie blättern.
5. Blackboard mit den Plänen zeigen (bei LLM-Lauf).
6. Lauf zu Ende laufen lassen, End-Zusammenfassung in `logfile.txt` zeigen.

## Setup

`pip install -r requirements.txt`. Der Standard-Lauf nutzt Regel-Agenten, also kein
API-Key nötig. Keine externen Daten, die Welt ist zufällig.

## Notfallplan

- GUI macht Probleme: headless laufen lassen und die Zahlen vorlesen –
  `cd src/sim && python run_headless.py --agents greedy --seeds 1` (oder ein
  gespeichertes Replay im GUI abspielen, z. B. `saves/greedy-0.3-boom.bin`).
- LLM/API fällt aus: auf den Regel-Lauf umschalten (Default), der braucht nichts Externes.
- Lauf hängt: kleinere `max_cycles` setzen (`--set max_cycles=200`) oder das
  Backup-Video `sim.gif` zeigen.
- Komplett-Ausfall: Video zeigen und an den Folien durch die Ergebnisse gehen.
