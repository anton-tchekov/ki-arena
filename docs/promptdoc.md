# Prompt-Doku (LLM-Agent)

Aufbau in `agents/llm_agent.py`: `build_prompt()` baut den Prompt, `request_response()`
schickt ihn an die API, `_parse_reply()` liest die Antwort, `finish_turn()` postet den
Plan aufs Blackboard und gibt die Aktion zurück.

## Was der Prompt mitgibt

- **Identität**: Name (`self.name`) + Rolle (Collector/Cutter) + Ziel der Rolle
- **Ort**: eigene Position (x,y), ASCII-Grid der Umgebung (`obs_to_matrix`), Baumliste mit Fruchtstand
- **Geometrie vorberechnet** (nur im Default-Modus, siehe unten): nächster relevanter Baum + Richtungshinweis + ob INTERACT möglich ist
- **Blackboard**: Notizen aller Teammitglieder (in Zugreihenfolge, also aktuell), plus Anleitung, was für Notizen sinnvoll sind (Claim/Warn/Command/Answer/Ask)
- **Antwortformat**: `ACTION:` und `PLAN:`

## Wie geparst wird (`_parse_reply`)

1. `<think>...</think>` (Chain-of-Thought mancher Modelle) wird rausgeschnitten
2. Zeile `ACTION:` -> Aktion; Zeile `PLAN:` -> Blackboard-Text
3. fehlt/ungültig die Aktion -> Fallback-Aktion (im Default-Modus die vorberechnete Geometrie, sonst eine zufällige gültige Aktion)
4. fehlt der Plan -> generischer Text ("Doing X.")

## Zwei Modi (`guidance`)

Wir haben irgendwann angefangen uns zu fragen, ob unsere ganzen Ergebnisse überhaupt
zeigen dass das LLM was kann, oder ob wir ihm einfach nur die Lösung vorsagen. Also
haben wir das konfigurierbar gemacht statt es einfach zu glauben.

**1. `guidance=True` (Standard, in main.py und run_headless.py ohne Extra-Flag)**

Wir rechnen die Geometrie in Python vor (`_plan_navigation`) und geben dem Modell
einen fertigen Hinweis, z.B. "your nearest tree is at (5,10), 2 steps RIGHT, choose
RIGHT". Zusätzlich mechanisch (nicht nur im Prompt-Text erwähnt):

- Bäume, die ein Teammitglied bereits claimt, werden aus der eigenen Zielauswahl
  entfernt (`_claimed_trees`). Der Baum verschwindet nicht aus der Welt, er wird nur
  bei der eigenen Zielwahl übersprungen solange noch ein unbeanspruchter übrig ist.
  Kam dazu weil kleine Modelle trotz Prompt-Bitte ("don't target the same tree")
  weiter auf denselben Baum liefen. Die Prompt-Anweisung allein reichte nicht, jetzt
  wird es mechanisch erzwungen.
- wird der eigene Name in einer fremden Notiz mit Koordinate genannt, wird das als
  direkte Anweisung übernommen (`directed_target`)
- Fallback-Aktion bei kaputter Antwort ist die vorberechnete Aktion, nie zufällig

Das Modell muss hier eigentlich nur noch zustimmen. Die richtige Bewegung steht
praktisch schon in der GUIDANCE-Zeile.

**2. `--llm-no-guidance`**

Alles oben genannte weg. Kein vorberechnetes Ziel, kein Claim-Filter, kein
directed_target, Fallback ist eine zufällige Aktion. Das Modell kriegt nur die
Baumliste und die Karte und muss sich selbst überlegen wo es hin will.

Ergebnis (siehe `experiment.md`): alle 5 getesteten Modelle sterben nach 50-55
Zyklen an Holzmangel, komplett unabhängig von Modellgröße. Praktisch niemand
interagiert überhaupt mit einem Baum. Grund beim Reinschauen in die Replays: die
Modelle haben teils komplett erfundene Baumkoordinaten benutzt die gar nicht auf
der Karte existierten, und selbst wenn sie ein echtes Ziel hatten, sind sie
zwischen zwei benachbarten Feldern hin und her gependelt statt sich stetig
anzunähern (kein Gedächtnis, jede Runde wird "nächster Baum" neu berechnet und
oft anders).

## Beispiel-Prompt (echter Aufruf aus `llm_calls.jsonl`, Standard-Modus mit guidance)

```
Your name is cutter_1. You are a Cutter in a shared grid-world
survival simulation. Other agents may address you by this name on the blackboard.
Two groups live here: Collectors gather fruit from trees, Cutters chop trees for
wood. Every agent depends on BOTH resources, so help your group thrive without
exhausting the forest for everyone else.

The world is a 20x20 grid. A position is (x, y) with x and y from 0 to 19.
Movement rules (x is horizontal, y is vertical):
  UP    -> y - 1      DOWN  -> y + 1
  LEFT  -> x - 1      RIGHT -> x + 1
  INTERACT -> act on a tree that is exactly one step away from you.

Current map (row = y downward, column = x rightward):
. . . . . . . . . . . . X . . . . . . .
. . . . . . . . . . . . . . . . . . . .
. . . . . . . . . . . . . . . . . T . .
. . . . . . . @ . X . . . . . . . . . .
. . . . . . . . . . . . . . . . . . . .
. . . . . . X . . . . . . . . . . . . .
. . . . T . . . . . . . . . . . . . . .
. . . . C . . . . . . . . . . . . . . .
. . . . . . . . . . . . T . . . . . . .
. . . . . . . T . . . . . . . . . . . .
. . . . . . . . . . . . . . . . . . . .
. T . . . . . . . . . . . . . . . . . .
. . . . . . . . . . . . . . . . . T C .
C . C . . . . . . . . . . . . . . . . .
T . T . T . . . . . . . . . . X . . . .
. . . . . . . . . . . . . . . . . . . .
. . . . . . . . . . . . . . . . . . . .
. . . . . . . . . . . . . . . . . . . .
. . . . . . . . . . . . . . . . . . . .
. . . T . . . . . . . . . . . . . . . .
Legend: '.'=empty  'T'=tree  '@'=you  'C'=collector  'X'=cutter

You ('@') are at x=7, y=3.
Trees as (x,y)=fruit: (0,14)=6, (2,14)=2, (1,11)=2, (7,9)=1, (17,12)=1, (3,19)=16, (17,2)=7, (4,14)=8, (4,6)=5, (12,8)=2
Shared stock: wood=104.2, fruit=288.2.

BLACKBOARD (shared notice board — this is your only way to talk to teammates):
Notes are pinned in turn order this cycle, so the notes below are already up to
date — nobody after you has moved yet, but everybody before you has, and their
notes are final for this cycle. Treat earlier notes as having priority: if
another cutter already claimed a tree, back off it.
Use the board to actually coordinate, not just narrate yourself. Kinds of notes
you can write:
  - CLAIM a tree before you reach it: "Claiming (5,10), heading there now" — so
    nobody after you targets the same one.
  - WARN about scarcity: "(3,2) is down to 1 fruit, leave it for now."
  - COMMAND / SUGGEST a specific teammate by name: "cutter_1, someone else should
    go to (8,2) instead" or, addressed to you, "cutter_1: you should go to (2,9),
    it's closer for you." If a note below names YOU (cutter_1), treat it as a
    priority instruction and follow it unless it is clearly wrong (e.g. the tree
    is now empty or already taken).
  - ANSWER a teammate's note if it affects your move (confirm a handoff, flag a
    conflict, redirect away from something they just claimed).
  - ASK for help: "Cutters, we're low on wood, prioritize chopping."
Read every note below, in order, before deciding — earlier notes already shaped
what's still available to you:
  - collector_0: Claiming (0,14) for fruit collection now
  - collector_1: Claiming (4,6) for fruit collection now
  - collector_2: Claiming (2,14) for fruit collection now
  - cutter_0: cutter_1, avoid (9,4) — I'm claiming (7,9) instead

Your job: get next to a tree and INTERACT to chop it down for wood — you need wood to survive. Spread out from other cutters and don't strip the forest faster than it can regrow.
GUIDANCE: A teammate directed you to (9,4); it is 2 step(s) RIGHT and 1 step(s) DOWN from you. You are NOT adjacent yet, so do NOT INTERACT — choose RIGHT to get closer.

First decide your single next action, respecting claims and instructions already
on the board above. Then write your OWN note for the blackboard: a short message
aimed at your teammates (a claim, a warning, a command/suggestion to a named
teammate, an answer, or a request) — not a diary entry about what you're doing
and why.
Respond in EXACTLY this format and nothing else:
ACTION: <one of UP, DOWN, LEFT, RIGHT, INTERACT>
PLAN: <one short message to your teammates>
```

**Antwort:**

```
ACTION: RIGHT
PLAN: cutter_0, heading to (9,4) now
```
