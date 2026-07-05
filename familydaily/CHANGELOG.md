# Changelog

Alle relevanten Änderungen an FamilyDaily werden hier festgehalten.
Format: [Keep a Changelog](https://keepachangelog.com/de/1.0.0/)

---

## [0.17.3] - 2026-07-05

### Fix
- **Seitenleisten-Eintrag fuer Nicht-Admin-User sichtbar**: `panel_admin: false` im Add-on-Manifest gesetzt, damit FamilyDaily auch fuer normale Home-Assistant-Benutzer in der Seitenleiste erscheint

---

## [0.17.2] — 2026-06-15

### Fix
- **Updates wurden nicht zuverlässig übernommen**: `index.html` wird jetzt mit `Cache-Control: no-cache` ausgeliefert, damit der Browser/die iPhone-WebApp nach einem Addon-Update das neue `app.js`/`style.css` (per `?v=`-Versionierung) auch wirklich lädt — statt am gecachten alten Stand zu hängen

---

## [0.17.1] — 2026-06-15

### Fix
- **Mehrtägige Termine in der Kalender-Liste**: Ein mehrtägiger Ganztagstermin (z. B. Urlaub) wurde nur am Starttag angezeigt. Er erscheint jetzt an jedem Tag, den er umspannt — Folgetage dezent gestrichelt dargestellt

---

## [0.17.0] — 2026-06-15

### Neu
- **Mehrtägige Ganztagstermine**: Beim Anlegen/Bearbeiten eines Termins erscheint bei „Ganztägig“ ein zweites Datumsfeld „Bis“ — ideal für Urlaub, Ferien oder mehrtägige Ausflüge. Das Enddatum wird inklusiv eingegeben („von Mo bis Fr“); die Umrechnung auf das HA-interne Format passiert automatisch. Termine mit Uhrzeit bleiben unverändert eintägig

---

## [0.16.0] — 2026-06-15

### Neu
- **Schnellnotiz auf Heute**: Frei beschreibbarer Haftzettel auf der Pinnwand — wird automatisch gespeichert und bleibt beim nächsten Öffnen erhalten
- **Countdown-Magnete**: Ganztägige Kalendertermine der nächsten 30 Tage erscheinen als Pillen unterhalb der Kopfzeile ("8 Tage · Geburtstag Max") — automatisch aus allen aktiven Kalendern
- **Mülltag-Banner**: HA-Entity (`sensor.nachste_abholung` o. ä.) in den Einstellungen hinterlegen; zeigt auf Heute einen Banner wenn heute oder morgen Abholung ist

### Geändert
- Haftnotiz-Bereich auf Heute zweigliedrig: oben [Essen | Einkaufen], darunter vollbreite Schnellnotiz

---

## [0.15.1] — 2026-06-15

### Fix
- PWA-Icon auf dem iPhone Home Screen zeigte ein oranges Platzhalter-Quadrat — korrektes Haus-Logo (192×192 und 512×512) hinterlegt

---

## [0.15.0] — 2026-06-12

### Neu
- **Termine in Personenfarben**: Sind Personen getaggt, färben sich Punkt und Markierung des Termins nach der Person — bei mehreren Personen als geteilter Farbkreis. Ohne Personen bleibt die Kalenderfarbe
- **Wetter in der Begrüßung**: Die Heute-Ansicht zeigt Temperatur und Wetterlage aus der ersten HA-Wetter-Entität (z. B. „Guten Morgen · 18° sonnig")
- **Legende unter dem Wochenstreifen**: Termine / Essen / Aufgaben sind jetzt unterscheidbar — der Essens-Punkt ist als Ring dargestellt

### Geändert
- Begrüßung feiner nach Tageszeit abgestuft („Mahlzeit" um die Mittagszeit statt „Hallo")
- Abschnitt „Heute ansteht" heißt jetzt „Heute steht an"

### Fix
- Termine, die exakt um Mitternacht enden, erzeugen keinen Punkt mehr am Folgetag

---

## [0.14.0] — 2026-06-12

### Neu
- **Zutaten beim Essensplan**: Gerichte können Zutaten haben (eine pro Zeile im Formular); beim erneuten Eintragen desselben Gerichts werden die Zutaten vom letzten Mal übernommen. Ein Tap auf den Korb-Button (Essensplan oder Heute-Haftnotiz) setzt alle Zutaten auf die Einkaufsliste — bereits vorhandene werden nicht doppelt angelegt
- **Personen-Filter im Aufgaben-Tab**: Chips mit den Familienmitgliedern; antippen zeigt nur die Aufgaben der Person
- **Einkaufslisten-Kategorien**: Artikel lassen sich Kategorien zuordnen (Tag am Artikel antippen); die Liste gruppiert dann in Supermarkt-Reihenfolge (Obst & Gemüse → … → Haushalt). Einmal zugeordnet, landen künftige Käufe desselben Artikels automatisch in der richtigen Kategorie
- **Termine auf „Heute“ antippbar**: öffnet direkt das Termin-Formular zum Ansehen/Bearbeiten
- **Schnell-Plus an beiden Heute-Abschnitten**: Termin bzw. Aufgabe direkt von der Heute-Ansicht anlegen

### Geändert
- Mehrtägige Termine zeigen ihre Punkte im Wochenstreifen jetzt an jedem Tag, nicht nur am Starttag

---

## [0.13.0] — 2026-06-12

### Neu
- **Komplettes UI-Redesign „Küchenpinnwand“**: warme Papier-Optik mit Terrakotta-Akzent, Zettel-Karten mit Klebestreifen, Haftnotiz für das Abendessen, Personen als Magnete im Heute-Kopf
- **Dark Mode**: Schalter unter Einstellungen → Darstellung; folgt initial der Systemeinstellung, Wahl wird pro Gerät gespeichert
- **Termin-Punkte im Wochenstreifen**: Tage mit Terminen zeigen jetzt farbige Punkte in der jeweiligen Kalenderfarbe (zusätzlich zu Essens- und Aufgaben-Punkten)
- **Echte Icons statt Emojis**: Tabler-Icons als lokales SVG-Sprite (Navigation, Buttons, Leerzustände)
- **Neue Schriften**: Baloo 2 (Überschriften) + Nunito (Text), lokal gebundled — kein CDN, funktioniert offline

### Geändert
- Heute-Ansicht neu aufgebaut: Datum + Familien-Magnete statt Gradient-Hero, Abschnitte „Heute ansteht“ / „Noch zu tun“, Essen & Einkaufen als Notizzettel
- Termine auf „Heute“ zeigen die Uhrzeit jetzt rechts in der Karte

---

## [0.12.1] — 2026-06-12

### Fix
- **Dockerfile**: `build.yaml` wiederhergestellt; Multi-Arch-Manifest ohne Arch-Prefix existiert nicht — Supervisor benötigt weiterhin `ARG BUILD_FROM` + arch-spezifische Images aus `build.yaml`

---

## [0.12.0] — 2026-06-12

### Neu
- **Listen-Tab in der Navigation**: Die Einkaufslisten sind jetzt direkt über die Navigationsleiste erreichbar (nicht mehr nur über die Heute-Karte)

### Fix
- **Dockerfile**: Pflicht-Labels hinzugefügt (`io.hass.version`, `io.hass.type`, `io.hass.arch`)

---

## [0.11.0] — 2026-06-11

### Neu
- **Kalender-Navigation**: ‹/›-Buttons springen 14 Tage vor/zurück; „Heute"-Button kehrt zur aktuellen Woche zurück
- **Monatspicker**: Klick auf den Datums-Header öffnet einen Kalender-Monats-Grid zum schnellen Springen (inkl. Monatsnavigation ‹/›); aktiver Bereich wird farbig hervorgehoben
- **Person-Tagging bei Terminen**: Termin anlegen/bearbeiten → Familienmitglied(er) auswählen → farbige Emoji-Pips erscheinen in der Terminliste; Daten werden unsichtbar im HA-Beschreibungsfeld gespeichert (`<!--fd-persons:1-->`)

---

## [0.10.0] — 2026-06-11

### Neu
- **Kalender-Auswahl:** Kalender sind von Personen entkoppelt. In den Einstellungen
  erscheinen alle HA-Kalender mit eigenem Farbwähler und An/Aus-Schalter — nur aktive
  Kalender werden in der App angezeigt und für Termin-Erinnerungen genutzt.
  Bestehende Person↔Kalender-Zuordnungen werden automatisch übernommen.
- **Termine bearbeiten:** Termin im Kalender antippen → Titel, Datum, Uhrzeit und
  Ganztags-Option ändern (HA WebSocket `calendar/event/update`).
- **Mehrere Notify-Services:** Benachrichtigungen gehen an beliebig viele Geräte
  (Mehrfachauswahl statt Dropdown) — z. B. beide Handys.
- **Desktop-Layout:** Ab 900 px Breite Seitenleiste statt Bottom-Tabs, Heute-Ansicht
  als zweispaltiges Karten-Raster, breitere Inhalte.

### Geändert
- Frischeres Design: Gradient-Hero auf der Heute-Seite, Farbtupfer im Hintergrund,
  Gradient-Buttons/-Badges, Icons in den Kartenüberschriften
- Personen dienen jetzt nur noch der Aufgaben-Zuweisung (Kalender-Feld entfernt)
- Termin-Erinnerungen ohne Personenbezug („Beginnt um 14:30 (in 30 Min.)")

---

## [0.9.2] — 2026-06-11

### Behoben
- **SUPERVISOR_TOKEN fehlte im Addon:** s6-overlay v3 (HA-Base-Image) entfernt die vom
  Supervisor injizierten Env-Variablen, wenn das `CMD` direkt gestartet wird. Der Start
  läuft jetzt über `run.sh` mit `#!/usr/bin/with-contenv bashio` — damit sind
  HA-Verbindung, Kalender und Benachrichtigungen im Addon-Betrieb funktionsfähig.

---

## [0.9.1] — 2026-06-11

### Neu
- **Benachrichtigungen:** Push-Erinnerungen über HA Companion App via `notify`-Services
  - Backend prüft jede Minute: Aufgaben-Erinnerung zur konfigurierten Uhrzeit, Termin-Vorlaufzeit vor Kalender-Events
  - Konfigurierbar in Einstellungen: Notify-Service (Dropdown aus HA), Erinnerungszeit (HH:MM), Vorlaufzeit (15 / 30 / 60 Min.), An/Aus-Toggle
  - Testbenachrichtigung direkt aus den Einstellungen
  - Deduplizierung: jede Erinnerung wird pro Tag/Event nur einmal gesendet
- **Heute-Tab:** Kompakter Wochenüberblick (Mo–So) mit Meal- und Aufgaben-Dots, heutige Spalte orange hervorgehoben

### Geändert
- Addon-Version 0.9.0 → 0.9.1
- `isoDate()` nutzt lokale Datumsteile statt UTC (behebt Off-by-One in UTC+1/+2)
- UI-Overhaul: neue Design-Tokens, animierter Tab-Indikator, Slide-up-Modals, `.emptyState`-Komponente, Heute-Header mit Greeting + Date-Pill, Card-Tap-Feedback

---

## [0.9.0] — 2026-06-11

### Neu
- **Kalender:** 14-Tage-Listenansicht, Termin anlegen (mit Ganztags-Option), löschen via HA Local Calendar
- **Aufgaben:** Aufgaben mit Person(en), Fälligkeitsdatum, Wiederholung (täglich / wöchentlich / monatlich); wiederkehrende Serien einzeln oder komplett löschbar
- **Essen:** Wochenplan Abendessen, letzte Woche mit einem Tipp übernehmen, Link-Feld für Rezepte
- **Heute:** vollständige Tagesübersicht — Termine, fällige Aufgaben, Abendessen, Einkaufslisten-Badge
- **Einstellungen:** Familienmitglieder anlegen/bearbeiten/löschen, HA-Kalender pro Person zuordnen, HA-Verbindungsstatus
- 5-Tab-Navigation (Heute · Kalender · Aufgaben · Essen · ⚙️); Einkaufen über Heute-Karte erreichbar
- PWA-Manifest verknüpft — App als Lesezeichen auf dem Startbildschirm installierbar
- PNG-Icons 192 × 192 und 512 × 512 für Android-Homescreen und iOS Apple-Touch-Icon
- Lade-Indikator (Spinner, 150 ms Verzögerung) und globaler Fehler-Fallback mit „Erneut versuchen"
- `touch-action: manipulation` auf allen interaktiven Elementen (verhindert 300-ms-Verzögerung auf iOS)
- Responsive Anpassungen: engere Tab-Beschriftungen ≤ 360 px, zentriertes Modal ab 600 px

### Geändert
- Addon-Version 0.2.0 → 0.9.0
- README erweitert: vollständige Funktionsübersicht, Voraussetzungen, Stack-Beschreibung

---

## [0.2.0] — 2026-06 (Commit d9685a1)

### Neu
- **Einkaufen:** mehrere Listen, Artikel mit Autovervollständigung aus Verlauf, abhaken, Erledigte löschen
- Live-Sync zwischen Geräten via WebSocket (Polling-Fallback nach Verbindungsverlust)

---

## [0.1.0] — 2026-06 (Commit 33376ae)

### Neu
- HA-Addon-Skeleton: FastAPI-Backend, SQLite in `/data`, Ingress + direkter Port 8099
- Heute-Platzhalter-UI, Health-Endpunkt `/api/health`
