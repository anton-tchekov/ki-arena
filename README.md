# ki-arena
SoSe2026 KI Praktikum Agent Arena Projekt

## Gruppenteilnehmer

- Daniil Khoma
- Haron Nazari
- Anton Tchekov

## Projektbeschreibung

Im Projekt soll ein Spiel umgesetzt werden, in dem zwei
gleich große Teams, bestehend aus mehreren KI-Agenten in
einer Arena um Ressourcen kämpfen. Das Spielfeld ist eine
Top-Down Karte mit einem rechteckigem Grid, auf dem sich
die Agenten befinden. Zu Beginn starten die Agenten auf
entgegengesetzten Seiten des Spielfelds.

Die Felder auf dem Spielfeld haben verschiedene Eigenschaften,
unter anderem Hindernisse, die nicht passiert werden können,
und Ressourcenfelder, die Agenten auf diesem Feld Punkte
geben.

Die Agenten haben eine begrenzte Sicht auf das Spielfeld,
spezifisch, sie wissen immer, was ihr eigenes Team tut, vom
gegnerischen Team nur innerhalb ihrer Sichtweite.
Die Agenten innerhalb eines Teams können miteinander kommunizieren.
Agenten in Angriffsreichweite können angreifen und den gegnerischen
Agenten Schaden zufügen.

Das Spiel ist zuende, wenn eine odere mehrere Win-Conditions
erfüllt sind, also wenn eine bestimmte Punktzahl erreicht ist
oder das gegnerische Team besiegt ist, oder die Zeit abläuft.

