# Ergebnisübersicht

Alle Configs und Agenten-Typen an einer Stelle zum schnellen Nachschlagen. Herleitung
und Interpretation stehen in `docs/experiment.md`, `docs/labnotebook.md` und
`src/sim/simulation_parameters.txt` — hier nur die Zahlen und was daraus folgt.

Standard-Konfig, wo nicht anders angegeben: Grid 20x20, 3 Collector + 2 Cutter, Start
Holz 50 / Frucht 100, wood_per_tree 5, Verbrauch 0.2/Agent/Zyklus, Spawn-Schwelle 100,
max_age 250. Alles headless über `src/sim/run_headless.py` reproduzierbar.

## Regel vs. RL vs. LLM

Gleiche Konfig, Seed 1, bis zum natürlichen Tod (kein Zyklen-Cap). LLM läuft über die
Mistral-API (magistral-small-latest).

| Agent            | Zyklen (Seed 1) | Mittel 3 Seeds | Todesursache | Holz Ende  | Frucht Ende | Bäume Ende |
|-------------------|------------------|-----------------|--------------|------------|-------------|------------|
| Regel (Greedy)    | 461              | 527             | Alter        | balanciert | balanciert  | 20         |
| LLM (Mistral)     | 172              | – (Einzellauf)  | Fruchtmangel | ~260       | 0           | 12         |
| RL (Q-Learning)   | 60               | 60              | Holzmangel   | 0          | 52          | 20 (unberührt) |

Regel gewinnt klar. Interessanter ist, dass RL und LLM an entgegengesetzten Enden
derselben Balance kaputtgehen: RL fällt praktisch keine Bäume, der Wald bleibt bei 20
stehen und es kommt kein Holz nach – Holzmangel. Das ändert sich auch nicht mit
korrekt verdrahteter Reward-Funktion (ein Caching-Bug wurde gefunden und gefixt,
Ergebnis blieb gleich) oder mehr Training, ist also eine echte Grenze und kein
Verdrahtungsfehler. Das LLM macht genau das Gegenteil: die Cutter fällen zu viel, Holz
häuft sich bis ~260 an, aber mit den Bäumen verschwinden auch die Fruchtquellen –
Fruchtmangel trotz vollem Holzlager. Koordination übers Blackboard passiert (das
Modell erklärt explizit, wer wohin geht), verhindert aber nicht, dass mehrere
Collector auf denselben Baum zielen. Regel-Agenten balancieren sich von selbst
(nächster freier Baum) und sterben erst an Alter.

Replays: `saves/greedy-baseline.bin`, `saves/rl-collapse.bin`, `saves/llm-coordination.bin`.

## tree_spawn_rate

Regel-Agenten, je 3 Seeds (0.3 mit 6 wegen der Streuung):

| tree_spawn_rate | Zyklen | Peak-Pop | Schnitt-Pop | Spawns | Todesursache      |
|-----------------|--------|----------|-------------|--------|--------------------|
| 0.1             | 105    | 5.0      | 5.0         | 0      | Holzmangel         |
| 0.3*            | ~784   | 7.0      | 4.8         | 17     | Alter (bimodal)    |
| 0.5 (Standard)  | 527    | 11.0     | 6.8         | 9.7    | Alter              |
| 0.9             | 619    | 12.3     | 7.7         | 15.0   | Alter              |

Am Rand ist es eindeutig: bei 0.1 stirbt alles an Holzmangel, ab 0.3 verhungert
niemand mehr. Aber die Laufdauer selbst ist nicht monoton – 0.3 überlebt im Schnitt
länger als 0.5 und 0.9, nur wegen der Streuung unten.

\* Bei 0.3 ist der Ausgang bimodal, reiner Seed-Zufall:

| Seed   | 1    | 2    | 3   | 4   | 5   | 6   |
|--------|------|------|-----|-----|-----|-----|
| Zyklen | 1153 | 1990 | 250 | 662 | 250 | 401 |

Entweder erreicht das Holz früh die Spawn-Schwelle, dann trägt die Kolonie 1000–2000
Zyklen (Boom). Oder es spawnt nie jemand, dann sterben alle 5 Gründer zusammen bei
exakt Zyklus 250 an Alter (Bust) – mit 372 Frucht im Lager, aber Holz bei 55 unter der
Schwelle. Reproduktion war hier holz-limitiert, nicht frucht-limitiert, obwohl Frucht
im Überfluss da war. Replays: `saves/greedy-0.3-boom.bin`, `saves/greedy-0.3-bust.bin`.

## Der 0.1-Kollaps: was hilft

Ausgangslage: bei tree_spawn_rate 0.1 verhungert die Gruppe nach ~105 Zyklen.

Cutter schonen (forest_reserve) bringt nichts:

| forest_reserve | Zyklen | Tode Holz |
|-----------------|--------|-----------|
| 0                | 105    | 5         |
| 2                | 122    | 5         |
| 4                | 110    | 5         |
| 6                | 75     | 5         |

Mehr Holz pro Baum dagegen schon:

| wood_per_tree | Zyklen | Tode Holz | Tode Alter |
|-----------------|--------|-----------|------------|
| 5 (Standard)     | 105    | 5         | 0          |
| 10               | 250    | 0         | 5          |
| 20               | 371    | 0         | 5          |

Der Engpass war der Holz-Durchsatz, nicht die Anzahl Bäume – deswegen half Schonen
nicht, aber mehr Ertrag pro Baum schon. Replays: `saves/greedy-0.1-collapse.bin`,
`saves/greedy-0.1-woodfix.bin`.

## LLM-Lauf im Detail

172 Zyklen, 860 API-Aufrufe. Holz steigt fast die ganze Zeit (49 → 65 → 95 → 127 →
199 → ~260), Frucht fällt parallel dazu (99 → 77 → 50 → 26 → 8 → 0). Alle 860 Antworten
kamen im richtigen `ACTION:`-Format, der Fallback musste nie einspringen. Insgesamt
~954.7k Tokens (922k Prompt, 32.6k Antwort), im Schnitt 1110 Tokens pro Aufruf, Latenz
0.4–2.0 s. Log komplett in `src/sim/llm_calls.jsonl`.

## Gespeicherte Läufe

| Save                       | Agenten | Besonderheit                       | Ergebnis                        |
|------------------------------|---------|--------------------------------------|-----------------------------------|
| `greedy-baseline.bin`        | Regel   | Standard                             | frühes Ende (Kollaps, 107 Z.)    |
| `greedy-0.3-boom.bin`        | Regel   | tree_spawn_rate=0.3, Seed 2          | 1990 Zyklen (Boom)               |
| `greedy-0.3-bust.bin`        | Regel   | tree_spawn_rate=0.3, Seed 3          | 250 Zyklen (Bust)                |
| `greedy-0.1-collapse.bin`    | Regel   | tree_spawn_rate=0.1                  | 110 Zyklen, Holzmangel           |
| `greedy-0.1-woodfix.bin`     | Regel   | tree_spawn_rate=0.1, wood_per_tree=10 | 250 Zyklen, kein Hungertod       |
| `rl-collapse.bin`             | RL      | 300 Trainings-Episoden               | 60 Zyklen, Holzmangel            |
| `llm-coordination.bin`        | LLM     | Mistral, natürlicher Tod             | 172 Zyklen, Fruchtmangel         |

Jede `.bin` hat eine `.txt` daneben mit Reproduktions-Befehl und Begründung, warum der
Lauf interessant ist.

## Kurzfassung

Regel-Agenten sind die robusteste Baseline und sterben erst an Alter. RL und LLM
scheitern strukturell an entgegengesetzten Enden derselben Holz/Frucht-Balance, nicht
an Zufall. tree_spawn_rate ist der wichtigste Hebel, aber ab 0.3 nicht mehr monoton –
ein einzelner Lauf kann täuschen, erst mehrere Seeds zeigen das bimodale Verhalten.
Der scheinbare Engpass war nicht der echte: Bäume schonen half nicht, mehr Ertrag pro
Baum schon. LLM-Koordination über Klartext-Blackboard funktioniert, aber nur teilweise
– ohne harte Zuteilung wie bei den Regel-Agenten bleibt Redundanz.
