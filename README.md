<img src="familydaily/logo.png" alt="FamilyDaily" width="460">
Selbst gehosteter Familien-Planer als Home-Assistant-Addon — Kalender, Aufgaben,
Einkaufslisten und Essensplan. Komplett lokal, kein Cloud-Konto, keine Anmeldung.

## Disclaimer

Erstellt mit Claude als Privatprojekt, work-in-progress solange es Spass macht. 

**Version 0.20.1**

## Funktionen

| Modul | Was es kann |
|---|---|
| **Heute** | Tagesübersicht mit unterscheidbaren Wochenmarkierungen, Terminen, Aufgaben, Abendessen, Einkaufs-Zettel, nächster Müllabholung und kompaktem Ausblick auf morgen |
| **Kalender** | 14-Tage-Liste und Terminübersicht aus HA-Kalendern; mehrtägige Termine zusätzlich als durchgehende Zeitspannen; Termine anlegen, bearbeiten, löschen und Personen zuordnen |
| **Aufgaben** | Aufgaben mit Person, Fälligkeit und zeitlich begrenzbarer Wiederholung; Serien zentral bearbeiten, pausieren, fortsetzen oder löschen; fünf Sekunden Undo nach Abhaken und Löschen – ebenso bei Terminen, Einkäufen und Essen |
| **Listen** | Mehrere Einkaufslisten, Autovervollständigung, Live-Sync zwischen Geräten; Kategorien mit Gruppierung in Supermarkt-Reihenfolge — einmal zugeordnet, landen Artikel künftig automatisch richtig |
| **Essen** | Wochenplan Abendessen mit Zutaten pro Gericht: Zutaten vom letzten Mal werden übernommen, ein Tap setzt alles auf die Einkaufsliste; letzte Woche kopieren |
| **Einstellungen** | Kalender auswählen & einfärben, Familienmitglieder, Benachrichtigungen, helles/dunkles Design |
| **Benachrichtigungen** | Push-Erinnerungen an mehrere Geräte über HA Companion App |

## Design

Warmes „Küchenpinnwand"-Design: Papier-Optik mit Zettel-Karten, Klebestreifen und
Haftnotizen, dazu ein vollwertiger **Dark Mode** (folgt der Systemeinstellung,
umschaltbar unter *Mehr → Darstellung*). Schriften (Baloo 2 + Nunito) und Icons
(Tabler) sind lokal gebundled — die App braucht auch fürs Aussehen kein Internet.

## Voraussetzungen

- Home Assistant OS oder Supervised
- Mindestens ein Kalender in HA — z. B. die Integration **Lokaler Kalender**
  (Einstellungen → Geräte & Dienste → Integration hinzufügen → „Lokaler Kalender").
  Ein gemeinsamer Familienkalender reicht; mehrere Kalender (z. B. pro Person oder
  „Arbeit"/„Schule") bekommen in FamilyDaily je eine eigene Farbe.
- In FamilyDaily unter **Einstellungen** sind alle HA-Kalender automatisch aktiv —
  dort lassen sich einzelne abschalten und Farben anpassen.

## Installation

1. Home Assistant → **Einstellungen → Add-ons → Add-on Store**
2. Menü (⋮) → **Repositories** → `https://github.com/mmWhatElse/FamilyDaily` eintragen
3. **FamilyDaily** installieren und starten
4. Öffnen per Seitenleiste (Ingress) oder direkt: `http://<ha-host>:8099`

Das Addon läuft vollständig ohne Internet. Daten liegen in SQLite unter `/data/familydaily.db`
und bleiben bei Updates erhalten. Kalenderdaten werden nicht gespeichert — sie kommen
direkt aus HA.

## Eigener Level-up-Sound (optional)

FamilyDaily kann beim Erledigen einer Aufgabe einen selbst bereitgestellten Ton spielen.
Lege dafür eine Datei namens `Level_up_fireworks.oga`, `task-level-up.mp3`,
`task-level-up.ogg`, `task-level-up.oga` oder `task-level-up.wav` im Konfigurationsordner
des Add-ons ab (im Container: `/config`).
Die Datei bleibt lokal auf deiner Home-Assistant-Installation und wird nicht über dieses
Repository verteilt. Ohne Datei verwendet die App automatisch die eingebaute Retro-Fanfare.

## Manuelle Installation (ohne GitHub-Repository)

Wer das Addon direkt vom lokalen Rechner installieren möchte, ohne ein öffentliches
Repository einzutragen:

1. Den Ordner `familydaily/` (enthält `config.yaml`, `Dockerfile` usw.) auf den HA-Host
   kopieren — z. B. nach `/addons/familydaily/` via **Samba-Addon** (`\\<ha-host>\addons\`)
   oder per **SSH-Addon** (`scp -r familydaily/ root@<ha-host>:/addons/familydaily/`).
2. Im Add-on Store auf **„Lokale Add-ons"** (oben rechts) tippen — FamilyDaily erscheint dort.
3. Installieren → das Image wird lokal auf dem HA-Host gebaut (dauert beim ersten Mal
   einige Minuten).
4. Starten und wie gewohnt öffnen.

**Updates:** Ordner erneut kopieren, dann im Add-on Store **„Neu laden"** und anschließend
**„Aktualisieren"** wählen — das Image wird neu gebaut. Die Daten in `/data` bleiben erhalten.

## Lokale Entwicklung

```bash
cd familydaily
pip install -r requirements.txt
FAMILYDAILY_DATA=./devdata uvicorn app.main:app --reload --port 8099
```

Ohne `SUPERVISOR_TOKEN` startet die App, meldet aber „nicht mit HA verbunden" — alle
Funktionen außer dem Kalender sind voll nutzbar.

## Stack

- **Backend:** Python / FastAPI + aiosqlite, WebSocket für Live-Updates
- **Frontend:** Vanilla JS SPA (kein Build-Schritt), mobil-first CSS mit Hell/Dunkel-Themes, lokale Schriften & SVG-Icons
- **Datenbank:** SQLite in `/data` (überlebt Addon-Updates, Migrationen laufen beim Start)
- **Kalender:** HA-API via Supervisor-Token (`homeassistant_api: true`)
