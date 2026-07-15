# Idee

Wir bauen ein Spiel, in dem KI-Agenten in einer Arena gemeinsam von begrenzten
Ressourcen leben müssen. Das Spielfeld ist eine Top-Down-Karte mit einem
rechteckigen Grid, auf dem sich die Agenten bewegen.

Es gibt zwei Rollen und einen gemeinsamen Wald:

- **Cutter** fällen Bäume und bringen Holz ein.
- **Collector** sammeln Früchte von den Bäumen.

Jeder Agent braucht beides zum Überleben. Daraus entsteht der zentrale
Zielkonflikt: Wer zu viel fällt, zerstört die Fruchtquellen für alle. Ideal
wäre, dass die Agenten so handeln, dass der Wald erhalten bleibt und trotzdem
alle satt werden. Bei genug Vorrat gibt es Nachwuchs, bei Mangel oder Alter
sterben Agenten.

Unsere Frage: Ergibt sich aus einfachem Verhalten eine Balance, und wie
schlagen sich dabei drei Agenten-Typen im Vergleich, nämlich regelbasierte
Agenten, RL-Agenten und LLM-Agenten? Wie die Agenten funktionieren steht in
[agenten.md](agenten.md), was wir messen in [metriken.md](metriken.md), was
dabei rauskam in [ergebnisse.md](ergebnisse.md).
