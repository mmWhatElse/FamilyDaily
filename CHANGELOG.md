# Changelog

Alle relevanten Änderungen an FamilyDaily werden hier festgehalten.
Format: [Keep a Changelog](https://keepachangelog.com/de/1.0.0/)

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
