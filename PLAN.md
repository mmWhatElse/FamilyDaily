# FamilyDaily — V1 Plan

Self-hosted family command center as a Home Assistant addon. German UI, browser-based,
phone-first, local data. Inspired by Dæly (daely-shop.com), reduced to what our family
actually uses.

## Goals

- One shared surface for the family: calendar, tasks, shopping lists, meal plan
- Runs entirely on Home Assistant (addon), data stays local (SQLite in `/data`)
- No accounts, no cloud, no OAuth in the app — calendar sync goes through HA's
  existing calendar integrations
- UI that is nice enough that the family *wants* to use it ("Heute" screen, ≤2 taps
  to every core action)

## Non-Goals (V1)

- Recipe storage / management (a meal is a text line + optional URL)
- Points / rewards / gamification
- Photo frame mode
- Per-person login or permissions (colors, not accounts)
- Native mobile apps (browser + home screen bookmark)

## Modules

### 1. Kalender
- Reads calendar events live from HA (`calendar` entities) — nothing stored locally
- Week view + day view, color-coded per family member (entity → person mapping)
- **Write-back:** create/edit/delete events via HA's `calendar.create_event` service
  (and per-integration equivalents). The app is the primary surface, so write is V1.
- Event form: Titel, Datum/Zeit (oder ganztägig), Kalender (= person), Notiz

### 2. Aufgaben
- Tasks with: Titel, zugewiesene Person(en), optionales Fälligkeitsdatum, erledigt-Flag
- Recurrence (täglich / wöchentlich / monatlich) modeled as template + spawned
  instances, so a single occurrence can be checked off without ending the series
- "Heute fällig" surfaces on the Heute screen

### 3. Einkaufen
- Multiple lists (Supermarkt, Drogerie, …), items with optional category
- Autocomplete from previously used item names (this is the feature that makes it fast)
- Checked items collapse to the bottom; "Erledigte löschen" action
- Live sync between devices (WebSocket, polling fallback)

### 4. Mahlzeiten
- One slot per day in V1: Abendessen
- Entry = Titel + optionale Notiz/URL (Chefkoch-Link etc.)
- Week view; copy last week as starting point

## UI Concept (phone-first)

- **Landing screen "Heute"** — not a menu:
  - Termine heute + morgen (alle Familienmitglieder, farbcodiert)
  - Offene Aufgaben für heute
  - Heutiges Abendessen
  - Einkaufslisten-Badge ("7 Artikel")
- Bottom tab bar: **Heute · Kalender · Listen · Essen**
- Big touch targets, works equally on a wall tablet later
- Language: German only in V1 (hardcoded strings are fine; i18n later if ever)

## Architecture

```
┌─────────────────── HA Addon (one container) ───────────────────┐
│  FastAPI (Python)                                              │
│   ├─ REST API  (/api/tasks, /api/lists, /api/meals, …)         │
│   ├─ WebSocket (live updates to all open clients)              │
│   ├─ HA bridge (Supervisor token → HA REST API for calendars)  │
│   └─ serves Svelte frontend as static files                    │
│  SQLite at /data/familydaily.db                                │
└────────────────────────────────────────────────────────────────┘
```

- **Backend:** Python / FastAPI
- **Frontend:** Svelte (SvelteKit static adapter), mobile-first CSS
- **DB:** SQLite — single file, zero admin, lives in addon `/data` (survives updates)
- **HA access:** addon runs with `homeassistant_api: true` → `SUPERVISOR_TOKEN`
  env var, calls `http://supervisor/core/api/...`. No user-facing auth setup.
- **Access paths:**
  - HA Ingress → sidebar entry inside HA
  - Direct port (e.g. 8099) → bookmarkable URL for phone home screens
- **Remote access:** whatever the household already uses for HA (Nabu Casa / VPN) —
  not the addon's problem

## Data Model

```
person          id, name, color, emoji, calendar_entity_id (nullable)
task_template   id, title, person_ids, recurrence (none/daily/weekly/monthly),
                weekday/day-of-month params, active
task            id, template_id (nullable), title, person_ids,
                due_date (nullable), done, completed_at
shopping_list   id, name, icon, sort_order
shopping_item   id, list_id, name, category (nullable), checked, checked_at
meal            id, date, title, note (nullable), url (nullable)
item_history    name, category, use_count        -- feeds autocomplete
```

Calendar events are **not** stored — always read from / written through HA.

## Calendar Strategy (decided)

**HA Local Calendar integration is the family's primary calendar in V1.**
One Local Calendar per family member (e.g. `calendar.familie_mama`,
`calendar.familie_papa`, `calendar.familie_kind`), created once in HA.

- Fully local (fits the privacy goal), full read/write support via HA services
- Create: `calendar.create_event` with `summary`,
  `start_date_time`/`end_date_time` (or `start_date`/`end_date` for all-day),
  `description`
- External calendars (work, school) can be added later as **read-only overlays**
- Person → calendar mapping configured once in app settings
  (dropdown of HA calendar entities)

## Remaining Assumptions — verify during M1

1. Addon with `homeassistant_api: true` can call
   `GET /api/calendars/<entity_id>?start=...&end=...` and `calendar.create_event`
   via the Supervisor token
2. Local Calendar edit/delete behavior via API (HA supports updating/deleting
   local calendar events through websocket API; REST coverage to confirm —
   fallback: delete + recreate)

## Milestones

1. **M0 — Calendar strategy** ✅ decided: HA Local Calendar (read/write, fully local)
2. **M1 — Addon skeleton:** ← in progress container builds, installs in HA, Ingress works,
   FastAPI serves a hello page, SQLite persists across restart
3. **M2 — Einkaufen:** full lists feature incl. autocomplete + live sync
   (smallest module that proves the whole stack and is immediately useful)
4. **M3 — Aufgaben:** incl. recurrence
5. **M4 — Kalender:** read view (week/day), then write-back
6. **M5 — Mahlzeiten + Heute screen:** the Heute screen lands last because it
   aggregates all other modules
7. **M6 — Polish:** empty states, error states, offline notice, app icon,
   home screen install (PWA manifest)
