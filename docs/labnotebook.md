# Lab Notebook

Standard-Konfig (`config.py`): Grid 20x20, 3 Collector + 2 Cutter, Start Holz 50 /
Frucht 100, tree_spawn_rate 0.5, wood_per_tree 5, Verbrauch 0.2/Agent/Zyklus,
Spawn-Schwelle 100 (Holz und Frucht), max_age 250, max_cycles 10000.

> Termin 3 lief noch mit Schwelle 150 / max_age 200 (Tabelle unten). Termin-6-Läufe
> nutzen den aktuellen Stand.

Alle Läufe headless und reproduzierbar über `src/sim/run_headless.py` (Einstellungen:
`src/sim/simulation_parameters.txt`).

## Termin 3 (alte Konfig: Schwelle 150, max_age 200)

Gleiche Konfig, nur anderer Seed:

| Seed | Zyklen | Peak-Pop | Schnitt-Pop | Spawns | Tode (Alter) | Tode (Hunger) | Bäume Ende |
|------|--------|----------|-------------|--------|--------------|---------------|------------|
| 1    | 366    | 11       | 6.0         | 6      | 11           | 0             | 17         |
| 2    | 600    | 11       | 6.0         | 13     | 18           | 0             | 20         |
| 3    | 435    | 11       | 6.0         | 8      | 13           | 0             | 20         |

- Laufdauer schwankt stark (366 bis 600) nur durch den Seed, Schnitt-Pop/Peak bleiben stabil
- niemand verhungert, Engpass ist hier Fortpflanzung, nicht Essen (Frucht pendelt um ~110, kaum über Schwelle 150, also kaum Nachwuchs, Gruppe stirbt gemeinsam an Alter)
- Holz häuft sich an (Ende ~360), Frucht bleibt knapp
- bei tree_spawn_rate 0.1 kippt das Bild: Wald wächst nicht nach, Holzmangel-Tod nach ~105 Zyklen (Details: `experiment.md`)

## Termin 6, Reproduktion mit aktueller Konfig, neue Beobachtungen

Regel-Agenten, je 3 Seeds, sofern nicht anders genannt.

### Boom oder Bust bei tree_spawn_rate = 0.3

`python run_headless.py --agents greedy --seeds 1-6 --set tree_spawn_rate=0.3`

| Seed | 1 | 2 | 3 | 4 | 5 | 6 |
|------|------|------|-----|-----|-----|-----|
| Zyklen | 1153 | 1990 | 250 | 662 | 250 | 401 |

- Ausgang ist bimodal, gleiche Konfig, nur der Seed entscheidet:
  - **Boom**: Holz erreicht früh die Spawn-Schwelle, es gibt Nachwuchs, Kolonie trägt sich 1000 bis 2000 Zyklen (Holz 125, Frucht 1 am Ende)
  - **Bust**: es spawnt nie, alle 5 Gründer sterben gemeinsam bei Zyklus 250 an Alter (Seeds 3, 5). Frucht-Überfluss (372) aber Holz unter Schwelle (55), Fortpflanzung war holz-limitiert
- Saves: `saves/greedy-0.3-boom.bin`, `saves/greedy-0.3-bust.bin`
- Folge: "mehr Wald ist länger" gilt nicht mehr monoton, 0.3 überlebt im Mittel länger als 0.5/0.9 (Tabelle: `experiment.md`)

### Agenten-Vergleich: wer überlebt am längsten?

Alle drei Typen, Standard-Konfig, Seed 1, natürlicher Tod (kein Zyklen-Cap). LLM über
Mistral-API (`magistral-small-latest`).

| Agenten-Typ | Überlebt (Seed 1) | Todesursache | Holz Ende | Frucht Ende | Bäume Ende |
|---|---|---|---|---|---|
| RL (Q-Learning, 300 Ep) | 60 Zyklen | Holzmangel | 0 | 52 | 20 (unberührt) |
| LLM (Mistral) | 172 Zyklen | Fruchtmangel | ~260 | 0 | 12 |
| Regel (Greedy) | 461 Zyklen | Alter | balanciert | balanciert | 20 |

- 3-Seed-Mittel: Greedy 527, RL 60 (LLM war nur ein Einzellauf, zu teuer für mehrere und eh nicht deterministisch)
- Ranking: Regel schlägt LLM schlägt RL
- RL und LLM scheitern an entgegengesetzten Enden derselben Balance:
  - **RL** (`saves/rl-collapse.bin`): Cutter lernen das Fällen nicht, Wald bleibt bei 20 Bäumen stehen, kein Holz kommt rein. Bleibt auch mit korrekt verdrahteter, geshapeter Belohnung (Reward-Caching-Bug gefixt, Effekt gleich) und mehr Training (100 auf 400 Ep). Echte Lerngrenze, kein Reward-Bug.
  - **LLM** (`saves/llm-coordination.bin`): Cutter fällen zu eifrig, Holz häuft sich monoton (49, 65, 95, 127, 199, ~260), Frucht schwindet monoton (99, 77, 50, 26, 8, 0). Verhungert an Frucht trotz Holz-Berg
- Regel-Agenten balancieren sich selbst (nächster unbesetzter Baum), niemand verhungert, Tod erst nach 461 Zyklen an Alter. Das ist die robuste Messlatte

### LLM-Lauf im Detail (Mistral-API, magistral-small-latest)

`MISTRAL_API_KEY=... python run_headless.py --agents llm --llm-backend mistral --seeds 1 --set max_cycles=600 --save --log logfile_llm.txt`

Aus dem 172-Zyklen-Lauf (860 Aufrufe, geloggt in `llm_calls.jsonl` + `logfile_llm.txt`):

- Cutter fällen zuverlässig, sogar zuverlässiger als bei RL, aber zu einseitig (Holz-Berg 260, Frucht auf 0)
- Cutter entfernen ganze Bäume und damit auch die Fruchtquellen, Collectoren kommen nicht hinterher
- Koordination vorhanden, nicht perfekt: Modell argumentiert explizit über Aufteilung ("leaving closer trees for others"), trotzdem zielen mehrfach alle drei Collector auf denselben reichsten Baum (z.B. (6,8) mit 12 Frucht). Die harte Zuteilung der Regel-Agenten (`_pick_uncontested_tree`) fehlt hier
- Antwortformat saß: alle 860 Aufrufe lieferten eine gültige `ACTION:`-Zeile, der Fallback aus `_parse_reply` musste nie einspringen
- Kosten: Latenz 0.4 bis 2.0s (Schnitt 0.6s), Prompt ~1040 Tokens, Antwort ~38 Tokens/Aufruf. Deshalb laufen lange Experimente mit Regel-Agenten, LLM-Läufe schauen wir uns eher als Replay an (`saves/llm-coordination.bin`)

## Nachtrag: Guidance abschalten

Details und Zahlen komplett in `docs/experiment.md`. Kurzfassung fürs Notebook:

- gebaut: `--llm-no-guidance` schaltet die vorberechnete Zielsuche komplett ab
- Ergebnis war ernüchternd, alle 5 Modelle sterben ohne Guidance nach 50-55 Zyklen an Holzmangel, egal wie groß das Modell ist. Sie navigieren einfach nicht zuverlässig genug selbst
