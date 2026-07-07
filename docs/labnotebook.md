# Lab Notebook

Standard-Konfig (`config.py`): Grid 20x20, 3 Collector + 2 Cutter, Start Holz 50 /
Frucht 100, tree_spawn_rate 0.5, wood_per_tree 5, Verbrauch 0.2/Agent/Zyklus,
Spawn-Schwelle 100 (Holz und Frucht), max_age 250, max_cycles 10000.

> Termin 3 lief noch mit Schwelle 150 / max_age 200 (Tabelle unten). Die
> Termin-6-Läufe nutzen den aktuellen Stand.

Alle Läufe headless und reproduzierbar über `src/sim/run_headless.py` (Einstellungen:
`src/sim/simulation_parameters.txt`).

## Termin 3 (alte Konfig: Schwelle 150, max_age 200)

Gleiche Konfig, nur anderer Seed:

| Seed | Zyklen | Peak-Pop | Schnitt-Pop | Spawns | Tode (Alter) | Tode (Hunger) | Bäume Ende |
|------|--------|----------|-------------|--------|--------------|---------------|------------|
| 1    | 366    | 11       | 6.0         | 6      | 11           | 0             | 17         |
| 2    | 600    | 11       | 6.0         | 13     | 18           | 0             | 20         |
| 3    | 435    | 11       | 6.0         | 8      | 13           | 0             | 20         |

Die Laufdauer schwankt stark (366–600) nur durch den Seed, Schnitt-Pop und Peak
bleiben dagegen stabil. Niemand verhungert, der Engpass ist hier die Fortpflanzung,
nicht das Essen: Frucht pendelt um ~110 und kommt selten über die Schwelle 150, also
kaum Nachwuchs, und die Gruppe stirbt gemeinsam an Alter. Holz häuft sich dabei an
(Ende ~360), Frucht bleibt knapp. Bei tree_spawn_rate 0.1 kippt das Bild: der Wald
wächst nicht nach, Holzmangel-Tod nach ~105 Zyklen (Details in `experiment.md`).

## Termin 6 – Reproduktion mit aktueller Konfig und neue Beobachtungen

Regel-Agenten, je 3 Seeds, sofern nicht anders genannt.

### Boom-oder-Bust bei tree_spawn_rate = 0.3

`python run_headless.py --agents greedy --seeds 1-6 --set tree_spawn_rate=0.3`

| Seed | 1    | 2    | 3   | 4   | 5   | 6   |
|------|------|------|-----|-----|-----|-----|
| Zyklen | 1153 | 1990 | 250 | 662 | 250 | 401 |

Der Ausgang ist bimodal: entweder erreicht das Holz früh die Spawn-Schwelle, es kommt
Nachwuchs, und die Kolonie trägt sich 1000–2000 Zyklen (Boom). Oder es spawnt nie
jemand, dann sterben alle 5 Gründer gemeinsam bei Zyklus 250 an Alter (Bust, Seeds 3
und 5). Im Bust liegt am Ende viel Frucht herum (372), aber das Holz bleibt bei 55
unter der Schwelle – Fortpflanzung war hier holz-limitiert trotz Frucht-Überfluss. Im
Boom ist es umgekehrt (Holz 125, Frucht 1). Gespeichert als `saves/greedy-0.3-boom.bin`
und `saves/greedy-0.3-bust.bin` – gleiche Konfig, nur der Seed entscheidet. Folge: der
saubere Zusammenhang "mehr Wald = länger" gilt mit der aktuellen Konfig nicht mehr
monoton, 0.3 überlebt im Mittel länger als 0.5 und 0.9 (Tabelle in `experiment.md`).

### Agenten-Vergleich: wer überlebt am längsten?

Alle drei Typen bei gleicher Standard-Konfig (3 Collector + 2 Cutter), Seed 1, bis zum
natürlichen Tod (kein Zyklen-Cap). LLM über die Mistral-API (`magistral-small-latest`).

| Agenten-Typ             | Überlebt (Seed 1) | Todesursache | Holz Ende | Frucht Ende | Bäume Ende |
|-------------------------|-------------------|--------------|-----------|-------------|------------|
| RL (Q-Learning, 300 Ep) | 60 Zyklen         | Holzmangel   | 0         | 52          | 20 (unberührt) |
| LLM (Mistral)           | 172 Zyklen        | Fruchtmangel | ~260      | 0           | 12         |
| Regel (Greedy)          | 461 Zyklen        | Alter        | balanciert| balanciert  | 20         |

3-Seed-Mittel: Greedy 527, RL 60. Der LLM-Lauf ist ein Einzellauf, teuer und wegen der
API nicht deterministisch. Ranking eindeutig: Regel vor LLM vor RL. Interessant ist,
dass die beiden Lern-Agenten an entgegengesetzten Enden derselben Balance scheitern.

RL stirbt nach 60 Zyklen an Holzmangel: die Cutter lernen das Fällen nicht, der Wald
bleibt bei 20 Bäumen stehen, kein Holz kommt rein. Das gilt auch mit korrekt
verdrahteter, geshapeter Belohnung (wir hatten einen Reward-Caching-Bug gefixt, der
Effekt blieb gleich) und mit mehr Training (100 auf 400 Episoden) – also eine echte
Lern- und Repräsentationsgrenze, kein Reward-Bug. Gespeichert als `saves/rl-collapse.bin`.

Das LLM macht nach 172 Zyklen genau das Gegenteil: die Cutter fällen zu eifrig, das
Holz häuft sich monoton auf (49 → 65 → 95 → 127 → 199 → ~260), während die Frucht
monoton schwindet (99 → 77 → 50 → 26 → 8 → 0). Die Gruppe verhungert an Frucht, mit
einem Holz-Berg von 260 im Lager. Gespeichert als `saves/llm-coordination.bin`.

Regel-Agenten balancieren sich dagegen selbst (jeder nimmt den nächsten unbesetzten
Baum), niemand verhungert, die Gruppe stirbt erst nach 461 Zyklen an Alter – die
robuste Messlatte.

### LLM-Lauf (Mistral-API, magistral-small-latest)

`MISTRAL_API_KEY=… python run_headless.py --agents llm --llm-backend mistral --seeds 1
--set max_cycles=600 --save --log logfile_llm.txt`

Jeder Aufruf (Prompt, Antwort, Latenz, Tokens) landet in `llm_calls.jsonl`, die
angekündigten Pläne übers Blackboard im `logfile_llm.txt`. Aus dem 172-Zyklen-Lauf
(860 Aufrufe): die Cutter fällen zuverlässig, sogar zuverlässiger als bei RL, aber zu
einseitig – Holz-Berg 260, Frucht auf 0. Cutter entfernen ganze Bäume und damit auch
die Fruchtquellen, die Collectoren kommen nicht hinterher. Koordination ist
vorhanden, aber nicht perfekt: das Modell argumentiert explizit über Aufteilung
("leaving closer trees for others", "avoiding overlap with other cutters"), trotzdem
zielen mehrfach alle drei Collector auf denselben reichsten Baum, etwa (6,8) mit 12
Frucht – die harte Zuteilung wie bei `_pick_uncontested_tree` der Regel-Agenten fehlt
dem LLM. Das Antwortformat saß dagegen: alle 860 Aufrufe lieferten eine gültige
`ACTION:`-Zeile, der Fallback aus `_parse_reply` musste nie einspringen. Kosten: Latenz
~0.4–2.0 s (Schnitt 0.6 s), Prompt ~1040 Tokens, Antwort ~38 Tokens je Aufruf – deshalb
laufen die langen Experimente mit Regel-Agenten, LLM-Läufe schauen wir uns als Replay
an (`saves/llm-coordination.bin`).
