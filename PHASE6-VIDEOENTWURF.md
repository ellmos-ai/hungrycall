# Phase 6 — Videoentwurf, gemessener Stand

> Stand 2026-08-02, 03:20. Alle Zahlen hier stammen aus eigenen Läufen, nicht aus
> Berichten. Wo etwas nicht gemessen wurde, steht das ausdrücklich.

## Ergebnis

`_calle-videos/hungrycall/renders/hungrycall_2026-08-02_03-07-56.mp4`

| Merkmal | Wert | wie belegt |
|---|---|---|
| Länge | **88,704 s** | `ffprobe` |
| Vorgabe | unter 90 s | Learnings nach dem 138-s-Erstentwurf |
| Bild | h264, 1920×1080 | `ffprobe` |
| Ton | aac, stereo | `ffprobe` |
| Pegel | mean **−20,7 dB**, max **−1,9 dB** | `ffmpeg volumedetect` |
| Referenzpegel | mean ≈ −22 dB, max ≈ −1,6 dB | `music-composer`-Skill |
| Dateigröße | 7,24 MB | Dateisystem |

## Musik — komponiert, nicht beschafft

`score.wav/mp3/mid/notes.json` aus `storyline.json` über den Skill `music-composer`
(Engine: `ai-media-editor/tools/compose_music.py`). Chiptune, c-Moll, **Seed 42** —
derselbe Seed erzeugt wieder dieselbe Datei, der Track ist reproduzierbar.

Länge **88,68 s**, also auf die Vertonung geschnitten statt ungefähr passend.

| Zeit | Emotion | Intensität | Wirkung |
|---|---|---|---|
| 0,0–12,8 | calm | 0,20 | nur Pads, sparsame Glocken |
| 12,8–26,6 | alive | 0,35 | Arpeggio setzt ein |
| 26,6–48,8 | tense | 0,45 | Bass und Lead |
| 48,8–64,6 | driving | 0,60 | Drums |
| 64,6–76,5 | epic | 0,75 | volles Layering |
| 76,5–88,7 | outro | 0,25 | Drums/Bass fallen weg, Glocken verglimmen |

Ereignisse: `damp` bei 42,0 s (Tiefe 0,5, Breite 1,2 s) duckt die Musik unter den
gesprochenen Schlüsselsatz; `climax` 64,6–74,0 s; `outro` ab 76,5 s.

## Sichtprüfung — durchgeführt, nicht behauptet

Kontaktbogen über `ai-media-editor`: `python editor.py frames <video> --every 8
--contact-sheet --label`. Elf Einzelbilder angesehen.

**Erzählbogen:** Hook „Beyond Single-Call Provider Apps" → Anfrage-Setup mit Karte und
Kandidatenradius → Kaskade mit Absagen (rot) und Zuschlag (grün) → Transkript mit
Preis → das verallgemeinerte Muster (MUSTER.md) → Schlusskarte.

Damit sind die drei Lücken des Erstentwurfs geschlossen: Abgrenzung zur Anbieter-App
steht im Titel, die Vollmacht-Pointe (Zeitfenster → Geld) hat eine eigene Einblendung,
die Nachnutzbarkeit einen eigenen Abschnitt.

**Entwurfskennzeichnung geprüft:** „CONCEPT DRAFT — NOT BOUND TO REAL DATA", rot
umrandet oben rechts, im vergrößerten Ausschnitt bei 24,6 s klar lesbar. Umgesetzt als
umgetextetes vorhandenes Badge, nicht als zusätzliche Ebene — deshalb keine Kollision
mit Titel, Untertiteln oder den übrigen Badges.

## Offen und ehrlich benannt

**Vier Kontrastwarnungen, null Fehler** (`npx hyperframes check`). Drei Stellen bei
24,633 s mit 2,55:1, eine bei 83,753 s mit 3,75:1, gefordert wären 4,5:1.

Ein Korrekturversuch am Hinweisband wurde **zurückgenommen**: Die Zahl der Warnungen
blieb unverändert, und die gemeldeten Selektoren zeigten auf andere Elemente als das
geänderte. Die vergrößerte Sichtprüfung zeigt an den gemeldeten Stellen weißen Text auf
dunklem Grund, gut lesbar — der Prüfer misst hier gegen einen halbtransparenten
Elternhintergrund und verfehlt die tatsächliche Schichtung. Auf Verdacht am Design zu
schrauben hätte es verschlechtert, ohne etwas zu beheben.

**Nicht geprüft:** ob die Musik unter der Sprache an jeder Stelle passend liegt — dafür
wäre Hören nötig, nicht Messen. Der Gesamtpegel spricht dafür, ersetzt das Urteil aber
nicht.

## Was der Nutzer entscheidet

Alles bis hier war Entwurfsebene und damit selbst zu entscheiden. Unumkehrbar und
deshalb offen bleiben: Veröffentlichung des Repos, Upload des Videos, Einreichung —
sowie jeder echte Anruf (Guthaben steht bei −0,05 USD).
