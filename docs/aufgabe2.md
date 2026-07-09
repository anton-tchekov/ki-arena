## Aus welchen Komponenten besteht Ihr System?

- **Arena** – Zentrum der Architektur, in Phasen unterteilt (z. B. Lern- vs. Spielphase)
- **Analysis** – Auswertung/Aufzeichnung des Spiels, z. B. Punkte je nach Agenten-Performance
- **Environment** – simples Grid mit Bäumen/Früchten; Agenten bewegen sich in 4 Himmelsrichtungen und interagieren mit Bäumen
- **Agents**
  - **Rule Based** – regelbasierter Agent mit fest gesetzten Regeln
  - **RL** – tabellarischer Q-Learning-Agent (`agents/rl_agent.py`), Training über Q-Tabelle (kein neuronales Netz)
  - **LLM** – General-Purpose LLM, bekommt Environment-Infos und agiert damit + vergangener Erfahrung

## Welche davon sind „Agenten” im Sinne von Kapitel 01?
Keiner im POMDP-Sinne – alle haben full statt partial observability. Kann sich im Projektverlauf ändern.

## Zu welchem Punkt der Russell/Norvig-Taxonomie gehören sie?

### Rule Based
Gehört zu Simple Reflex

### RL
Learning. Minimierung des Fehlers, eingeprägt in der Trainingsphase.

### LLM
Learning

## Wo befinden sich Memory, Planning, Action im Vier-Schichten-Modell?

### Rule Based
- Memory: Keins
- Planning: Feste Thresholds und regeln ``if.. else``
- Action: Bewegen und Interagieren

### RL
- Memory: liegt in der Q-Tabelle (Zustand -> Aktionswerte).
- Planning: Basierend auf was geklappt hat in den Trainingsphasen
- Action: Bewegen und Interagieren

### LLM
- Memory: Behält ein Context window mit Erfahrungen als Memory
- Planning?
- Action: Bewegen und Interagieren

## Wer trifft welche Entscheidungen, und warum dort?

Noch keine Tests durchlaufen, um die Entscheidungen zu beurteilen