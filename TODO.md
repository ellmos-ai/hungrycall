# TODO.md — HungryCall Backflow & Task Backlog

> **Video-Backflow Strategy (Learnings 2026-08-02)**: Erfundene Details aus dem Videoentwurf wurden im Abgleich gegen die Software evaluiert. Wo das Video die bessere Benutzeroberfläche und Benutzerführung zeigte, wurden die Features nicht aus dem Video gestrichen, sondern direkt in die Software übernommen ("Option 3: Stimmt nicht, ist aber besser -> wird gebaut").

## Completed Video Backflow Features (2026-08-02)

- [x] **Kandidatenradius auf der Karte (Candidate Search Radius Circle)**
  - *Quelle*: Videoentwurf 00:08s
  - *Begründung*: Das Video zeigte einen gestrichelten Umkreis um den Benutzerstandort. Das macht die räumliche Suchgrenze (z. B. 3.0 km) für den Nutzer auf den ersten Blick transparent.
  - *Umsetzung*: `initLeafletMap()` in `hungrycall/templates.py` zeichnet nun dynamisch `L.circle([lat, lon], radius_km * 1000)` auf der Leaflet-Karte.

- [x] **Darstellung der Ablehnungsgründe auf den Restaurant-Karten (Inline Rejection Reason Badges)**
  - *Quelle*: Videoentwurf 00:32s
  - *Begründung*: Im Video wurde bei Ablehnung eines Kandidaten (z. B. Budget überschritten oder unklarer Preis) der genaue Grund direkt an der Karte rot hervorgehoben. Das ist viel transparenter als nur ein rotes X.
  - *Umsetzung*: `#rejection-{id}` Container in `render_restaurant_selection_step()` und SSE DOM-Update in `hungrycall/web.py` mit Badge `🔴 Abgelehnt: <Grund>`.

- [x] **Budget-Band mit Höchstbetrag (Active Financial Authority Cap Band)**
  - *Quelle*: Videoentwurf 00:24s
  - *Begründung*: Ein permanenter visueller Banner im Monitor-Header hebt das finanzielle Mandat (`max_budget_eur`) während der Kaskadenausführung hervor.
  - *Umsetzung*: `render_cascade_monitor()` in `hungrycall/templates.py` rendert nun das `🛡️ FINANCIAL AUTHORITY CAP` Banner mit Betragsanzeige.

- [x] **Transkriptansicht mit Preis-Highlighting (Transcript Price Verification Badge)**
  - *Quelle*: Videoentwurf 00:56s
  - *Begründung*: Die verifizierte Preisaussage des Dienstleisters muss im Gesprächsprotokoll sofort als Beleg herausstechen.
  - *Umsetzung*: `render_result_card()` in `hungrycall/templates.py` bettet das Badge `🏷️ Bestätigter Transkript-Endpreis: XX.XX €` direkt über den Transkript-Zeilen ein.
