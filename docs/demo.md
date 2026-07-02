# Live-Demo

## Use Case

Wir zeigen einen Lauf: Collector sammeln Früchte, Cutter fällen Bäume, beide brauchen
die Ressourcen. Man sieht live, wie sich Population und Ressourcen entwickeln und woran
die Gruppe stirbt. Dauer ca. 3–4 Minuten.

Ablauf:

1. `python main.py` starten (Grid links, Control Panel rechts).
2. Welt kurz erklären (Bäume, Agenten, Farben).
3. Pause, dann die Graphen zeigen (Holz/Frucht, Population, Alter).
4. Mit Prev/Next oder Klick in den Graph durch die Historie blättern.
5. Blackboard mit den Plänen zeigen (bei LLM-Lauf).
6. Lauf zu Ende laufen lassen, End-Zusammenfassung in `logfile.txt` zeigen.

## Setup

`pip install -r requirements.txt`. Der Standard-Lauf nutzt Regel-Agenten, also kein
API-Key und kein Ollama nötig. Keine externen Daten, die Welt ist zufällig.

## Notfallplan

- GUI macht Probleme: headless laufen lassen und die Zahlen aus `logfile.txt` vorlesen.
- LLM/API fällt aus: auf den Regel-Lauf umschalten (Default), der braucht nichts Externes.
- Lauf hängt: kleinere `max_cycles` setzen oder das Backup-Video `sim.gif` zeigen.
- Komplett-Ausfall: Video zeigen und an den Folien durch die Ergebnisse gehen.
