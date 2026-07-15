# Ergebnisse

Alle Läufe headless und reproduzierbar (`run_headless.py`, feste Seeds).
Rohdaten und Details stehen in
[detailiertedoku/experiment.md](detailiertedoku/experiment.md) und
[detailiertedoku/labnotebook.md](detailiertedoku/labnotebook.md),
interessante Läufe liegen als Replay in `src/sim/saves/`.

## Überblick: Regel schlägt LLM schlägt RL

Alle drei Typen, Standard-Konfig, Seed 1, natürlicher Tod:

| Agent | Zyklen | Todesursache | Warum |
|---|---|---|---|
| Regel (Greedy) | 461 | Alter | balanciert sich selbst, niemand verhungert |
| LLM (Mistral) | 172 | Fruchtmangel | Cutter fällen zu eifrig, Holz-Berg, Frucht auf 0 |
| RL (Q-Learning, 300 Ep) | 60 | Holzmangel | Cutter lernen das Fällen nicht, Wald bleibt unberührt |

RL und LLM scheitern an entgegengesetzten Enden derselben Holz/Frucht-Balance.
Beim RL ist es eine echte Lerngrenze, kein Reward-Bug. 3-Seed-Mittel: Regel
527, RL 60 (LLM nur Einzellauf, zu teuer für mehrere).

## Was hält die Population am Leben? (tree_spawn_rate)

Regel-Agenten, je 3 Seeds:

| tree_spawn_rate | Zyklen | Todesursache |
|---|---|---|
| 0.1 | 105 | Holzmangel |
| 0.3 | ~784* | Alter (bimodal) |
| 0.5 (Standard) | 527 | Alter |
| 0.9 | 619 | Alter |

- Bei 0.1 kollabiert alles an Holzmangel, ab 0.3 stirbt niemand mehr an Hunger.
- \* 0.3 ist Boom oder Bust: je nach Seed trägt sich die Kolonie 1000 bis 2000
  Zyklen oder die Gründer sterben gemeinsam bei Zyklus 250, gleiche Konfig.
- Fix gegen den 0.1-Kollaps: mehr Holz pro Baum hilft (kein Hungertod mehr),
  Wald schonen bringt nichts. Der echte Engpass war Holz-Durchsatz, nicht
  Baumzahl.

## LLM-Modellvergleich (Mistral, Seed 1, Cap 500)

| Modell | Größe | Zyklen | Todesursache | Kosten |
|---|---|---|---|---|
| ministral-3b-2512 | 3B | 245 | Holzmangel | $0.19 |
| ministral-8b-2512 | 8B | 70 | Holzmangel | $0.08 |
| mistral-small-2603 | 119B MoE | 250 | Alter | $0.29 |
| mistral-medium-3-5 | 128B | 795* | Alter | $2.79 |
| mistral-large-2512 | 675B MoE | 360 | Alter | $0.95 |

\* mit Cap 3000 gemessen, der 500er-Cap hatte die echte Lebensdauer versteckt.

Der Engpass ist Navigation, nicht Entscheidung: Cutter erreichen nur in 3 bis
16% der Züge einen Baum (steigt mit Modellgröße), aber sobald sie daneben
stehen, interagieren sie zu 100% korrekt.

## LLM ohne Guidance

Unsere Guidance rechnet dem Modell die Bewegung praktisch vor. Um zu sehen,
was das Modell selbst kann, haben wir sie mit `--llm-no-guidance` komplett
abgeschaltet (gleiche Konfig und Seed):

| Modell | Zyklen (mit Guidance) | Zyklen (ohne Guidance) |
|---|---|---|
| ministral-3b-2512 | 245 | 50 |
| ministral-8b-2512 | 70 | 50 |
| mistral-small-2603 | 250 | 50 |
| mistral-medium-3-5 | 795 | 55 |
| mistral-large-2512 | 360 | 50 |

Ohne Guidance sterben alle 5 Modelle nach 50 bis 55 Zyklen an Holzmangel,
egal wie groß. Die Modelle erfinden teils Baumkoordinaten und pendeln
zwischen zwei Feldern hin und her, weil sie kein Memory haben. Die
Modellvergleichs-Tabelle oben misst also vor allem, wie gut unsere Guidance
ist, nicht wie gut das Modell navigiert.

## Kernaussagen

- Einfache Regeln sind die robusteste Messlatte, LLM und RL schlagen sie nicht.
- Erst messen, dann am richtigen Hebel drehen: Ohne Todesursachen-Metrik
  hätten wir den Holz-Durchsatz nie als Engpass gefunden.
- Kleine Konfig-Änderungen haben riesige Wirkung, deshalb feste Seeds und
  mehrere Läufe.
- LLMs ohne Führung navigieren ein Grid nicht, mit Führung stimmen sie nur
  noch zu.
