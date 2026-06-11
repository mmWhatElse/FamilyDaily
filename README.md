# FamilyDaily

Selbst gehosteter Familien-Planer als Home-Assistant-Addon — Kalender, Aufgaben,
Einkaufslisten und Essensplan. Komplett lokal, kein Cloud-Konto, keine Anmeldung.

**Version 0.9.0 (V1)**

## Funktionen

| Modul | Was es kann |
|---|---|
| **Heute** | Tagesübersicht: Termine, fällige Aufgaben, Abendessen, Einkaufslisten-Badge |
| **Kalender** | 14-Tage-Liste aus HA-Kalendern, Termin anlegen, löschen |
| **Aufgaben** | Aufgaben mit Person, Fälligkeitsdatum, Wiederholung (täglich / wöchentlich / monatlich) |
| **Essen** | Wochenplan Abendessen, letzte Woche übernehmen |
| **Einstellungen** | Familienmitglieder verwalten, HA-Kalender pro Person zuordnen |
| **Einkaufen** | Mehrere Listen, Autovervollständigung, Live-Sync zwischen Geräten |

## Voraussetzungen

- Home Assistant OS oder Supervised
- Integration **Lokaler Kalender** in HA — ein Kalender pro Familienmitglied
  (Einstellungen → Geräte & Dienste → Integration hinzufügen → „Lokaler Kalender")
- In FamilyDaily unter **Einstellungen** jeden Kalender einer Person zuordnen

## Installation

1. Home Assistant → **Einstellungen → Add-ons → Add-on Store**
2. Menü (⋮) → **Repositories** → `https://github.com/mmWhatElse/FamilyDaily` eintragen
3. **FamilyDaily** installieren und starten
4. Öffnen per Seitenleiste (Ingress) oder direkt: `http://<ha-host>:8099`

Das Addon läuft vollständig ohne Internet. Daten liegen in SQLite unter `/data/familydaily.db`
und bleiben bei Updates erhalten. Kalenderdaten werden nicht gespeichert — sie kommen
direkt aus HA.

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
- **Frontend:** Vanilla JS SPA (kein Build-Schritt), mobil-first CSS
- **Datenbank:** SQLite in `/data` (überlebt Addon-Updates)
- **Kalender:** HA-API via Supervisor-Token (`homeassistant_api: true`)
