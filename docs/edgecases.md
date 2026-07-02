# Edge Cases

Sonderfälle, die wir geprüft haben. Je: was erwartet, was passiert, wie gelöst.

**1. Kein Baum erreichbar / leerer Wald.**
Erwartet: Agent hängt oder crasht. Tatsächlich: `act()` gibt eine Zufallsbewegung
zurück, der Agent wandert. Gelöst durch Random-Fallback in den Regel-Agenten und
einen Wander-Hinweis im LLM-Agent.

**2. LLM antwortet im falschen Format.**
Erwartet: Umgebung bekommt Müll. Tatsächlich: `_parse_reply` entfernt Gedankengänge,
liest die `ACTION:`-Zeile, und wenn die fehlt, greift die vorberechnete Aktion zum
nächsten Baum. Die Umgebung bekommt nie eine ungültige Aktion.

**3. Population stirbt komplett aus.**
Erwartet: Endlosschleife im `agent_selector`. Tatsächlich: alle werden terminated,
der Selector wird leer, der Lauf endet sauber. Die Zusammenfassung wird trotzdem
geschrieben (`finally` in `main.py`). Gelöst über den Sonderfall `len(agents) == 0`.

**4. Ressourcen würden negativ.**
Erwartet: negatives Holz/Frucht. Tatsächlich: Werte bleiben bei 0, per `max(0, ...)`
im Verbrauch und beim Abzug der Spawn-Kosten.

**Offen:** Fehlt der API-Key oder läuft Ollama nicht, schlägt der LLM-Aufruf ohne
Fallback fehl. Für Regel-Läufe egal.
