# Evaluation & Metriken

Wie haben wir die Qualität unseres Systems gemessen, was erfassen unsere
Metriken nicht, und welcher Benchmark könnte diese Lücke schließen?

(Die reine Metrik-Liste steht in `docs/metriken.md` — hier geht es um das
Evaluationsdesign dahinter.)

## Wie gemessen wurde

- **`analysis/statistics.py` (`SimulationStats`)**: überlebte Zyklen
  (Hauptmaß), nachhaltige Population (Schnitt über den Lauf, damit
  unterschiedlich lange Läufe vergleichbar sind), Peak-Population,
  Durchschnittsalter, Tode nach Ursache, Endzustand des Waldes.
- **`run_headless.py` `collect_metrics()`**: gleiche Zahlen als Dict für
  Multi-Seed-Vergleiche, inkl. arithmetischem Mittel über Seeds.
- **Manuelle Vergleichstabellen** (`docs/experiment.md`,
  `docs/labnotebook.md`): Regel- vs. RL- vs. LLM-Agent auf gleicher Config,
  5 Mistral-Modelle im Vergleich (Zyklen, Todesursache, API-Calls, Kosten),
  Ablation `--llm-no-guidance` trennt Navigations- von
  Entscheidungsqualität.
- **Reward-Funktionen** (`CompositeRewardFn`) sind Trainingssignal fürs RL,
  keine Ergebnis-Metrik.

Damit ließen sich belastbare Aussagen treffen wie "Regel schlägt LLM schlägt
RL" oder dass Cutter nur in 3–16 % der Fälle einen Baum erreichen, aber zu
100 % korrekt interagieren sobald sie daneben stehen.

## Was die Metriken nicht erfassen

- **LLM-Reasoning-Qualität**: keine automatische Bewertung von Blackboard-
  Plänen, nur manuelles Lesen im Replay.
- **Latenz-Verteilung**: Rohwerte im JSONL-Log, aber kein p50/p95/p99, nur
  handschriftliche Prosa-Bereiche.
- **Kosten**: Tokenzahlen geloggt, Dollarkosten manuell nachgerechnet, keine
  Kostenmetrik im Code.
- **Statistische Signifikanz**: kein Varianz-/Konfidenzintervall irgendwo
  berechnet, nur Mittelwerte. LLM-Vergleiche sind sogar reine Einzelläufe
  ("zu teuer für mehrere, eh nicht deterministisch") — keinerlei
  statistische Absicherung.
- **Robustheit/Generalisierung**: alle Läufe auf derselben Environment-
  Familie, nur einzelne Parameter variiert, kein Held-out-Szenario. System
  ist laut eigener Doku "sehr config-empfindlich", aber wie sehr außerhalb
  der getesteten Sweeps ist unbekannt.
- **Kein Train/Eval-Split**: `EvaluationPhase` existiert im Code, wird aber
  von keinem Entry-Point aufgerufen — Training und "Bewertung" laufen auf
  demselben Ausführungslauf.
- **Volle statt partielle Observability**: kein echtes POMDP, obwohl das
  für die LLM-Koordinationsfrage eigentlich relevanter wäre.

## Welcher Benchmark die Lücke schließen könnte

- **Mehrere Seeds pro LLM-Modell statt Einzelläufen**, mit Varianz/
  Konfidenzintervall — macht LLM-Zahlen erstmals mit Regel-/RL-Zahlen
  vergleichbar. Günstigste und wichtigste Verbesserung.
- **Koordinationsspezifischer Test-Satz**, unabhängig vom Simulationslauf:
  feste kleine Konfliktszenarien (z. B. zwei Collector, ein Baum) mit
  erwarteter korrekter Entscheidung, automatisch gegen die LLM-Antwort
  geprüft — ähnlich zu Melting Pot oder Overcooked-AI, die Multi-Agent-
  Koordination unter Ressourcenknappheit in wiederholbaren Szenarien messen.
- **Held-out-Config-Set**, das nie zum Tunen benutzt wurde, einmalig am Ende
  über alle Agententypen laufen lassen — würde "config-empfindlich"
  quantifizieren statt nur behaupten.
