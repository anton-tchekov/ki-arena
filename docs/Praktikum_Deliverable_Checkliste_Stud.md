# Deliverable-Checkliste – Praktikum „Agentic AI, Multi-Agenten-Systeme und LLMs"

**Modul:** Agentic AI – Master · HAW Hamburg
**Zweck:** Vollständigkeitskontrolle aller Pflicht-Deliverables über die sechs Termine plus Abschlusspräsentation.
**Verwendung:** Jede Gruppe hakt am Ende eines Termins die erledigten Punkte ab. Der Dozent nutzt dieselbe Liste zur Abnahme.

---

## Vorab auszufüllen

- **Gruppe / Teamname:** HAD
- **Gruppenmitglieder:** Anton Tchekov, Daniil Khoma, Haron Nazari
- **Gewähltes Projekt (A–F bzw. eigener Vorschlag):** Ki-Arena
- **Repository-Link:** https://github.com/anton-tchekov/ki-arena

> Hinweis: Eigene Projektvorschläge müssen an mindestens drei Vorlesungskapitel anschließen und vorab mit dem Dozenten abgestimmt sein.

---

## Termin 1 – Kickoff und Setup

**Ziel:** Gruppe steht, Projekt gewählt, Repository existiert, Tooling bei allen lokal lauffähig.

- [x] Gruppe gebildet (bis zu 5 Personen)
- [x] Projekt aus dem Katalog gewählt **und beim Dozenten gemeldet**
- [x] Gemeinsames Git-Repository angelegt; alle Mitglieder haben Schreibzugriff
- [x] Rollen in der Gruppe verteilt (Repo/CI, Doku, Dozentenkontakt)
- [x] Tooling-Frage geklärt (LLM-Zugriff + Frameworks) und Basis-Pakete installiert

**Pflicht-Deliverable Termin 1**

- [x] `README.md` im Repo enthält: Projektname, Gruppenmitglieder, gewähltes Projekt, einen Absatz „Was wollen wir bauen?"
- [x] Erste **Architekturskizze** im README (als Foto oder Diagramm): Agenten/Komponenten, Kommunikation, benötigte externe Tools/APIs
- [x] „Hello, LLM"-Skript läuft **bei allen Gruppenmitgliedern lokal**

---

## Termin 2 – Architektur und Prototyp

**Ziel:** Aus der Skizze wird ein bewusst entworfenes Design; ein minimaler End-to-End-Prototyp läuft.

- [x] Architektur verfeinert, folgende Fragen **schriftlich** beantwortet:
- [x] Aus welchen Komponenten besteht das System?
  - [x] Welche davon sind „Agenten" (Kap. 01)? Zuordnung zur Russell/Norvig-Taxonomie
  - [x] Wo liegen Memory, Planning, Action im Vier-Schichten-Modell?
  - [x] Wer trifft welche Entscheidungen – und warum dort?
- [x] Minimaler End-to-End-Durchlauf implementiert (Funktion vor Eleganz)
- [x] Erste Stolpersteine festgehalten (unklare Doku, Improvisationen, getroffene Annahmen)

**Pflicht-Deliverable Termin 2**

- [x] Architekturdokument (1–2 Seiten) im Repository
- [x] Lauffähiger Prototyp im Repository **mit Anleitung zum Starten**
- [x] Kurze Liste offener Fragen für die nächste Sitzung

---

## Termin 3 – Kernfunktionalität

**Ziel:** Das System tut, was es tun soll – zumindest im Standardfall.

- [x] Hauptlogik implementiert – projektspezifisch:
- [x] **Projekt B:** Spielmechanik + mind. zwei verschiedene Agenten-Typen, die gegeneinander spielen können
- [x] Mehrere End-to-End-Durchläufe durchgeführt und protokolliert (Varianz beobachtet) → `docs/labnotebook.md`
- [x] Auffälliges/unerwartetes Systemverhalten notiert → `docs/labnotebook.md`

**Pflicht-Deliverable Termin 3**

- [x] Lauffähige Kernfunktionalität im Repository
- [x] Kurzes „Lab Notebook" (Markdown-Datei im Repo) mit den Beobachtungen aus den Durchläufen → `docs/labnotebook.md`

---

## Termin 4 – Erweiterung und Robustheit

**Ziel:** Das System überlebt ungewöhnliche Eingaben; das Innenleben ist nachvollziehbar.

- [x] **Observability** eingebaut: strukturiertes Logging aller LLM-Aufrufe (Prompt, Response, Latenz, Tokens/Kosten) über die Mistral-API → `llm_calls.jsonl` (`analysis/llm_logger.py`)
- [x] Mind. **drei Edge Cases / Failure Modes** identifiziert (z. B. leere/absurde Eingabe, Tool-/API-Ausfall, Endlosschleife, falsches Output-Format) → `docs/edgecases.md`
- [x] Sinnvolle Fehlerbehandlung implementiert (bewusste Entscheidungen: wiederholen / abbrechen / an Nutzer melden)
- [-] **Nur sicherheitsrelevante Projekte (D, A, F):** erste Guardrail-Schicht — nicht relevant für Projekt B (Ki-Arena)

**Pflicht-Deliverable Termin 4**

- [x] Observability-Setup ist aktiv und produziert Logs → `logfile.txt`, CSV-Logger, `llm_calls.jsonl`
- [x] Dokumentierte Edge-Case-Liste mit je: erwartetes Verhalten / tatsächliches Verhalten / gewählter Lösungsansatz → `docs/edgecases.md`
- [-] Erste Version der Guardrails (sofern projekt-relevant) — nicht relevant für Projekt B

---

## Termin 5 – Evaluation und Experiment

**Ziel:** Belegen, *wie gut* das System ist – und unter welchen Bedingungen es versagt.

- [x] Mind. **eine quantitative und eine qualitative Metrik** definiert → `docs/metriken.md`
- [x] **Eine konkrete Hypothese** formuliert, die experimentell überprüft wird → `docs/experiment.md`
- [x] Experiment durchgeführt mit **mind. drei Durchläufen pro Variante**; alle Ergebnisse dokumentiert (auch unerwartete) → `docs/experiment.md`; reproduzierbar über den Headless-Runner `src/sim/run_headless.py`, interessante Einstellungen in `src/sim/simulation_parameters.txt`
- [x] Iteration durchgeführt: bei aufgedeckten Schwächen eine Komponente verbessert und erneut gemessen → `docs/experiment.md` (Cutter-Schonregel + Holz-Ertrag)

**Pflicht-Deliverable Termin 5**

- [x] Definition der Metriken im Repo → `docs/metriken.md`
- [x] Hypothesen-Dokument mit Versuchsaufbau und Ergebnissen (Tabellen, ggf. Plots) → `docs/experiment.md`
- [x] Schriftliche Reflexion: Was wurde gelernt – über das System und über Agentic AI im Allgemeinen? → `docs/reflexion.md`

---

## Termin 6 – Polish und Generalprobe

**Ziel:** Alles für Termin 7 läuft zuverlässig; die Dokumentation ist vollständig.

- [x] Repository aufgeräumt: Abhängigkeiten dokumentiert (`requirements.txt` + `pyproject.toml`), README aktualisiert, `.ipynb_checkpoints` aus dem Tracking entfernt und ignoriert; Headless-Runner `src/sim/run_headless.py` als reproduzierbarer, GUI-freier Einstieg ergänzt
- [x] **Projekt-Dokumentation (4–8 Seiten)** geschrieben → `docs/projektdokumentation.md`:
  - [x] Motivation und Zielsetzung
  - [x] Architekturüberblick (mit Diagramm)
  - [x] Designentscheidungen und ihre Begründung
  - [x] Evaluation und Ergebnisse
  - [x] Limitationen und Failure Modes
  - [x] Was man mit mehr Zeit anders/zusätzlich machen würde
- [x] **Live-Demo** vorbereitet (Use Case, benötigte Daten, Notfallplan bei Fehlschlag) → `docs/demo.md`
- [x] **Präsentationsfolien (10–15 Folien)** erstellt – Struktur: Problem & Motivation / Lösungsansatz & Architektur / Demo / Evaluation & Ergebnisse / Erkenntnisse & Limitationen / Fazit → `docs/slides.md`
- [ ] **Trockenlauf** in der Gruppe durchgeführt (Zeit gestoppt, alle reden mind. einmal) *(Gruppenaufgabe, manuell)*

**Pflicht-Deliverable Termin 6**

- [x] Aufgeräumtes Repository mit vollständiger Doku → `docs/projektdokumentation.md` + `docs/`-Index im README
- [x] Präsentationsfolien im Repo → `docs/slides.md`
- [ ] Backup-Video der Demo (kurzer Bildschirmmitschnitt) für den Notfall *(muss aufgenommen werden; `sim.gif` als Zwischenlösung vorhanden)*

---

## Termin 7 – Abschlusspräsentation

**Format:** 15–20 Min. Vortrag inkl. Live-Demo, danach ca. 10 Min. Diskussion.

- [ ] Vortrag mit Live-Demo nach der in Termin 6 vorbereiteten Struktur gehalten
- [ ] Diskussion bestritten (Fragen zu Designentscheidungen, Trade-offs, Failure Modes)
- [ ] Jedes Gruppenmitglied hat mind. einen inhaltlichen Beitrag geleistet
- [ ] **Übergabe:** finale Dokumentation **und** Repository-Link an den Dozenten

---

## Finale Abgabe-Übersicht (Schnellkontrolle)

Alle nachfolgenden Artefakte sollten am Ende im Repository vorhanden sein:

- [x] `README.md` (Projektinfo, Gruppe, Architekturskizze – aktuell gehalten)
- [x] Architekturdokument (1–2 Seiten) → `docs/aufgabe2.md` + Diagramm
- [x] Lauffähiges System mit Start-Anleitung → README + `requirements.txt`
- [x] Lab Notebook (Beobachtungen aus Durchläufen) → `docs/labnotebook.md`
- [x] Observability-Logs / Logging-Setup → `logfile.txt`, `llm_calls.jsonl` (Mistral-API), CSV-Logger
- [x] Headless-Runner für reproduzierbare Läufe (Regel / RL / LLM) → `src/sim/run_headless.py`
- [x] Interessante Parameter-Einstellungen dokumentiert → `src/sim/simulation_parameters.txt`
- [x] Gespeicherte interessante Läufe (semantisch benannt) mit Erklärung → `src/sim/saves/*.bin` (7 kuratierte Läufe wie `greedy-0.3-boom`, `rl-collapse`, `llm-coordination`; je mit `.txt`)
- [x] Edge-Case-Liste mit Lösungsansätzen → `docs/edgecases.md`
- [-] Guardrails (sofern projekt-relevant: A, D, F) — nicht relevant für Projekt B
- [x] Metriken-Definition → `docs/metriken.md`
- [x] Hypothesen-Dokument mit Versuchsaufbau + Ergebnissen → `docs/experiment.md`
- [x] Schriftliche Reflexion → `docs/reflexion.md`
- [x] Projekt-Dokumentation (4–8 Seiten) → `docs/projektdokumentation.md`
- [x] Präsentationsfolien → `docs/slides.md`
- [ ] Backup-Demo-Video *(muss aufgenommen werden; `sim.gif` als Zwischenlösung)*
- [x] Transparenz-Hinweis zur Nutzung von Coding-Assistenten (wer/was beigetragen hat) → `docs/transparenz.md`

---

