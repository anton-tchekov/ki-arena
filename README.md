# ki-arena
SoSe2026 KI Praktikum Agent Arena Projekt

## Gruppenteilnehmer

- Daniil Khoma
- Haron Nazari
- Anton Tchekov

## Projektbeschreibung

Im Projekt soll ein Spiel umgesetzt werden, in dem mehrere
gleich große Teams, bestehend aus mehreren KI-Agenten in
einer Arena Ressourcen verwenden müssen. Das Spielfeld ist eine
Top-Down Karte mit einem rechteckigem Grid, auf dem sich
die Agenten bewegen können.

Die Felder auf dem Spielfeld haben verschiedene Eigenschaften,
unter anderem Ressourcenfelder, die Agenten erreichen und
je nach ihrer Rolle verwenden müssen.

Die Agenten haben eine begrenzbare Sicht auf das Spielfeld,
und verschiedene Ziele. Das Ziel ist das in der Simulation
alle Teams in einem bestimmten Maße kooperativ handeln,
und sich eine Balance herausbildet, jedoch jede Gruppe
von Agenten trotzdem ihre eigenen Interessen verfolgt.

### Agenten

Es sollen einfache Regelbasierte Agenten, RL-Agenten und LLM-Agenten
miteinander verglichen werden.

Es gibt aktuell zwei Gruppen von Agenten in der Simulation, einmal die
Holzfäller, die Bäume fällen, und die Früchtesammler, die von den Bäumen
Früchte sammeln. Das Ziel ist, dass idealerweise die Agenten so handeln,
dass die Ressourcen der Spielwelt erhalten bleiben, und gleichermaßen
die Bedürfnisse der Agenten an Holz und Früchten erfüllt sind.

Zudem sollen in einer Weiterentwicklung weitere Agenten hinzugefügt werden,
welche andere Ziele verfolgen, die auch (teilweise) in Konflikt zu den Zielen
der anderen Agenten stehen.
