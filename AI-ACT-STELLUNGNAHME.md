# Ersteinschätzung zum EU AI Act: HungryCall

**Stand:** 2. August 2026
**Gegenstand:** KI-gestützte Anrufe bei Restaurants für Bestellung, Abholung oder Reservierung
**Hinweis:** Diese technische und redaktionelle Ersteinschätzung ist keine Rechtsberatung. Der konkrete Betreiber muss Einsatz, Verträge, Datenquellen und Rechtsordnung vor dem Live-Betrieb rechtlich prüfen lassen.

## Kurzurteil

HungryCall fällt nach seinem dokumentierten Zweck nicht in einen der Hochrisiko-Anwendungsfälle des Anhangs III. Art. 50 Abs. 1 und 5 der Verordnung (EU) 2024/1689 ist trotzdem unmittelbar relevant: Die angerufene natürliche Person muss spätestens bei der ersten Interaktion klar erkennen können, dass sie mit einem KI-System spricht. Diese Pflicht gilt seit dem 2. August 2026.

Der Code beginnt den Aufgabentext mit „automated assistant“. Das ist ein vorhandener Transparenzansatz, belegt aber noch keine Erfüllung: Der Text nennt weder „KI“ noch „AI“, ist nicht als wortwörtlich zu sprechender Satz markiert und wird nach dem Anruf nicht als tatsächlich erste Bot-Äußerung geprüft. Der Art.-50-Nachweis ist deshalb **offen und vor weiteren Live-Anrufen zu schließen**.

Art. 50 beantwortet außerdem nicht, ob die Telefonnummer verarbeitet und der Anruf überhaupt ausgelöst werden durfte. Diese vorgelagerte Frage bleibt nach der DSGVO und gegebenenfalls nach nationalem Telekommunikations-, Wettbewerbs- und Strafrecht separat zu lösen.

## 1. Welche Pflichten greifen?

| Thema | Ersteinschätzung | Begründung |
| --- | --- | --- |
| Art. 50 Abs. 1 und 5 AI Act | **Greift.** | Das System ist für die direkte Sprachinteraktion mit natürlichen Personen bestimmt. Die Information muss klar, unterscheidbar und spätestens bei der ersten Interaktion erfolgen. Auf eine angeblich „offensichtliche“ Computerstimme sollte der Betreiber nicht vertrauen. |
| Art. 4 AI Act | **Greift rollenbezogen.** | Anbieter und Betreiber müssen Maßnahmen zur Förderung der KI-Kompetenz ihrer mit Betrieb und Nutzung befassten Personen treffen; dazu gehören hier Freigabe, Überwachung, Eskalation und Datenschutz des Anrufprozesses. |
| Art. 6 und Anhang III AI Act | **Nach aktuellem Verwendungszweck kein Hochrisiko-System.** | Restaurantbestellungen und Reservierungen gehören nicht zu den in Anhang III aufgeführten Bereichen. HungryCall ist auch kein Sicherheitsbauteil eines in Anhang I geregelten Produkts. |
| Art. 53 / GPAI-Verhaltenskodex | **Nicht als unmittelbare Projektpflicht belegt.** | HungryCall stellt nach der Repository-Evidenz kein eigenes General-Purpose-AI-Modell bereit, sondern bindet einen Anrufdienst ein. Pflichten des Modellanbieters sind nicht mit den Pflichten dieser Anwendung gleichzusetzen. |
| DSGVO | **Greift bei personenbezogenen Daten.** | Telefonnummer, Name, Stimme, Gesprächsinhalt, Rückrufnummer und Transkript können personenbezogene Daten sein. Art. 5 und 6 sowie je nach Erhebung Art. 13 oder 14 sind bereits für Kontaktaufnahme und Gespräch zu prüfen. |

Die Einstufung ist zweckabhängig. Eine spätere Umwidmung zu Personalbewertung, Bildungszugang, Kreditwürdigkeitsprüfung oder einem anderen Anhang-III-Zweck erfordert eine neue Prüfung vor dem Einsatz. Die Hochrisiko-Pflichten für Anhang-III-Systeme gelten nach der Änderung durch Verordnung (EU) 2026/1744 ab dem 2. Dezember 2027; Art. 50 gilt unabhängig davon bereits jetzt.

## 2. Was erfüllt der aktuelle Code – und was nicht?

### Vorhandene Kontrollen

- `hungrycall/engine.py:49-55` baut den kanonischen Aufgabentext und setzt an dessen Anfang: `Hello, I am an automated assistant calling on behalf of ...`.
- Dieser Text wird in allen drei Modi vor den Bestell- oder Reservierungsauftrag gestellt (`hungrycall/engine.py:58-103`).
- Der Live-Adapter sendet genau diesen Aufgabentext, die Zielnummer und `locale: de` an CALL-E (`hungrycall/call_client.py:392-426`).
- Ein echter Anruf verlangt sowohl `--live` als auch `--confirm-live` (`hungrycall/cli.py:24-29, 111-120`). Das schützt vor versehentlichem Auslösen, ersetzt aber keine Rechtsgrundlage und keine Offenlegung gegenüber der angerufenen Person.
- Das Ergebnis enthält ein maskiertes Transkript und Aktivitätsdaten (`hungrycall/call_client.py:447-479`). Damit wäre eine technische Nachweisprüfung möglich.

### Offene Lücke nach Art. 50

Der aktuelle Satz sagt „automated assistant“, nicht ausdrücklich „AI system“ oder „KI-System“. Er steht außerdem außerhalb von Anführungszeichen. Die eigene Messdokumentation in `FINDINGS.md` hält fest, dass nicht zitierter Aufgabentext vom Dienst umformuliert oder erweitert werden kann. Der Rückgabecode prüft weder, ob die Offenlegung gesprochen wurde, noch ob sie die erste Bot-Äußerung war.

Deshalb lautet der Status **teilweise umgesetzt, nicht nachgewiesen konform**. Eine robuste Mindestlösung wäre ein wortwörtlicher, lokalisierter erster Satz, zum Beispiel:

> „Guten Tag, ich bin ein KI-Anrufassistent im Auftrag von [Name].“

Er muss in jedem Live-Pfad vor Bestellung, Preisfrage oder sonstigem Inhalt stehen. Ein Ergebnisnachweis muss die erste Bot-Äußerung prüfen und bei fehlender oder verspäteter Offenlegung den Lauf als nicht konform markieren. Diese Arbeit ist in `AUFGABEN.txt` eingetragen; sie wurde in dieser Stellungnahme nicht vorgetäuscht.

## 3. Die angerufene Person hat vorher nicht eingewilligt

Die Einwilligung des App-Nutzers deckt nicht automatisch die Person ab, die im Restaurant den Hörer abnimmt. Auch eine Zustimmung im laufenden Gespräch kann die bereits erfolgte Beschaffung der Nummer, Übermittlung an CALL-E und Anwahl nicht rückwirkend rechtfertigen.

Vor einem Live-Anruf muss der Verantwortliche deshalb mindestens dokumentieren:

1. **Zweck und Rechtsgrundlage jeder Phase:** Nummernbeschaffung, Auswahl, Anwahl, Gespräch, Transkription, lokale Speicherung und etwaige Anbieteraufbewahrung sind getrennt zu betrachten. Bei einem berechtigten Interesse nach Art. 6 Abs. 1 Buchst. f DSGVO braucht es eine echte Interessenabwägung einschließlich vernünftiger Erwartungen und weniger eingriffsintensiver Mittel; das öffentliche Auffinden einer Geschäftsnummer ist kein Freibrief.
2. **Informationspflicht:** Stammt die Nummer nicht von der angerufenen Person, ist Art. 14 DSGVO zu prüfen; bei der ersten Kommunikation ist regelmäßig zumindest eine verständliche erste Informationsebene erforderlich. Direkt im Gespräch erhobene Antworten fallen zusätzlich unter Art. 13. Neben dem KI-Hinweis gehören Betreiber, Zweck, Nummernquelle, Transkription beziehungsweise Aufzeichnung, Rechte und ein erreichbarer Vollhinweis dazu.
3. **Widerspruch und Sperre:** Ein „Nein“, ein Abbruch oder ein Widerspruch muss sofort respektiert und in einer zweckgebundenen Nicht-anrufen-Liste berücksichtigt werden. Eine wiederholte Kaskade darf dieselbe Person nicht wegen eines bloßen technischen Fehlers erneut belasten.
4. **Werbung gesondert klassifizieren:** Eine echte Bestellung oder Reservierung ist nicht automatisch Telefonwerbung. Falls ein konkreter Einsatz aber Werbung ist, gelten zusätzlich die Einwilligungsmaßstäbe des § 7 UWG; bei einer automatischen Anrufmaschine verlangt § 7 Abs. 2 Nr. 2 UWG vorherige ausdrückliche Einwilligung.
5. **Aufzeichnung klären:** Das Repository belegt den Empfang eines Transkripts, aber nicht, ob und wie der Dienst Audio speichert. Erfolgt eine Tonaufzeichnung, muss ihre Befugnis vorab separat geprüft werden; § 201 StGB schützt das nichtöffentlich gesprochene Wort. „Wir speichern lokal kein Audio“ genügt nicht, wenn ein Dienstleister aufzeichnet.

Die Annahme in `SPEC.md`, veröffentlichte Restaurantnummern seien für Anrufe gedacht, ist ein Produktargument, keine festgestellte Rechtsgrundlage. Beschäftigte des Restaurants behalten Datenschutz- und Persönlichkeitsrechte. Der Betreiber muss den konkreten Ablauf, das Land und den Zweck prüfen.

## 4. Pflichten des Hosters in den Servermodi

Die Rollen „Anbieter“, „Betreiber“ und datenschutzrechtlich „Verantwortlicher“ oder „Auftragsverarbeiter“ folgen aus den tatsächlichen Mitteln, Zwecken, Verträgen und Markenauftritten – nicht aus dem Namen des Servermodus. Wer HungryCall unter eigener Marke anbietet oder in Betrieb nimmt, muss die Rollen nach Art. 3 AI Act und Art. 4 DSGVO schriftlich zuordnen.

| Modus aus `../huckepack/KONZEPT.md` | Was daraus folgt |
| --- | --- |
| `local` | Der Betreiber hält die lokale Datenbank und den Schlüssel. Er braucht Zugriffsschutz, Löschfristen, Rechteprozesse, Protokollierung, Verträge und eine vollständige Datenschutzinformation. Der aktuelle Mehrnutzerbefund ist negativ (`HOST-READINESS.md:3-30`). |
| `huckepack-gift` | Browserpersistenz reduziert die dauerhafte Speicherung beim Host, nicht dessen Beteiligung. Der Host stellt Schlüssel und Ausführung; Anrufdaten laufen durch seinen Prozess. Art.-50-Offenlegung, Rechtsgrundlage, CALL-E-Vertrag, Transfers, Löschkonzept und Rechtekanal bleiben erforderlich. |
| `huckepack-only-host` | Ein Schlüssel des Nutzers ändert nicht automatisch die rechtliche Rolle des Hosters. Daten und Schlüssel passieren den Host während des Anrufs; diese Verarbeitung, Verantwortungsabgrenzung, Sicherheit und Anbieterweitergabe müssen erklärt und abgesichert werden. |
| `pay-membership` | Im Konzept nur Stub. Vor einer Freigabe sind Konten, Mandantentrennung, Abrechnung, Objektberechtigungen, Geheimnisverwaltung, Löschung, Export, Incident-Prozesse und ein vollständiger Compliance-Betrieb erforderlich. Er darf nicht als betriebsbereit dargestellt werden. |

`DATA-FLOW.md:22-33, 37-65` belegt für den aktuellen Stand insbesondere die Übermittlung von Zielnummer und Aufgabe an CALL-E, die fehlende vertragliche Evidenz zu Anbieteraufbewahrung und Transfers sowie die verbleibende Transitverarbeitung in Huckepack-Modi. `PRIVACY-TEMPLATE.md:25-71` enthält dafür bewusst offene Betreiberfelder; das Ausfüllen des Templates ersetzt die Umsetzung nicht.

### Freigabekriterien vor Live-Hosting

- Fester erster KI-Satz in jeder Sprache und jedem Pfad; automatischer Nachweis aus erster Bot-Äußerung.
- Dokumentierte Rollen, Zweck- und Rechtsgrundlagenmatrix einschließlich Nummernquelle und Interessenabwägung.
- Kurzer mündlicher Ersthinweis plus vollständige Art.-13/14-Information über einen barrierearmen Kanal.
- Verifizierte CALL-E-Vertragspartei, Rollen, Unterauftragsverarbeiter, Länder, Aufbewahrung, Löschweg, Art.-28-Regelung und gegebenenfalls Kapitel-V-Mechanismus.
- Getrennte Entscheidung zu Transkription und möglicher Audioaufzeichnung; Datenminimierung, Fristen, Auskunft, Löschung, Widerspruch und Nicht-anrufen-Liste.
- Sicherheits- und Mandantenprüfung passend zum Modus; `pay-membership` bleibt bis zur echten Umsetzung gesperrt.
- Maßnahmen zur KI-Kompetenz nach Art. 4 und dokumentierte Neubewertung bei jeder Zweckänderung.

## 5. Quellen und Evidenzgrenzen

Eigene Um:bruch-Analysen, auf die diese Einschätzung aufbaut, ohne sie zu kopieren:

- `C:\Users\User\OneDrive\.TOPICS\.UMBRUCH\website\src\content\blog\ai-act-transparenzpflichten-ab-august-2026.md` – „Ab 2. August: KI-Inhalte erkennen ist keine Nebensache mehr“.
- `...\ki-reviews\eu-ai-act-transparenz-code-of-practice.md` und die danebenliegende englische Fassung.
- `...\ki-reviews\eu-ai-act-haftungsluecke.md` und die danebenliegende englische Fassung.
- `C:\Users\User\OneDrive\.TOPICS\.UMBRUCH\_editorial\entwuerfe\2026-07-03_eu-ai-act_leitartikel_synthese.md` – redaktioneller Entwurf, nicht als veröffentlichte Quelle behandelt.

Primär- und Behördenquellen: [Verordnung (EU) 2024/1689](https://eur-lex.europa.eu/eli/reg/2024/1689/oj), [Digital Omnibus – Verordnung (EU) 2026/1744](https://eur-lex.europa.eu/eli/reg/2026/1744/oj), [Art. 50 im AI Act Service Desk](https://ai-act-service-desk.ec.europa.eu/de/ai-act/article-50), [Umsetzungszeitplan](https://ai-act-service-desk.ec.europa.eu/en/ai-act/timeline/timeline-implementation-eu-ai-act), [DSGVO](https://eur-lex.europa.eu/eli/reg/2016/679/2016-05-04/eng), [§ 7 UWG](https://www.gesetze-im-internet.de/uwg_2004/__7.html) und [§ 201 StGB](https://www.gesetze-im-internet.de/stgb/__201.html).

Nicht belegt und daher offen sind insbesondere aktuelle CALL-E-Vertragsdaten, tatsächliche Audioaufzeichnung, Anbieteraufbewahrung, Verarbeitungsländer, Unterauftragsverarbeiter und die Rechtsgrundlage eines konkreten Betreibers.
