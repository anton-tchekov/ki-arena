# Observability Design

Welche Tracing- und Logging-Strategie haben wir implementiert, und was konnten wir
damit sehen, was ohne Observability unsichtbar geblieben wäre?

Kein Standard-`logging`, sondern vier eigene, spezialisierte Bausteine — alle
optional, alle kostenlos wenn ungenutzt:

- **Run-Log** (`analysis/run_logger.py` → `logfile.txt`, Klartext, pro Lauf
  überschrieben): Config-Header, SPAWN/DEATH-Events mit Ursache, periodische
  Zustandszeilen, LLM-Blackboard-Plans, Abschluss-Summary.
- **LLM-Call-Log** (`analysis/llm_logger.py` → `llm_calls.jsonl`, ein JSON pro
  Call): Prompt, Response, Latenz, Tokens, Modell — modellunabhängig
  normalisiert über Ollama- und Mistral-Backend.
- **State-History/Replay** (`environment/state_history.py` → `saves/*.bin`,
  gzip-JSON): kompletter Weltzustand pro Zyklus, im GUI rückspulbar per
  Graph-Klick.
- **Debug-Prints** (`agents/rl_agent.py`, `debug=True`): Epsilon, Aktion,
  diskretisierter State, Q-Werte alle 50 Schritte.
- **Koordinations-Metrik** (`analysis/coordination.py`, in `env_grid.py`
  eingebunden): zählt pro Zyklus, wie oft zwei Agenten dieselbe Koordinate auf
  dem Blackboard beanspruchen, als `stats_blackboard_conflicts` — macht
  "LLM-Koordination nicht perfekt" zu einer Zahl statt einem manuellen
  Replay-Eindruck.
- **LLM-Call-Aggregation** (`analysis/llm_call_stats.py`, CLI): rollt
  `llm_calls.jsonl` pro Modell auf — Calls, Retries, Latenz (Mittel/p50/p95),
  Tokens, optional Kosten über `--price MODEL=IN,OUT`.

Zusätzlich loggt der LLM-Call-Log jetzt auch **Retries pro Call** (`retries`-
Feld), und beide Backends setzen ein **explizites Timeout** statt sich auf
SDK-Defaults zu verlassen (`llmmanager_mistral.py` `timeout_ms`,
`llmmanager.py` `timeout`).

Vier weitere gezielte Ergänzungen, nur für Rule-Based- und LLM-Agenten (RL
bleibt hier bewusst außen vor):

- **Run-ID + Zyklus im LLM-Call-Log.** `llm_calls.jsonl` wächst über alle
  jemals gemachten Läufe hinweg (nie rotiert). Jede Zeile bekommt jetzt eine
  `run_id` (einmal pro Prozess erzeugt) und die `cycle`-Nummer — sonst lässt
  sich ein Call im Log keinem bestimmten Lauf/Zyklus zuordnen, außer durch
  Abgleich der Zeitstempel von Hand.
- **Rolle + Guidance-Modus pro Call.** Jede Zeile trägt jetzt `agent_role`
  (cutter/collector) und `guidance` (bool). Die `--llm-no-guidance`-Ablation
  ließ sich vorher nur durch Vergleich zweier separater Log-Dateien von Hand
  auswerten; `llm_call_stats.py` gruppiert jetzt automatisch danach.
- **Automatische Oszillations-Erkennung** (`agents/llm_agent.py
  _check_oscillation`): erkennt, wenn ein Agent seine letzten 4 Positionen
  nur zwischen zwei Feldern verbringt, und druckt sofort eine Warnung. Genau
  das Muster (Modell berechnet "nächster Baum" jede Runde leicht anders,
  läuft ewig hin und her), das vorher nur durch manuelles Lesen der
  Replay-Positionen auffiel.
- **Crash-Sicherung in `run_headless.py`.** Ein 500-Zyklen-LLM-Lauf ist teuer;
  stirbt er bei Zyklus 480 mit einer unbehandelten Exception, war bisher
  außer der verlorenen Terminal-Ausgabe nichts greifbar — jetzt schreibt ein
  Exception-Handler Traceback + Zyklusnummer in eine `crash_*.log`-Datei und
  sichert das Replay bis dahin, genau wie beim bestehenden SIGTERM/SIGINT-Pfad.

## Was dadurch sichtbar wurde

- **Todesursachen statt nur "Population tot".** Aufschlüsselung nach Alter/
  Holzmangel/Fruchtmangel im Run-Log zeigte, dass RL-Cutter reihenweise an
  Holzmangel sterben — erster Hinweis auf einen kaputten RL-Cutter, lange vor
  jeder Reward-Code-Analyse.
- **Kosten/Tempo pro LLM-Modell.** Aus dem JSONL-Log von Hand ausgewertet:
  `reasoning_effort=Medium` kostet ~250s/Call, `Small` ~8s — Grundlage für den
  Ausschluss von Thinking-Modellen bei langen Läufen.
- **Navigations- vs. Entscheidungsfehler getrennt.** Replay + Prompt-Log
  zeigten: Cutter erreichen nur in 3–16 % der Fälle überhaupt einen Baum,
  interagieren aber zu 100 % korrekt sobald sie daneben stehen — ohne das Log
  wäre nur "LLM schlecht" sichtbar gewesen, nicht wo genau.
- **Ein Parsing-Bug.** Reasoning-Antworten kommen als Chunk-Liste statt String
  zurück — fiel durch leere `response`-Felder im JSONL auf, sonst hätte man es
  als Modellversagen fehlgedeutet.
- **Ablation ohne Navigationshilfe** (`--llm-no-guidance`): Logs zeigten
  erfundene Baumkoordinaten und ziellos wechselnde Ziele pro Zug — Beleg für
  fehlendes Gedächtnis, nicht nur "schlechtere" Navigation.
- **Blackboard-Cleanup-Bug** per Replay gefunden: Agenten, die an Alter/Hunger
  sterben, umgehen die normale `is_done`-Aufräumlogik, ihre Plan-Notiz bleibt
  für immer stehen.
- **Reward-Caching-Bug** über Q-Wert-Prints entdeckt: Environment cachte die
  Reward-Funktion bei Konstruktion, ein späteres Umsetzen wurde beim Training
  stillschweigend ignoriert.

Kurz: Ohne diese vier Ebenen hätte man nur ein Endergebnis pro Lauf gesehen
(überlebte Zyklen) — genug um zu wissen *dass* etwas schlecht läuft, aber nicht
*warum*.

## Bewusste Lücken

- ~~Keine automatische Latenz-Aggregation~~ — behoben durch
  `analysis/llm_call_stats.py` (Mittel/p50/p95 pro Modell).
- ~~Kein clientseitiges Timeout auf LLM-Calls~~ — behoben, beide Backends
  setzen jetzt ein explizites Timeout statt sich auf SDK-Defaults zu
  verlassen.
- Keine Kostenberechnung im Code (Tokenzahlen geloggt und jetzt aggregierbar,
  aber Preistabelle muss man selbst über `--price MODEL=IN,OUT` mitgeben —
  keine hartkodierten/geratenen Dollarpreise, die veralten könnten).
- `CsvLogger` als strukturierte Alternative existiert, ist aber nirgends
  verdrahtet.
