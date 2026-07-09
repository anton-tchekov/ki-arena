# Stolpersteine

## Agents

### LLM

- versteht anfangs nicht, was es tun soll, Prompt musste die Aufgabe sehr explizit machen (Rolle, Koordinaten, Nachbarschaft)
- kleine Modelle navigieren ein ASCII-Grid nicht zuverlässig, deshalb wird die Geometrie standardmäßig vorberechnet und das Modell bekommt nur noch einen Hinweis + Fallback-Aktion
- Antwortformat ist nie garantiert, robustes Parsing nötig, sonst bekommt die Umgebung Müll
- als wir aus Neugier die Geometrie-Vorberechnung mal komplett abgeschaltet haben (`--llm-no-guidance`): alle 5 Modelle sterben dann nach 50-55 Zyklen an Holzmangel, egal wie groß. Grund war teils erfundene Baumkoordinaten die es gar nicht gab, teils reines Hin-und-Herlaufen zwischen zwei Feldern weil das Modell sich sein Ziel jede Runde neu ausdenkt und kein Gedächtnis hat

## Mistral-API

- Modell-Codenamen sind uneindeutig: `mistral-medium-2604` und `mistral-medium-3-5`
  sind derselbe API-Alias, aber nur einer davon steht in der offiziellen Doku-Übersicht.
  Im Zweifel `models.list()` fragen statt den Docs zu vertrauen
- Rate-Limits unterscheiden sich massiv pro Modell (0.07 RPS bei `mistral-large-2512`
  bis 12.5 RPS bei `ministral-3b-2512`). Mehrere Modelle parallel laufen lassen
  provoziert 429/Connection-Errors, das steht nicht offensichtlich in der Fehlermeldung
- `reasoning_effort` (Thinking) ist nicht bei jedem Modell frei wählbar, manche
  akzeptieren nur `none`/`high`, kein `low`/`medium`. Die API gibt zum Glück einen
  klaren 400-Fehler mit den erlaubten Werten
- reasoning-Antworten kommen als Liste von Content-Chunks (`ThinkChunk`/`TextChunk`)
  zurück statt als String. Das bricht sowohl JSON-Logging als auch ACTION/PLAN-Parsing,
  wenn man nur `.content` als String erwartet
- Agenten, die durch Alter/Hunger sterben, laufen an der normalen `is_done`-Aufräum-
  Logik vorbei (werden intern während eines fremden Agenten-Zugs entfernt). Ihre
  Blackboard-Notiz bleibt für immer stehen, wenn man sich nur auf den regulären
  Termination-Pfad verlässt
