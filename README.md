# FamilyDaily

Selbst gehosteter Familien-Planer als Home-Assistant-Addon: Kalender, Aufgaben,
Einkaufslisten und Essensplan. Komplett lokal, ohne Cloud und ohne Konten.

Siehe [PLAN.md](PLAN.md) für das Konzept und die Roadmap.

## Installation (als Addon-Repository)

1. Home Assistant → **Einstellungen → Add-ons → Add-on Store**
2. Menü (⋮) → **Repositories** → `https://github.com/mmWhatElse/FamilyDaily` hinzufügen
3. **FamilyDaily** installieren und starten
4. Öffnen über die Seitenleiste (Ingress) oder direkt: `http://<ha-host>:8099`

## Voraussetzungen

- Home Assistant OS / Supervised (Addons werden benötigt)
- Für den Kalender: die Integration **Lokaler Kalender** in HA
  (Einstellungen → Geräte & Dienste → Integration hinzufügen → "Lokaler Kalender"),
  idealerweise ein Kalender pro Familienmitglied

## Lokale Entwicklung

```bash
cd familydaily
pip install -r requirements.txt
FAMILYDAILY_DATA=./devdata python -m uvicorn app.main:app --reload --port 8099
```

Ohne `SUPERVISOR_TOKEN` läuft die App, meldet aber „nicht mit Home Assistant verbunden".
