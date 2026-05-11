## Aus welchen Komponenten besteht Ihr System?

### Arena
Das Zentrum der Architektur. Ist in Phasen unterteilt um beispielsweise zwischen einer Lern- und Spielphase zu unterscheiden

### Analysis
Dient zur Auswertung und Aufzeichnung des Spiels. Kann Beispielsweise Punkte für die Agenten verteilen, je nachdem wie gut sie sich schlagen

### Environment
Ein simples Grid, auf dem sich Bäume mit Früchten befinden. Agenten können sich in 4 Himmelsrichtungen bewegen und Interaktionen auslösen mit Bäumen

### Agents

#### Rule Based
Standard regelbasierter Agent mit von uns gesetzten Regeln

#### RL
Neural Network, welches durch Reinforcement-Learning trainiert wird

#### LLM
Ein General-Purpose LLM. Bekommt Environment Informationen und agiert auf diese mithilfe von vergangener Erfahrung

## Welche davon sind „Agenten” im Sinne von Kapitel 01?
Derzeit sind keine davon Agenten im POMDP sinne, da sie alle full observability haben und nicht partial. Dies kann sich im Laufe des Projektes ändern.

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
- Memory: ist in den Gewichten.
- Planning: Basierend auf was geklappt hat in den Trainingsphasen
- Action: Bewegen und Interagieren

### LLM
- Memory: Behält ein Context window mit Erfahrungen als Memory
- Planning?
- Action: Bewegen und Interagieren

## Wer trifft welche Entscheidungen, und warum dort?

Noch keine Tests durchlaufen, um die Entscheidungen zu beurteilen