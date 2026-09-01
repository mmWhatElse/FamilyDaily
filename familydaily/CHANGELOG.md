# Changelog

Alle relevanten Änderungen an FamilyDaily werden hier festgehalten.
Format: [Keep a Changelog](https://keepachangelog.com/de/1.0.0/)

---

## [0.23.0] - 2026-09-01

### Neu
- Familienmitglieder lassen sich mit einem oder mehreren Home-Assistant-Notify-Geräten verbinden. Aufgaben und Termine mit mehreren Personen erreichen die Geräte aller markierten Personen, ohne doppelte Push-Nachrichten an gemeinsam genutzte Geräte.
- Standardgeräte bleiben für Aufgaben und Termine ohne Personenzuordnung verfügbar.

### Tests
- Backendtests decken Gerätezuordnung, Mehrpersonen-Aufgaben, Mehrpersonen-Termine und den Standardversand ohne Person ab.

---

## [0.22.0] - 2026-07-20

### Neu
- Rezepte können als Favoriten markiert und gezielt gefiltert werden; zusätzlich zeigt die Rezeptbox, wann ein Gericht zuletzt im Wochenplan stand.
- Sechs alltagstaugliche Tags wie „Schnell“, „Familientauglich“, „Meal Prep“ und „Vegetarisch“ erleichtern das Stöbern. Die 24 Startrezepte sind bereits passend einsortiert.
- „Idee“ schlägt auf Basis der aktiven Kategorie, Suche und Filter ein Rezept vor und bevorzugt Gerichte, die nicht in den letzten sieben Tagen gekocht wurden.
- Beim Übertragen auf die Einkaufsliste lassen sich vorhandene Zutaten vorher abwählen. Das funktioniert sowohl am Rezept als auch direkt im Wochenplan.
- Der neue Wocheneinkauf sammelt mit einem Tap die Zutaten aller geplanten Mahlzeiten und lässt sie vor dem Übertragen gemeinsam prüfen.
- Bestehende Rezepte können als vorausgefüllte Variante gespeichert und mit einer persönlichen Notiz ergänzt werden.

### Geändert
- Suche, Kategorien, Tags und Favoriten lassen sich miteinander kombinieren; der Suchbegriff bleibt auch nach einer Favoriten-Aktion erhalten.
- Favoriten und Tags werden bei bestehenden Installationen automatisch und ohne Datenverlust ergänzt.

### Tests
- Backendtests decken Tags, Favoriten und die aus dem Wochenplan abgeleitete Kochhistorie ab.
- Rezeptbox, Varianten, Zutatenauswahl und Wocheneinkauf wurden zusätzlich in der mobilen Oberfläche geprüft.

---

## [0.21.1] - 2026-07-20

### Neu
- Rezepte lassen sich jetzt direkt aus der Rezeptansicht löschen; eine Sicherheitsabfrage verhindert versehentliches Entfernen.

### Geändert
- Bereits eingeplante Mahlzeiten bleiben als Momentaufnahme mit Titel, Zutaten und Kalorien erhalten, wenn das zugrunde liegende Rezept gelöscht wird.

### Tests
- Ein neuer Regressionstest deckt das Löschen eines Rezepts samt Erhalt bestehender Wochenplaneinträge ab.

---

## [0.21.0] - 2026-07-15

### Neu
- **Rezeptbox unter Essen**: 24 alltagstaugliche Startrezepte aus dem 1.800-kcal-Rezeptbaukasten, gegliedert in Frühstück, Hauptgerichte und Snacks, mit Zutatenmengen, Kalorien und Proteinwerten. Hauptgerichte lassen sich beim Einplanen flexibel Mittag oder Abend zuordnen.
- Rezepte lassen sich durchsuchen, neu anlegen, bearbeiten und löschen sowie direkt für einen Wochentag einplanen.
- Alle Zutaten eines Rezepts landen mit einem Tap gesammelt auf der ersten Einkaufsliste; bereits offene identische Artikel werden nicht doppelt angelegt.
- Der Wochenplan unterstützt jetzt pro Tag je einen Eintrag für Frühstück, Mittag, Abendessen und Snacks.

### Technik
- Bestehende Essenspläne werden automatisch und verlustfrei als Abendessen migriert.
- Geplante Rezepte speichern eine Momentaufnahme ihrer Zutaten und Kalorien, damit spätere Rezeptänderungen bestehende Wochenpläne nicht unbeabsichtigt verändern.
- Sechs neue Tests decken Startdaten, Rezeptpflege, vier Tageskategorien, beide Migrationen und den Sammeltransfer zur Einkaufsliste ab.

---

## [0.20.1] - 2026-07-11

### Neu
- **Optionales Enddatum für Aufgabenserien**: Tägliche, wöchentliche und monatliche Aufgaben können beim Anlegen ein inklusives Enddatum erhalten. Damit lässt sich beispielsweise eine tägliche Aufgabe genau für einen Monat planen.
- Das Enddatum kann in „Wiederholungen verwalten“ nachträglich geändert oder entfernt werden. Die Übersicht zeigt „bis …“ und nach Ablauf „beendet“.

### Technik
- Eine automatische Datenbankmigration ergänzt `end_date`; bestehende Serien bleiben unbegrenzt.
- Materialisierung und Morgen-Vorschau erzeugen nach dem Enddatum keine Aufgaben mehr.
- Acht Backend- und Migrationstests decken den inklusiven letzten Tag, den Folgetag und das Entfernen des Enddatums ab.

---

## [0.20.0] - 2026-07-11

### Neu
- **Wiederholungen verwalten**: Wiederkehrende Aufgaben besitzen jetzt eine eigene Verwaltung. Serien lassen sich bearbeiten, pausieren, fortsetzen und vollständig löschen; Rhythmus, Startdatum und Zuweisungen sind änderbar, der nächste Termin wird angezeigt.
- **Morgen-Ausblick auf Heute**: Eine kompakte Karte zeigt morgige Termine, Aufgaben und das geplante Abendessen. Auch tägliche Wiederholungen werden für die Vorschau berücksichtigt.
- **Mehrtägige Kalenderleiste**: Oberhalb der 14-Tage-Liste werden mehrtägige Termine als durchgehende Balken über ihre tatsächliche Zeitspanne dargestellt.
- **Undo für Aufgaben, Termine, Einkäufe und Essen**: Nach Abhaken oder Löschen erscheint fünf Sekunden lang „Rückgängig“. Löschungen werden erst nach Ablauf dieser Frist wirklich ausgeführt.
- **Müll-Entity testen**: Unter „Mehr → Mülltag“ prüft ein neuer Button die konfigurierte Entity und zeigt ihren aktuellen State an.

### Geändert
- **Müllarten auf einen Blick**: Altpapier, Gelber Sack, Biomüll und Restmüll erhalten farbige Chips. Bei einer Abholung morgen erinnert FamilyDaily zusätzlich daran, die Tonne heute Abend rauszustellen.
- **Verständlicher Wochenstreifen**: Ganztägige Termine, Termine mit Uhrzeit, Essen und Aufgaben verwenden unterschiedliche Markierungen statt gleichartiger Punkte.
- Serien speichern nun ein Startdatum. Eine automatische Migration ergänzt es bei bestehenden Wiederholungen; Änderungen an einer Serie werden auf offene und zukünftige Instanzen übertragen.

### Tests
- Regressionstests decken Löschen, Pausieren, Bearbeiten, Fortsetzen, morgige Serienvorschau und typische Müllsensor-States ab.
- Desktop- und Mobilansicht wurden auf Layout, Überlauf, Morgen-Karte, Wochenmarkierungen und Serienmanager geprüft.

---

## [0.19.6] - 2026-07-11

### Geändert
- **Nächste Müllabholung dauerhaft auf Heute**: Der konfigurierte HA-Sensor wird nun immer angezeigt, solange er einen verfügbaren State liefert. Spätere Abholungen erscheinen kompakt als „Nächste Abholung“; heute und morgen werden weiterhin hervorgehoben.
- Die Erkennung akzeptiert neben `in X Tag(en)` auch States mit `heute` oder `morgen` unabhängig von Groß-/Kleinschreibung. `unknown` und `unavailable` werden ausgeblendet.
- Der Hilfetext unter „Mehr → Mülltag“ beschreibt das neue Verhalten.

---

## [0.19.5] - 2026-07-11

### Geändert
- **Kurzes Feuerwerk statt Level-up-Popup**: Beim Erledigen einer Aufgabe erscheinen für rund 1,5 Sekunden drei einfache, farbige Partikelbursts. Das bisherige Popup samt Abdunklung und „Familien-XP“-Karte entfällt; Sound und haptisches Feedback bleiben erhalten.
- Bei aktivierter Systemeinstellung „Bewegung reduzieren“ wird der visuelle Effekt vollständig ausgeblendet.

---

## [0.19.4] - 2026-07-11

### Geändert
- **Wiederholungsaufgaben eindeutig löschen**: Beim Löschen kann jetzt klar zwischen dem einzelnen Vorkommen, der vollständigen Serie und Abbrechen gewählt werden. Ein einzeln gelöschtes Vorkommen erscheint nicht mehr sofort erneut.
- **Mehrtägige Termine in der Terminübersicht**: Termine werden an jedem Tag ihrer Laufzeit aufgeführt. Folgetage sind dezent als „Fortsetzung“ gekennzeichnet; das gilt für ganztägige und zeitgebundene Termine.

### Technik
- Datenbankmigration ergänzt einen internen Übersprungen-Marker für gezielt gelöschte Serienvorkommen.
- Regressionstests decken das Löschen eines einzelnen Vorkommens und einer vollständigen Serie ab.

---

## [0.19.3] - 2026-07-09

### Neu
- **OSRS-Sounddatei lokal verwenden**: Das Format `.oga` wird für den optionalen Level-up-Ton unterstützt; eine Datei namens `Level_up_fireworks.oga` wird direkt erkannt.

---

## [0.19.2] - 2026-07-09

### Neu
- **Level-up beim Erledigen**: Abgehakte Aufgaben feiern ihren Abschluss mit einer Retro-Animation, haptischem Feedback und Ton. Optional kann eine nur lokal gespeicherte Datei `task-level-up.mp3`, `.ogg` oder `.wav` den eingebauten Ton ersetzen.

---

## [0.19.1] - 2026-07-09

### Neu
- **Terminübersicht**: Der Kalender bietet jetzt zusätzlich zur 14-Tage-Ansicht eine umschaltbare, scrollbare Liste aller kommenden Termine. Sie ist nach Datum gruppiert und kann bei Bedarf um weitere zwölf Monate erweitert werden.

---

## [0.19.0] - 2026-07-09

### Neu
- **Aufgaben direkt bearbeiten**: Ein Tap auf eine Aufgabe öffnet auf den Ansichten „Heute“ und „Aufgaben“ das Bearbeitungsformular. Titel, Fälligkeitsdatum und Zuweisungen lassen sich dort ändern.
- **Monatsübersicht im Kalender**: Der Datumswähler zeigt zunächst alle Monate eines Jahres; so lassen sich Termine schnell in einem beliebigen Monat anlegen.

### Fix
- Beim Bearbeiten kann ein Fälligkeitsdatum jetzt auch wieder entfernt werden.

---

## [0.18.0] - 2026-07-05

### Neu
- **Aufgaben verschieben**: Offene Aufgaben können per Kalender-Button auf heute, morgen oder ein frei wählbares Datum verschoben werden. Bei wiederkehrenden Aufgaben wird nur die konkrete Aufgabe verschoben, nicht die Serie.

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
