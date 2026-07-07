---
marp: true
paginate: true
---

# Ki-Arena

Multi-Agenten-Simulation um geteilte Ressourcen

Gruppe HAD · Anton Tchekov, Daniil Khoma, Haron Nazari · HAW Hamburg

---

## Problem & Motivation

- Eine Grid-Welt, ein Wald, zwei Rollen:
  - **Collector** sammeln Früchte
  - **Cutter** fällen Bäume für Holz
- Jeder Agent braucht **beides** zum Überleben.
- Spannung: eigene Ziele vs. gemeinsamer Wald.
- Frage: Bildet sich eine **Balance** – oder kippt das System?

---

## Ziel

- Lauffähige Multi-Agenten-Simulation mit klaren Regeln
- Drei vergleichbare Agenten-Typen: Regel, RL, LLM
- Werkzeuge, um zu sehen **warum** ein Lauf so ausgeht
  (Logs, Metriken, Graphen)

---

## Lösungsansatz & Architektur

![h:380](diagrams/Architekturdiagramm.png)

---

## Architektur – Bausteine

- **environment/** – Welt, Ressourcen, Regeln, Visualisierung
- **agents/** – Regel-, RL-, LLM-Agent + Blackboard
- **arena/** – Episoden-Ablauf (Training / Ausführung)
- **analysis/** – Statistik, Logfile, LLM-Log
- **llm/** – Mistral-API-Anbindung
- Alles über **PettingZoo (AEC)**, Stellschrauben in **config.py**

---

## Wichtige Designentscheidungen

- Geometrie fürs LLM vorberechnen (kleine Modelle navigieren ein Grid nicht gut)
- Robustes Parsing, bei Müll eine sichere Fallback-Aktion
- Blackboard als Klartext, Agenten kündigen Pläne in einem Satz an
- Ein Fenster: Grid + Control Panel (Wayland-Fix)
- Regel-Agent als schnelle Messlatte

---

## Demo

- `python main.py` → Grid links, Control Panel rechts
- Pause, Graphen (Holz/Frucht, Population, Alter)
- Durch die Historie blättern
- Blackboard mit Plänen
- End-Zusammenfassung in `logfile.txt`

---

## Evaluation – Aufbau

- **Hypothese:** Wald-Nachwuchs (`tree_spawn_rate`) entscheidet über Überleben
- 4 Werte (0.1 / 0.3 / 0.5 / 0.9), je 3 Seeds
- Headless, Regel-Agenten, Mittelwert
- Metriken: Zyklen, Schnitt-Population, Todesursache

---

## Evaluation – Ergebnis

| tree_spawn_rate | Zyklen | Schnitt-Pop | Todesursache    |
|-----------------|--------|-------------|-----------------|
| 0.1             | 105    | 5.0         | Holzmangel      |
| 0.3             | ~784*  | 4.7         | Alter (bimodal) |
| 0.5             | 527    | 6.8         | Alter           |
| 0.9             | 619    | 7.7         | Alter           |

→ Ränder klar: 0.1 kollabiert, ab 0.3 Tod durch Alter.
\*0.3 = Boom-oder-Bust (250 bis 1990 Zyklen, nur der Seed entscheidet).

---

## Iteration

- Schwäche: Kollaps bei langsamem Wald (0.1), Tod durch Holzmangel
- **Versuch A:** Cutter schonen den Wald → bringt nichts
  - Engpass ist der **Holz-Durchsatz**, nicht die Zahl der Bäume
- **Versuch B:** mehr Holz pro Baum (5 → 10) → hilft
  - niemand verhungert mehr, Gruppe wird alt
- Lernpunkt: den **echten** Engpass beheben

---

## Erkenntnisse & Limitationen

- Überraschung 1: bei Standard-Werten stirbt die Gruppe an **Alter**, nicht Hunger
- Überraschung 2: bei 0.3 **Boom-oder-Bust** – gleiche Konfig, gegensätzliches
  Schicksal, nur der Seed entscheidet (Reproduktion mal holz-, mal frucht-limitiert)
- **RL** schlägt die simple Regel nicht (60 vs. 461 Zyklen)
- Beobachtbarkeit früh einbauen – ohne Logs hätten wir das nie gesehen
- Limits: volle Sicht (kein POMDP), kein API-Fallback, sehr config-empfindlich
- Edge Cases dokumentiert und abgefangen

---

## Fazit

- Einfache Regeln, klare Umgebung, messbare Ergebnisse
- Balance hängt am Wald-Nachwuchs und am Ressourcen-Durchsatz
- Nächste Schritte: Teilwissen, LLM vs. RL vs. Regel direkt vergleichen,
  robustere API-Anbindung

**Danke – Fragen?**
