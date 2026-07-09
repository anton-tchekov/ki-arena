# Edge Cases

Sonderfälle, die wir geprüft haben. Je: was erwartet, was passiert, wie gelöst.

Kein Baum erreichbar / leerer Wald: erwartet war, dass der Agent hängt oder crasht.
Tatsächlich gibt `act()` eine Zufallsbewegung zurück, der Agent wandert einfach weiter.
Gelöst durch Random-Fallback in den Regel-Agenten und einen Wander-Hinweis im LLM-Agent.

LLM antwortet im falschen Format: erwartet war, dass die Umgebung Müll bekommt.
Tatsächlich entfernt `_parse_reply` die Gedankengänge, liest die `ACTION:`-Zeile, und
wenn die fehlt, greift die vorberechnete Aktion zum nächsten Baum. Die Umgebung
bekommt so nie eine ungültige Aktion.

Population stirbt komplett aus: erwartet war eine Endlosschleife im `agent_selector`.
Tatsächlich werden alle terminated, der Selector wird leer, der Lauf endet sauber.
Die Zusammenfassung wird trotzdem geschrieben (`finally` in `main.py`), gelöst über
den Sonderfall `len(agents) == 0`.

Ressourcen würden negativ: erwartet waren negative Holz-/Fruchtwerte. Tatsächlich
bleiben sie bei 0, per `max(0, ...)` im Verbrauch und beim Abzug der Spawn-Kosten.

**Offen:** Fehlt der Mistral-API-Key, schlägt der LLM-Aufruf ohne Fallback fehl.
Für Regel-Läufe egal.
