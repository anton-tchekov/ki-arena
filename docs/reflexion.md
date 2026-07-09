# Reflexion

## Über das System

- Der Engpass war ein anderer als gedacht. Wir hatten Hunger erwartet, aber bei
  Standard-Werten sterben die Agenten an Alter, weil zu wenig Nachwuchs kommt.
- Mehr schonen ist nicht automatisch besser. Die Cutter-Schonregel hat bei langsamem
  Wald nichts gebracht, weil der echte Engpass der Holz-Durchsatz war. Erst messen,
  dann am richtigen Hebel drehen.
- Kleine Konfig-Werte haben große Wirkung (tree_spawn_rate 0.1 vs 0.9 = Faktor 6 beim
  Überleben). Deshalb braucht man feste Seeds und mehrere Läufe.

## Über Agentic AI

- Beobachtbarkeit früh einbauen. Ohne die Todesursachen-Zahlen hätten wir nie gemerkt,
  dass es um Alter statt Hunger geht.
- Kleine LLMs muss man führen. Der LLM-Agent navigiert ein ASCII-Grid nicht
  zuverlässig, also rechnen wir die Geometrie vor und geben einen Hinweis plus
  Fallback. Das Modell entscheidet, wir fangen Fehler ab.
- Nie auf gutes Format vertrauen. Antworten werden geparst, bei Müll greift ein
  sicherer Rückfall. Das hat mehr gebracht als ein besserer Prompt.
- Regel-Agenten sind eine gute Messlatte: schnell, mit Seed deterministisch, und kein
  API-Aufruf nötig.
