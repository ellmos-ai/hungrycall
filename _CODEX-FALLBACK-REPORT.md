# Bericht: Kein stiller Rückfall auf Beispieldaten

Stand: 2026-08-02

## Ergebnis

Im Normalbetrieb gibt die Restaurantsuche keine Beispieldaten mehr zurück. Fehler
führen zu einer leeren Ergebnisfläche mit klarer Begründung. Der Restaurant-Testmodus
ist davon getrennt, ausdrücklich einschaltbar und zunächst ausgeschaltet.

## Unterscheidbare Fehlerfälle

1. **Dienst nicht erreichbar oder Zeitüberschreitung**
   Nominatim oder Overpass war nicht erreichbar, lief in eine Zeitüberschreitung,
   antwortete mit einem Fehlerstatus oder lieferte keine auswertbare Antwort. Die
   Oberfläche nennt den Dienstfehler und zeigt keine Beispieldaten.
2. **Keine Restaurants im gewählten Umkreis**
   Overpass antwortete erfolgreich, lieferte aber keine nutzbaren Restaurants mit
   realer Rufnummer. Die Meldung nennt den gewählten Radius und schlägt ausdrücklich
   vor, den Umkreis zu vergrößern.
3. **Adresse nicht gefunden**
   Nominatim antwortete erfolgreich, konnte PLZ und Ort aber nicht zuordnen. Die
   Oberfläche fordert zum Prüfen der Eingabe auf und zeigt keine Beispieldaten.

## Testmodus und Herkunft

Der Restaurant-Testmodus wird über ein eigenes, standardmäßig nicht ausgewähltes
Kontrollkästchen aktiviert. Er führt keinen Netzwerkzugriff für die Restaurantsuche
aus und darf serverseitig nicht mit echten Anrufen kombiniert werden. Über der
Kandidatenliste steht unübersehbar:

> Testmodus — Beispieldaten, keine echten Restaurants

Im Normalbetrieb steht dort stattdessen **OpenStreetMap via Overpass** als Quelle,
zusammen mit der Zahl der nutzbaren Treffer und dem gewählten Radius. Deutsch und
Englisch verwenden den vorhandenen Übersetzungsmechanismus.

## Gemessene Verifikation

Vollständiger Lauf:

```text
python -X utf8 -m pytest -q -p no:cacheprovider --basetemp C:\_Local_DEV\repos\hungrycall\.tmp-pytest-final-1785689882743
112 passed, 1 warning in 18.54s
```

Der Lauf prüfte den vollständigen gemeinsamen Arbeitsbaum einschließlich der bereits
parallel vorhandenen Branding-Regressionen.

Die Warnung ist die bereits vorhandene Starlette-Abkündigungswarnung für
`TestClient`/`httpx`. Kein Produkttest wurde übersprungen. Das temporäre
Testverzeichnis wurde danach entfernt.

## Harte Grenzen

Es wurde kein echter Restaurantdienst abgefragt, kein echter Anruf ausgelöst, nichts
gepusht und nichts veröffentlicht.

## Lokaler Commit

Der angeforderte lokale Commit konnte wegen des schreibgeschützten Git-Index nicht
angelegt werden. Der exakte erste Staging-Versuch endete mit:

```text
fatal: Unable to create 'C:/_Local_DEV/repos/hungrycall/.git/index.lock': Permission denied
```

Es wurde nichts vorgemerkt, kein Commit erzeugt und kein zweiter Schreibversuch
unternommen. Die fertigen Änderungen liegen ausschließlich im Arbeitsverzeichnis.
