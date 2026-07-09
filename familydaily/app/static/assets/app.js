/* FamilyDaily SPA — no build step, plain JS. */

const $main = document.getElementById("view");
const state = { tab: "heute", listId: null, listName: "", calOffset: 0, calView: "range", agendaYears: 1, taskFilter: null };

/* ---------- helpers ---------- */

const api = {
  get: (url) => fetch(url).then((r) => r.json()),
  post: (url, body) =>
    fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: body ? JSON.stringify(body) : null,
    }).then((r) => (r.status === 204 ? null : r.json())),
  put: (url, body) =>
    fetch(url, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }).then((r) => r.json()),
  patch: (url, body) =>
    fetch(url, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }).then((r) => r.json()),
  del: (url) => fetch(url, { method: "DELETE" }),
};

function setMain(...nodes) {
  $main.replaceChildren(...nodes.filter((n) => n != null));
}

function showLoading() {
  setMain(el("div", { class: "loading" },
    el("div", { class: "spinner" }),
    el("p", { class: "muted" }, "Lädt …")
  ));
}

const SVG_NS = "http://www.w3.org/2000/svg";

/* Inline-SVG aus dem Sprite in index.html (#i-<name>) */
function icon(name, size = 18) {
  const svg = document.createElementNS(SVG_NS, "svg");
  svg.setAttribute("class", "icon");
  svg.setAttribute("width", size);
  svg.setAttribute("height", size);
  svg.setAttribute("aria-hidden", "true");
  const use = document.createElementNS(SVG_NS, "use");
  use.setAttribute("href", `#i-${name}`);
  svg.appendChild(use);
  return svg;
}

function emptyState(iconName, title, sub) {
  return el("div", { class: "empty-state" },
    el("div", { class: "empty-icon" }, icon(iconName, 42)),
    el("p", { class: "empty-title" }, title),
    sub ? el("p", { class: "empty-sub" }, sub) : null
  );
}

function greeting() {
  const h = new Date().getHours();
  if (h < 5)  return "Gute Nacht";
  if (h < 10) return "Guten Morgen";
  if (h < 12) return "Schönen Vormittag";
  if (h < 14) return "Mahlzeit";
  if (h < 17) return "Schönen Nachmittag";
  if (h < 21) return "Guten Abend";
  return "Gute Nacht";
}

const WEATHER_DE = {
  "clear-night": "klar", cloudy: "bewölkt", fog: "neblig", hail: "Hagel",
  lightning: "Gewitter", "lightning-rainy": "Gewitter", partlycloudy: "teils bewölkt",
  pouring: "Starkregen", rainy: "regnerisch", snowy: "Schnee", "snowy-rainy": "Schneeregen",
  sunny: "sonnig", windy: "windig", "windy-variant": "windig", exceptional: "Unwetter",
};

/* Akzentfarbe eines Termins: getaggte Personen vor Kalenderfarbe;
   bei mehreren Personen ein Farb-Kreisdiagramm */
function eventColor(ev) {
  const cols = (ev.persons || []).map((p) => p.color).filter(Boolean);
  if (cols.length === 0) return ev.color || "var(--accent)";
  if (cols.length === 1) return cols[0];
  const seg = 360 / cols.length;
  const stops = cols.map((c, i) => `${c} ${i * seg}deg ${(i + 1) * seg}deg`).join(", ");
  return `conic-gradient(${stops})`;
}

/* ---------- Theme (hell/dunkel) ---------- */

function syncThemeColor() {
  const dark = document.documentElement.dataset.theme === "dark";
  document.querySelector("meta[name=theme-color]")
    ?.setAttribute("content", dark ? "#251e12" : "#f8f1e2");
}

function applyTheme(t) {
  document.documentElement.dataset.theme = t;
  try { localStorage.setItem("fd_theme", t); } catch (e) { /* private mode */ }
  syncThemeColor();
}

function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") node.className = v;
    else if (k.startsWith("on")) node.addEventListener(k.slice(2), v);
    else node.setAttribute(k, v);
  }
  for (const c of children) {
    if (c == null) continue;
    node.append(c.nodeType ? c : document.createTextNode(c));
  }
  return node;
}

function isoDate(d = new Date()) {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function fmtDate(iso) {
  if (!iso) return "";
  const d = new Date(iso.length === 10 ? iso + "T12:00:00" : iso);
  return d.toLocaleDateString("de-DE", { weekday: "short", day: "numeric", month: "numeric" });
}

function fmtTime(iso) {
  if (!iso || iso.length === 10) return "";
  const d = new Date(iso);
  return d.toLocaleTimeString("de-DE", { hour: "2-digit", minute: "2-digit" });
}

function weekMonday() {
  const d = new Date();
  d.setDate(d.getDate() - ((d.getDay() + 6) % 7));
  d.setHours(0, 0, 0, 0);
  return d;
}

const DAYS_DE = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"];
const RECUR_LABEL = { daily: "täglich", weekly: "wöchentlich", monthly: "monatlich" };

/* Einkaufs-Kategorien in Supermarkt-Reihenfolge */
const CATEGORIES = [
  "Obst & Gemüse", "Backwaren", "Fleisch & Fisch", "Kühlregal", "Tiefkühl",
  "Vorräte", "Getränke", "Drogerie", "Haushalt", "Sonstiges",
];

function addDays(iso, n) {
  const d = new Date(iso + "T12:00:00");
  d.setDate(d.getDate() + n);
  return isoDate(d);
}

function taskShiftButton(task) {
  if (task.done) return null;
  return el("button", {
    class: "btn-icon task-shift-btn",
    title: "Aufgabe verschieben",
    "aria-label": "Aufgabe verschieben",
    onclick: (e) => {
      e.stopPropagation();
      openTaskShift(task);
    },
  }, icon("calendar", 16));
}

function toast(msg) {
  document.querySelector(".toast")?.remove();
  const t = el("div", { class: "toast" }, msg);
  document.body.appendChild(t);
  setTimeout(() => t.classList.add("show"), 20);
  setTimeout(() => {
    t.classList.remove("show");
    setTimeout(() => t.remove(), 300);
  }, 2200);
}

/* Zutaten eines Gerichts auf die erste Einkaufsliste setzen (idempotent) */
async function ingredientsToList(meal) {
  const lists = await api.get("api/shopping/lists").catch(() => []);
  if (!lists.length) { toast("Keine Einkaufsliste vorhanden"); return false; }
  const target = lists[0];
  let added = 0;
  for (const name of meal.ingredients || []) {
    const res = await api.post(`api/shopping/lists/${target.id}/items`, { name }).catch(() => null);
    if (res && !res.duplicate) added++;
  }
  toast(added
    ? `${added} Zutat${added === 1 ? "" : "en"} auf „${target.name}“ gesetzt`
    : "Alles schon auf der Liste");
  return true;
}

async function shiftTask(task, dueDate, overlay) {
  await api.patch(`api/tasks/${task.id}`, { due_date: dueDate });
  overlay?.remove();
  toast(`Aufgabe verschoben auf ${fmtDate(dueDate)}`);
  render();
}

function openTaskShift(task) {
  const overlay = el("div", { class: "modal-overlay", onclick: (e) => { if (e.target === overlay) overlay.remove(); } });
  const dateInput = el("input", {
    type: "date",
    class: "form-input",
    value: task.due_date || isoDate(),
  });
  const errMsg = el("p", { class: "err", style: "display:none" });

  overlay.appendChild(el("div", { class: "modal-card task-shift-card" },
    el("div", { class: "modal-handle" }),
    el("h2", { style: "margin-bottom:4px" }, "Aufgabe verschieben"),
    el("p", { class: "shift-task-title" }, task.title),
    el("div", { class: "shift-options" },
      el("button", { class: "btn-soft", onclick: () => shiftTask(task, isoDate(), overlay) },
        icon("sun", 15), "Heute"),
      el("button", { class: "btn-ghost", onclick: () => shiftTask(task, addDays(isoDate(), 1), overlay) },
        icon("calendar", 15), "Morgen")
    ),
    el("p", { class: "form-field-label" }, "Datum wählen"),
    el("div", { class: "shift-date-row" },
      dateInput,
      el("button", { class: "btn-soft", onclick: async () => {
        if (!dateInput.value) {
          errMsg.textContent = "Datum fehlt";
          errMsg.style.display = "";
          return;
        }
        await shiftTask(task, dateInput.value, overlay);
      }}, "Setzen")
    ),
    errMsg,
    el("button", { class: "btn-ghost", onclick: () => overlay.remove() }, "Abbrechen")
  ));
  document.body.appendChild(overlay);
}

/* ---------- live updates ---------- */

function connectWs() {
  const proto = location.protocol === "https:" ? "wss:" : "ws:";
  const base = location.pathname.replace(/\/$/, "");
  const ws = new WebSocket(`${proto}//${location.host}${base}/api/ws`);
  ws.onmessage = (ev) => {
    const msg = JSON.parse(ev.data);
    const t = state.tab;
    if (
      (msg.type === "shopping" && (t === "listen" || t === "heute")) ||
      (msg.type === "tasks"    && (t === "aufgaben" || t === "heute")) ||
      (msg.type === "calendar" && (t === "kalender" || t === "heute")) ||
      (msg.type === "meals"    && (t === "essen" || t === "heute")) ||
      (msg.type === "persons"  && t === "einstellungen")
    ) render();
  };
  ws.onclose = () => setTimeout(connectWs, 3000);
  setInterval(() => { if (ws.readyState === 1) ws.send("ping"); }, 30000);
}

/* ---------- Heute ---------- */

async function viewHeute() {
  const today = isoDate();
  const mon = weekMonday();
  const sun = new Date(mon); sun.setDate(mon.getDate() + 6);
  const nextMon = new Date(mon); nextMon.setDate(mon.getDate() + 7);
  const weekStart = isoDate(mon);
  const weekEnd = isoDate(sun);

  const day30 = addDays(today, 30);
  const tomorrow = addDays(today, 1);

  const [lists, tasks, weekMeals, weekTasks, weekCal, persons, weather, appSettings, countdownRaw] = await Promise.all([
    api.get("api/shopping/lists").catch(() => []),
    api.get("api/tasks?view=today").catch(() => []),
    api.get(`api/meals?start=${weekStart}&end=${weekEnd}`).catch(() => []),
    api.get("api/tasks").catch(() => []),
    api.get(`api/calendar/events?start=${weekStart}T00:00:00&end=${isoDate(nextMon)}T00:00:00`).catch(() => null),
    api.get("api/persons").catch(() => []),
    api.get("api/weather").catch(() => null),
    api.get("api/settings").catch(() => ({})),
    api.get(`api/calendar/events?start=${tomorrow}T00:00:00&end=${day30}T00:00:00`).catch(() => null),
  ]);

  // Mülltag: entity state nur laden wenn konfiguriert
  const muellEntityId = appSettings?.muell_entity || "";
  let muellInfo = null;
  if (muellEntityId) {
    const md = await api.get(`api/ha/entity?entity_id=${encodeURIComponent(muellEntityId)}`).catch(() => null);
    if (md?.available) {
      const m = md.state.match(/^(.+?)\s+in\s+(\d+)\s+tag/i);
      if (m) {
        const days = parseInt(m[2], 10);
        if (days <= 1) muellInfo = { what: m[1], days };
      }
    }
  }

  // Countdown: ganztägige Termine in den nächsten 30 Tagen
  const quickNote = appSettings?.quick_note || "";
  const countdownEvents = Array.isArray(countdownRaw)
    ? countdownRaw
        .filter((ev) => ev.all_day && (ev.start || "").slice(0, 10) > today)
        .sort((a, b) => (a.start || "").localeCompare(b.start || ""))
        .slice(0, 3)
        .map((ev) => {
          const days = Math.round(
            (new Date(ev.start.slice(0, 10) + "T12:00:00") - new Date(today + "T12:00:00")) / 86400000
          );
          return { title: ev.summary, days };
        })
    : [];

  const openTotal = lists.reduce((s, l) => s + l.open_count, 0);
  const todayLabel = new Date().toLocaleDateString("de-DE", {
    weekday: "long", day: "numeric", month: "long",
  });
  const personMap = Object.fromEntries(persons.map((p) => [p.id, p]));

  const calOk = Array.isArray(weekCal);
  // Heutige Termine (inkl. mehrtägiger, die heute laufen — Ganztags-Ende ist exklusiv)
  const cal = calOk ? weekCal.filter((ev) => {
    const s = (ev.start || "").slice(0, 10);
    const e = (ev.end || ev.start || "").slice(0, 10);
    return s <= today && (ev.all_day ? today < e : today <= e);
  }) : null;

  const weekMealMap = Object.fromEntries(weekMeals.map((m) => [m.date, m]));
  const weekTaskMap = {};
  weekTasks.forEach((t) => {
    if (t.due_date && !t.done) {
      (weekTaskMap[t.due_date] = weekTaskMap[t.due_date] || []).push(t);
    }
  });
  // Termine pro Tag für die Punkte im Wochenstreifen — mehrtägige zählen an jedem Tag
  const weekEvMap = {};
  if (calOk) weekCal.forEach((ev) => {
    const s = (ev.start || "").slice(0, 10);
    if (!s) return;
    let last = (ev.end || s).slice(0, 10);
    if (ev.all_day) last = addDays(last, -1); // Ganztags-Ende ist exklusiv
    else if ((ev.end || "").slice(11, 16) === "00:00" && last > s) {
      last = addDays(last, -1); // Ende exakt Mitternacht zählt nicht in den Folgetag
    }
    if (last < s) last = s;
    let d = s < weekStart ? weekStart : s;
    const stop = last > weekEnd ? weekEnd : last;
    for (let guard = 0; d <= stop && guard < 7; d = addDays(d, 1), guard++) {
      (weekEvMap[d] = weekEvMap[d] || []).push(ev);
    }
  });
  const meal = weekMealMap[today];

  // Week strip: Mon–Sun with event/meal/task dots
  const weekDayNodes = [];
  for (let i = 0; i < 7; i++) {
    const d = new Date(mon); d.setDate(mon.getDate() + i);
    const iso = isoDate(d);
    const isToday = iso === today;
    const isPast = iso < today;
    const dayName = d.toLocaleDateString("de-DE", { weekday: "short" }).replace(/\.$/, "");

    const dots = [];
    (weekEvMap[iso] || []).slice(0, 3).forEach((ev) =>
      dots.push(el("span", { class: "week-dot", style: `background:${eventColor(ev)}` }))
    );
    if (weekMealMap[iso]) dots.push(el("span", { class: "week-dot meal" }));
    (weekTaskMap[iso] || []).slice(0, 3).forEach(() =>
      dots.push(el("span", { class: "week-dot task" }))
    );

    weekDayNodes.push(
      el("div", {
        class: "week-day" + (isToday ? " today" : "") + (isPast ? " past" : ""),
        onclick: () => switchTab("kalender"),
      },
        el("span", { class: "week-day-name" }, dayName),
        el("span", { class: "week-day-num" }, String(d.getDate())),
        el("div", { class: "week-dots" }, ...dots.slice(0, 4))
      )
    );
  }

  // Kopfzeile: Begrüßung mit Wetter + Anzahl-Zusammenfassung
  let hello = greeting();
  if (weather?.available && weather.temperature != null) {
    const cond = WEATHER_DE[weather.condition] || "";
    hello += ` · ${Math.round(weather.temperature)}°${cond ? " " + cond : ""}`;
  }
  const subParts = [];
  if (calOk) subParts.push(cal.length === 1 ? "1 Termin" : `${cal.length} Termine`);
  const openToday = tasks.filter((t) => !t.done).length;
  subParts.push(openToday === 1 ? "1 Aufgabe" : `${openToday} Aufgaben`);
  subParts.push(meal ? "Essen steht fest" : "Essen noch offen");

  // Termine-Inhalt
  let calContent;
  if (!calOk) {
    calContent = el("div", { class: "card" },
      emptyState("wifi-off", "Kalender nicht verbunden", "In Einstellungen Kalender zuordnen"));
  } else if (cal.length === 0) {
    calContent = el("div", { class: "card" },
      emptyState("calendar-check", "Frei heute", "Keine Termine eingetragen"));
  } else {
    calContent = el("ul", { class: "event-list" }, ...cal.map((ev) => {
      const time = fmtTime(ev.start);
      return el("li", {
        class: "event-item",
        style: `--pc:${eventColor(ev)}`,
        onclick: () => openEventForm(ev, persons),
      },
        el("span", { class: "event-body" },
          el("span", { class: "event-title" }, ev.summary),
          el("span", { class: "event-meta" }, ev.calendar)
        ),
        time ? el("span", { class: "event-time" }, time) : null
      );
    }));
  }

  // Aufgaben-Inhalt
  let taskContent;
  if (tasks.length === 0) {
    taskContent = el("div", { class: "card" },
      emptyState("circle-check", "Alles erledigt", "Keine offenen Aufgaben heute"));
  } else {
    taskContent = el("ul", { class: "task-list" }, ...tasks.map((t) => {
      const pips = (t.person_ids || []).map((pid) => {
        const p = personMap[pid];
        return p ? el("span", { class: "person-pip", style: `background:${p.color}`, title: p.name },
          p.emoji || p.name[0]) : null;
      });
      return el("li", { class: "task-item task-item-editable" + (t.done ? " done" : ""), onclick: () => openTaskForm(persons, t) },
        el("button", {
          class: "check",
          onclick: (e) => {
            e.stopPropagation();
            api.patch(`api/tasks/${t.id}`, { done: !t.done }).then(render);
          },
        }, t.done ? icon("check", 14) : ""),
        el("span", { class: "task-title", style: "flex:1" }, t.title),
        taskShiftButton(t),
        ...pips
      );
    }));
  }

  // Schnellnotiz-Textarea
  const noteTA = document.createElement("textarea");
  noteTA.className = "quick-note-ta";
  noteTA.placeholder = "Notiz fürs Board …";
  noteTA.value = quickNote;
  let noteDirty = false;
  noteTA.addEventListener("input", () => { noteDirty = true; });
  noteTA.addEventListener("blur", () => {
    if (noteDirty) {
      api.patch("api/settings", { quick_note: noteTA.value });
      noteDirty = false;
    }
  });

  setMain(
    el("header", { class: "heute-header" },
      el("div", {},
        el("h1", {}, todayLabel),
        el("p", { class: "heute-sub" }, `${hello} — ${subParts.join(" · ")}`)
      ),
      persons.length
        ? el("div", { class: "avatar-stack" }, ...persons.map((p) =>
            el("span", { class: "magnet", style: `background:${p.color}`, title: p.name },
              p.emoji || p.name[0])))
        : null
    ),

    countdownEvents.length
      ? el("div", { class: "countdown-strip" },
          ...countdownEvents.map((ev) =>
            el("div", { class: "countdown-pill" },
              el("span", { class: "countdown-days" }, String(ev.days)),
              el("span", { class: "countdown-unit" }, ev.days === 1 ? "Tag" : "Tage"),
              el("span", { class: "countdown-title" }, ev.title)
            )
          )
        )
      : null,

    el("div", { class: "card week-strip-card" },
      el("div", { class: "week-strip" }, ...weekDayNodes),
      el("div", { class: "week-legend" },
        el("span", {}, el("span", { class: "week-dot", style: "background:var(--accent)" }), "Termine"),
        el("span", {}, el("span", { class: "week-dot meal" }), "Essen"),
        el("span", {}, el("span", { class: "week-dot task" }), "Aufgaben")
      )
    ),

    el("section", { class: "pin-section" },
      el("div", { class: "pin-heading" },
        el("h2", {}, "Heute steht an"),
        el("button", {
          class: "pin-add",
          "aria-label": "Neuen Termin anlegen",
          onclick: () => openEventForm(null, persons),
        }, icon("plus", 15))
      ),
      calContent
    ),
    el("section", { class: "pin-section" },
      el("div", { class: "pin-heading" },
        el("h2", {}, "Noch zu tun"),
        el("button", {
          class: "pin-add",
          "aria-label": "Neue Aufgabe anlegen",
          onclick: () => openTaskForm(persons),
        }, icon("plus", 15))
      ),
      taskContent
    ),

    muellInfo
      ? el("div", { class: "muell-banner" },
          el("span", { class: "muell-icon" }, "🗑️"),
          el("div", { class: "muell-text" },
            el("span", { class: "muell-label" }, muellInfo.days === 0 ? "Heute" : "Morgen"),
            el("span", { class: "muell-what" }, muellInfo.what)
          )
        )
      : null,

    el("div", { class: "pin-notes" },
      el("div", { class: "pin-notes-row" },
        // Abendessen-Haftnotiz — tippt sich zur Essens-Woche
        el("div", { class: "sticky-note", onclick: () => switchTab("essen") },
          el("span", { class: "note-label" }, "Heute auf dem Tisch"),
          meal
            ? el("span", { class: "note-title" }, meal.title)
            : el("span", { class: "note-title note-title--empty" }, "Noch nichts geplant — antippen"),
          (meal?.url || meal?.ingredients?.length)
            ? el("span", { class: "note-actions" },
                meal.url
                  ? el("a", { href: meal.url, target: "_blank", class: "note-link",
                      onclick: (e) => e.stopPropagation() }, icon("external-link", 12), "Rezept")
                  : null,
                meal.ingredients?.length
                  ? el("button", { class: "note-link", onclick: async (e) => {
                      e.stopPropagation();
                      await ingredientsToList(meal);
                      render();
                    } }, icon("basket", 12), "Zutaten auf die Liste")
                  : null
              )
            : null
        ),
        // Einkaufs-Zettel
        el("div", { class: "kraft-note", onclick: () => switchTab("listen") },
          icon("shopping-cart", 18),
          el("span", { class: "note-strong" }, "Einkaufen"),
          el("span", { class: "note-sub" },
            openTotal
              ? (openTotal === 1 ? "1 Artikel offen" : `${openTotal} Artikel offen`)
              : "Alles besorgt")
        )
      ),
      // Schnellnotiz
      el("div", { class: "sticky-note sticky-note--memo" },
        el("span", { class: "note-label" }, "Schnellnotiz"),
        noteTA
      )
    )
  );
}

/* ---------- Kalender ---------- */

async function viewKalender() {
  showLoading();
  const today = new Date();
  const isAgenda = state.calView === "agenda";
  const base = new Date(today);
  if (!isAgenda) base.setDate(today.getDate() + (state.calOffset || 0));
  const endD = new Date(base);
  if (isAgenda) endD.setFullYear(endD.getFullYear() + state.agendaYears);
  else endD.setDate(endD.getDate() + 14);
  const start = isoDate(base);
  const end = isoDate(endD);

  let events, persons;
  try {
    [events, persons] = await Promise.all([
      api.get(`api/calendar/events?start=${start}T00:00:00&end=${end}T23:59:59`),
      api.get("api/persons").catch(() => []),
    ]);
    if (!Array.isArray(events)) throw new Error(events?.detail || events?.error || "Fehler");
  } catch (e) {
    setMain(
      el("h1", {}, "Kalender"),
      el("div", { class: "card" },
        emptyState("wifi-off", "Kalender nicht verbunden",
          "HA-Verbindung prüfen — Kalender aktivierst du in den Einstellungen.")
      )
    );
    return;
  }

  const viewToggle = el("div", { class: "calendar-view-toggle", role: "group", "aria-label": "Kalenderansicht" },
    el("button", {
      class: "calendar-view-btn" + (!isAgenda ? " active" : ""),
      onclick: () => { state.calView = "range"; render(); },
    }, icon("calendar", 15), "14 Tage"),
    el("button", {
      class: "calendar-view-btn" + (isAgenda ? " active" : ""),
      onclick: () => { state.calView = "agenda"; render(); },
    }, icon("notes", 15), "Terminübersicht")
  );

  if (isAgenda) {
    const groupedAgenda = {};
    for (const ev of events) {
      // Mehrtägige Termine, die schon laufen, gehören an den heutigen Beginn der Übersicht.
      const startDay = (ev.start || "").slice(0, 10);
      if (!startDay) continue;
      const day = startDay < isoDate(today) ? isoDate(today) : startDay;
      if (day) (groupedAgenda[day] = groupedAgenda[day] || []).push(ev);
    }
    const agendaDays = Object.entries(groupedAgenda).map(([day, dayEvents]) => {
      const date = new Date(day + "T12:00:00");
      const label = date.toLocaleDateString("de-DE", { weekday: "long", day: "numeric", month: "long", year: "numeric" });
      return el("section", { class: "agenda-day" },
        el("h2", { class: "agenda-date" + (day === isoDate(today) ? " today" : "") }, label),
        ...dayEvents.map((ev) => {
          const time = ev.all_day ? "Ganztägig" : fmtTime(ev.start);
          return el("div", {
            class: "cal-event agenda-event",
            style: `--pc:${eventColor(ev)}`,
            onclick: () => openEventForm(ev, persons),
          },
            el("span", { class: "cal-event-title" }, ev.summary),
            el("span", { class: "event-meta" }, ev.calendar),
            el("span", { class: "cal-event-time" }, time),
            el("button", {
              class: "del-btn",
              onclick: async (e) => {
                e.stopPropagation();
                if (!confirm(`"${ev.summary}" löschen?`)) return;
                await api.post("api/calendar/events/delete", { entity_id: ev.entity_id, uid: ev.uid });
                render();
              },
            }, icon("x", 15))
          );
        })
      );
    });
    setMain(
      el("h1", {}, "Kalender"),
      viewToggle,
      el("button", { class: "btn-soft", style: "margin-bottom:16px", onclick: () => openEventForm(null, persons) },
        icon("plus", 16), "Neuer Termin"),
      agendaDays.length
        ? el("div", { class: "agenda-list" },
            ...agendaDays,
            el("button", {
              class: "btn-ghost agenda-more",
              onclick: () => { state.agendaYears += 1; render(); },
            }, "Weitere 12 Monate laden")
          )
        : emptyState("calendar-check", "Keine kommenden Termine", "In den nächsten 12 Monaten ist nichts eingetragen.")
    );
    return;
  }

  // Termine über alle Tage verteilen, die sie umspannen (mehrtägige zählen an jedem Tag)
  const winStart = start;             // erster sichtbarer Tag
  const winEnd = addDays(start, 13);  // letzter sichtbarer Tag (14-Tage-Fenster)
  const grouped = {};
  for (const ev of events) {
    const s = (ev.start || "").slice(0, 10);
    if (!s) continue;
    let last = (ev.end || s).slice(0, 10);
    if (ev.all_day) last = addDays(last, -1);  // Ganztags-Ende ist exklusiv
    else if ((ev.end || "").slice(11, 16) === "00:00" && last > s) {
      last = addDays(last, -1);                // Ende exakt Mitternacht zählt nicht in den Folgetag
    }
    if (last < s) last = s;
    let d = s < winStart ? winStart : s;
    const stop = last > winEnd ? winEnd : last;
    for (let guard = 0; d <= stop && guard < 14; d = addDays(d, 1), guard++) {
      (grouped[d] = grouped[d] || []).push(ev);
    }
  }

  const dayEls = [];
  for (let i = 0; i < 14; i++) {
    const d = new Date(base); d.setDate(base.getDate() + i);
    const day = isoDate(d);
    const isToday = isoDate(d) === isoDate(today);
    const label = d.toLocaleDateString("de-DE", { weekday: "short", day: "numeric", month: "short" });
    const dayEvs = grouped[day] || [];

    const evEls = dayEvs.map((ev) => {
      const isStart = (ev.start || "").slice(0, 10) === day;
      const time = isStart ? fmtTime(ev.start) : "";
      const pips = (ev.persons || []).map((p) =>
        el("span", { class: "person-pip person-pip--sm", style: `background:${p.color}`, title: p.name },
          p.emoji || p.name[0])
      );
      return el("div", {
        class: "cal-event" + (isStart ? "" : " cal-event--cont"),
        style: `--pc:${eventColor(ev)}`,
        onclick: () => openEventForm(ev, persons),
      },
        el("span", { class: "cal-event-title" }, ev.summary),
        ...pips,
        time ? el("span", { class: "cal-event-time" }, time) : null,
        el("button", {
          class: "del-btn",
          onclick: async (e) => {
            e.stopPropagation();
            if (!confirm(`"${ev.summary}" löschen?`)) return;
            await api.post("api/calendar/events/delete", { entity_id: ev.entity_id, uid: ev.uid });
            render();
          },
        }, icon("x", 15))
      );
    });

    dayEls.push(
      el("div", { class: "cal-day" + (dayEvs.length ? " has-events" : "") },
        el("div", { class: "cal-day-header" + (isToday ? " today" : "") }, label),
        ...evEls
      )
    );
  }

  const lastDay = new Date(endD); lastDay.setDate(endD.getDate() - 1);
  const rangeLabel = `${base.toLocaleDateString("de-DE", { day: "numeric", month: "short" })} – ${lastDay.toLocaleDateString("de-DE", { day: "numeric", month: "short" })}`;

  const navRow = el("div", { class: "cal-nav" },
    el("button", { class: "cal-nav-btn", onclick: () => { state.calOffset = (state.calOffset || 0) - 14; render(); } }, icon("chevron-left", 16)),
    el("button", { class: "cal-nav-date", onclick: () => openMonthPicker(base) }, rangeLabel),
    el("button", { class: "cal-nav-btn", onclick: () => { state.calOffset = (state.calOffset || 0) + 14; render(); } }, icon("chevron-right", 16)),
    state.calOffset ? el("button", { class: "cal-nav-today", onclick: () => { state.calOffset = 0; render(); } }, "Heute") : null
  );

  setMain(
    el("h1", {}, "Kalender"),
    viewToggle,
    navRow,
    el("button", { class: "btn-soft", style: "margin-bottom:16px", onclick: () => openEventForm(null, persons) },
      icon("plus", 16), "Neuer Termin"),
    ...dayEls
  );
}

function openEventForm(existing, persons = []) {
  const isEdit = !!existing;
  const overlay = el("div", { class: "modal-overlay", onclick: (e) => { if (e.target === overlay) overlay.remove(); } });

  const titleInput = el("input", { type: "text", placeholder: "Titel", class: "form-input",
    value: existing?.summary || "", autocomplete: "off" });
  const dateInput  = el("input", { type: "date", class: "form-input",
    value: existing ? (existing.start || "").slice(0, 10) : isoDate() });
  // Enddatum wird dem Nutzer inklusiv gezeigt; HA speichert exklusiv (= +1 Tag)
  let endInitial;
  if (existing?.all_day && existing.start && existing.end) {
    endInitial = addDays((existing.end || "").slice(0, 10), -1);
  } else {
    endInitial = existing ? (existing.start || "").slice(0, 10) : isoDate();
  }
  const endDateInput = el("input", { type: "date", class: "form-input", value: endInitial });
  const timeStart  = el("input", { type: "time", class: "form-input",
    value: existing && !existing.all_day ? fmtTime(existing.start) : "09:00" });
  const timeEnd    = el("input", { type: "time", class: "form-input",
    value: existing && !existing.all_day ? fmtTime(existing.end) : "10:00" });
  const allDayCb   = el("input", { type: "checkbox" });
  allDayCb.checked = !!existing?.all_day;

  const startLabel = el("p", { class: "form-field-label" }, "Datum");
  const startField = el("div", {}, startLabel, dateInput);
  const endLabel   = el("p", { class: "form-field-label" }, "Bis");
  const endField   = el("div", {}, endLabel, endDateInput);
  const calSel     = el("select", { class: "form-input" }, el("option", { value: "" }, "Lädt …"));
  const errMsg     = el("p", { class: "err", style: "display:none" });

  const existingPersonIds = new Set((existing?.persons || []).map((p) => p.id));
  const personChecks = persons.map((p) => {
    const cb = el("input", { type: "checkbox", "data-pid": String(p.id) });
    cb.checked = existingPersonIds.has(p.id);
    return el("label", { class: "person-check-row" },
      cb,
      el("span", { class: "person-pip", style: `background:${p.color}` }, p.emoji || p.name[0]),
      el("span", {}, p.name)
    );
  });

  api.get("api/calendar/calendars").then((cals) => {
    const active = Array.isArray(cals) ? cals.filter((c) => c.enabled) : [];
    const opts = active.map((c) => el("option", { value: c.entity_id }, c.name));
    calSel.replaceChildren(
      el("option", { value: "" }, opts.length ? "— Kalender wählen —" : "Keine Kalender aktiviert"),
      ...opts
    );
    if (active.length === 1 && !isEdit) calSel.value = active[0].entity_id;
    if (isEdit) {
      if (![...calSel.options].some((o) => o.value === existing.entity_id)) {
        calSel.appendChild(el("option", { value: existing.entity_id }, existing.calendar || existing.entity_id));
      }
      calSel.value = existing.entity_id;
      calSel.disabled = true;
    }
  });

  function syncTimeVisibility() {
    const allDay = allDayCb.checked;
    timeStart.style.display = allDay ? "none" : "";
    timeEnd.style.display   = allDay ? "none" : "";
    endField.style.display  = allDay ? "" : "none";
    startLabel.textContent  = allDay ? "Von" : "Datum";
    // Enddatum nie vor Startdatum
    if (allDay && endDateInput.value < dateInput.value) endDateInput.value = dateInput.value;
  }
  allDayCb.addEventListener("change", syncTimeVisibility);
  dateInput.addEventListener("change", () => {
    if (allDayCb.checked && endDateInput.value < dateInput.value) endDateInput.value = dateInput.value;
  });
  syncTimeVisibility();

  const card = el("div", { class: "modal-card" },
    el("div", { class: "modal-handle" }),
    el("h2", { style: "margin-bottom:14px" }, isEdit ? "Termin bearbeiten" : "Neuer Termin"),
    titleInput,
    el("label", { class: "form-label" }, allDayCb, " Ganztägig"),
    startField, endField,
    timeStart, timeEnd, calSel,
    persons.length ? el("p", { class: "form-field-label" }, "Personen") : null,
    ...personChecks,
    errMsg,
    el("div", { class: "form-btns" },
      el("button", { class: "btn-ghost", onclick: () => overlay.remove() }, "Abbrechen"),
      el("button", { class: "btn-soft", onclick: async () => {
        const title = titleInput.value.trim();
        const calId = calSel.value;
        if (!title) { errMsg.textContent = "Titel fehlt"; errMsg.style.display = ""; return; }
        if (!calId) { errMsg.textContent = "Kalender wählen"; errMsg.style.display = ""; return; }
        const allDay = allDayCb.checked;
        let evStart, evEnd;
        if (allDay) {
          evStart = dateInput.value;
          if (endDateInput.value < evStart) {
            errMsg.textContent = "Enddatum liegt vor dem Startdatum";
            errMsg.style.display = "";
            return;
          }
          // UI-Enddatum ist inklusiv → HA erwartet exklusiv (+1 Tag)
          evEnd = addDays(endDateInput.value, 1);
        } else {
          evStart = `${dateInput.value}T${timeStart.value}:00`;
          evEnd   = `${dateInput.value}T${timeEnd.value}:00`;
        }
        const person_ids = [...card.querySelectorAll("input[data-pid]")]
          .filter((cb) => cb.checked)
          .map((cb) => Number(cb.dataset.pid));
        const body = {
          entity_id: calId, summary: title, start: evStart, end: evEnd, all_day: allDay,
          description: existing?.description || null,
          person_ids,
        };
        const res = isEdit
          ? await api.post("api/calendar/events/update", {
              ...body, uid: existing.uid, recurrence_id: existing.recurrence_id || null,
            })
          : await api.post("api/calendar/events", body);
        if (res && (res.detail || res.error)) {
          errMsg.textContent = res.detail || res.error;
          errMsg.style.display = "";
          return;
        }
        overlay.remove();
        render();
      }}, "Speichern")
    )
  );
  overlay.appendChild(card);
  document.body.appendChild(overlay);
  setTimeout(() => titleInput.focus(), 50);
}

function openMonthPicker(activeBase) {
  document.querySelector(".month-picker-overlay")?.remove();
  const today = new Date();
  let pickerDate = new Date(activeBase.getFullYear(), activeBase.getMonth(), 1);

  const overlay = el("div", { class: "month-picker-overlay", onclick: (e) => { if (e.target === overlay) overlay.remove(); } });
  const pickerEl = el("div", { class: "month-picker" });
  overlay.appendChild(pickerEl);
  document.body.appendChild(overlay);

  let showMonthOverview = true;

  function refresh() {
    const year = pickerDate.getFullYear();
    const month = pickerDate.getMonth();
    const monthLabel = pickerDate.toLocaleDateString("de-DE", { month: "long", year: "numeric" });
    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);
    let startDow = firstDay.getDay(); // 0=Sun
    startDow = startDow === 0 ? 6 : startDow - 1; // convert to Mon=0

    if (showMonthOverview) {
      const months = Array.from({ length: 12 }, (_, index) => {
        const isActive = index === activeBase.getMonth() && year === activeBase.getFullYear();
        const isCurrent = index === today.getMonth() && year === today.getFullYear();
        return el("button", {
          class: "mp-month" + (isActive ? " mp-month-active" : "") + (isCurrent ? " mp-month-current" : ""),
          onclick: () => {
            pickerDate = new Date(year, index, 1);
            showMonthOverview = false;
            refresh();
          },
        }, new Date(year, index, 1).toLocaleDateString("de-DE", { month: "short" }));
      });
      pickerEl.replaceChildren(
        el("div", { class: "mp-head" },
          el("button", { class: "mp-nav", "aria-label": "Vorheriges Jahr", onclick: (e) => { e.stopPropagation(); pickerDate = new Date(year - 1, month, 1); refresh(); } }, icon("chevron-left", 15)),
          el("span", { class: "mp-label" }, String(year)),
          el("button", { class: "mp-nav", "aria-label": "Nächstes Jahr", onclick: (e) => { e.stopPropagation(); pickerDate = new Date(year + 1, month, 1); refresh(); } }, icon("chevron-right", 15))
        ),
        el("div", { class: "mp-month-grid" }, ...months)
      );
      return;
    }

    const cells = [];
    ["Mo","Di","Mi","Do","Fr","Sa","So"].forEach((d) =>
      cells.push(el("span", { class: "mp-dow" }, d))
    );
    for (let i = 0; i < startDow; i++) cells.push(el("span", { class: "mp-day mp-other" }));

    const activeStart = isoDate(activeBase);
    const activeEndD = new Date(activeBase); activeEndD.setDate(activeBase.getDate() + 13);
    const activeEnd = isoDate(activeEndD);

    for (let d = 1; d <= lastDay.getDate(); d++) {
      const date = new Date(year, month, d);
      const ds = isoDate(date);
      const isToday = ds === isoDate(today);
      const inRange = ds >= activeStart && ds <= activeEnd;
      cells.push(el("span", {
        class: "mp-day" + (isToday ? " mp-today" : "") + (inRange ? " mp-range" : ""),
        onclick: () => {
          const diff = Math.round((date.getTime() - new Date(isoDate(today) + "T00:00:00").getTime()) / 86400000);
          state.calOffset = diff;
          overlay.remove();
          render();
        },
      }, String(d)));
    }
    const rem = (startDow + lastDay.getDate()) % 7;
    if (rem > 0) for (let i = 0; i < (7 - rem); i++) cells.push(el("span", { class: "mp-day mp-other" }));

    pickerEl.replaceChildren(
      el("div", { class: "mp-head" },
        el("button", { class: "mp-nav", onclick: (e) => { e.stopPropagation(); pickerDate = new Date(year, month - 1, 1); refresh(); } }, icon("chevron-left", 15)),
        el("button", { class: "mp-label mp-label-btn", onclick: () => { showMonthOverview = true; refresh(); } }, monthLabel),
        el("button", { class: "mp-nav", onclick: (e) => { e.stopPropagation(); pickerDate = new Date(year, month + 1, 1); refresh(); } }, icon("chevron-right", 15))
      ),
      el("div", { class: "mp-grid" }, ...cells)
    );
  }
  refresh();
}

/* ---------- Aufgaben ---------- */

async function viewAufgaben() {
  let fetchOk = true;
  const [tasks, persons] = await Promise.all([
    api.get("api/tasks").catch(() => { fetchOk = false; return []; }),
    api.get("api/persons").catch(() => []),
  ]);
  const personMap = Object.fromEntries(persons.map((p) => [p.id, p]));

  // Personen-Filter: nur Aufgaben der gewählten Person
  if (state.taskFilter != null && !personMap[state.taskFilter]) state.taskFilter = null;
  const matchesFilter = (t) =>
    state.taskFilter == null || (t.person_ids || []).includes(state.taskFilter);
  const open = tasks.filter((t) => !t.done && matchesFilter(t));
  const done = tasks.filter((t) => t.done && matchesFilter(t));

  function chip(label, pid, color) {
    const active = state.taskFilter === pid;
    return el("button", {
      class: "chip" + (active ? " active" : ""),
      style: active && color ? `background:${color};border-color:${color}` : "",
      onclick: () => { state.taskFilter = pid; render(); },
    },
      color ? el("span", { class: "chip-dot", style: `background:${active ? "#fff" : color}` }) : null,
      label
    );
  }
  const chipRow = persons.length
    ? el("div", { class: "chip-row" },
        chip("Alle", null, null),
        ...persons.map((p) => chip(p.name, p.id, p.color)))
    : null;
  const filterName = state.taskFilter != null ? personMap[state.taskFilter]?.name : null;

  function taskRow(t) {
    const pips = (t.person_ids || []).map((pid) => {
      const p = personMap[pid];
      return p ? el("span", { class: "person-pip", style: `background:${p.color}`, title: p.name },
        p.emoji || p.name[0]) : null;
    });
    const recurBadge = t.recurrence && t.recurrence !== "none"
      ? el("span", { class: "recur-badge" }, icon("repeat", 11), RECUR_LABEL[t.recurrence]) : null;
    const dueLbl = t.due_date
      ? el("span", {
          class: "due-lbl" + (!t.done && t.due_date < isoDate() ? " overdue" : ""),
        }, fmtDate(t.due_date))
      : null;

    return el("li", { class: "task-item task-item-editable" + (t.done ? " done" : ""), onclick: () => openTaskForm(persons, t) },
      el("button", {
        class: "check",
        onclick: (e) => {
          e.stopPropagation();
          api.patch(`api/tasks/${t.id}`, { done: !t.done }).then(render);
        },
      }, t.done ? icon("check", 14) : ""),
      el("div", { class: "task-body" },
        el("span", { class: "task-title" }, t.title),
        el("div", { class: "task-meta" }, ...pips, dueLbl, recurBadge)
      ),
      taskShiftButton(t),
      el("button", {
        class: "del-btn",
        onclick: async (e) => {
          e.stopPropagation();
          if (t.template_id) {
            const series = confirm("Auch alle künftigen Wiederholungen löschen?");
            await api.del(`api/tasks/${t.id}?series=${series}`);
          } else {
            await api.del(`api/tasks/${t.id}`);
          }
          render();
        },
      }, icon("x", 15))
    );
  }

  setMain(
    el("h1", {}, "Aufgaben"),
    el("button", { class: "btn-soft", style: "margin-bottom:16px",
      onclick: () => openTaskForm(persons) }, icon("plus", 16), "Neue Aufgabe"),
    chipRow,
    fetchOk
      ? (open.length
          ? el("ul", { class: "task-list" }, ...open.map(taskRow))
          : emptyState("confetti",
              filterName ? `Nichts zu tun für ${filterName}` : "Alles erledigt!",
              "Keine offenen Aufgaben"))
      : emptyState("wifi-off", "Backend nicht erreichbar", "Bitte App neu laden"),
    done.length ? el("p", { class: "section-label" }, "Erledigt") : null,
    done.length ? el("ul", { class: "task-list" }, ...done.map(taskRow)) : null
  );
}

function openTaskForm(persons, existing = null) {
  const isEdit = !!existing;
  const overlay = el("div", { class: "modal-overlay", onclick: (e) => { if (e.target === overlay) overlay.remove(); } });

  const titleInput = el("input", { type: "text", placeholder: "Aufgabe", class: "form-input", autocomplete: "off", value: existing?.title || "" });
  const dateInput  = el("input", { type: "date", class: "form-input", value: existing?.due_date || "" });
  const recurSel   = el("select", { class: "form-input" },
    el("option", { value: "none" }, "Keine Wiederholung"),
    el("option", { value: "daily" }, "Täglich"),
    el("option", { value: "weekly" }, "Wöchentlich"),
    el("option", { value: "monthly" }, "Monatlich"),
  );
  recurSel.value = existing?.recurrence || "none";
  recurSel.disabled = isEdit;
  const existingPersonIds = new Set(existing?.person_ids || []);
  const personChecks = persons.map((p) => {
    const checkbox = el("input", { type: "checkbox", value: String(p.id) });
    checkbox.checked = existingPersonIds.has(p.id);
    return el("label", { class: "person-check-row" },
      checkbox,
      el("span", { class: "person-pip", style: `background:${p.color}` }, p.emoji || p.name[0]),
      " " + p.name
    );
  });
  const errMsg = el("p", { class: "err", style: "display:none" });

  overlay.appendChild(el("div", { class: "modal-card" },
    el("div", { class: "modal-handle" }),
    el("h2", { style: "margin-bottom:14px" }, isEdit ? "Aufgabe bearbeiten" : "Neue Aufgabe"),
    titleInput,
    el("p", { class: "form-field-label" }, "Fälligkeitsdatum"),
    dateInput,
    el("p", { class: "form-field-label" }, "Wiederholung"),
    recurSel,
    persons.length ? el("p", { class: "form-field-label" }, "Zugewiesen an") : null,
    ...personChecks,
    errMsg,
    el("div", { class: "form-btns" },
      el("button", { class: "btn-ghost", onclick: () => overlay.remove() }, "Abbrechen"),
      el("button", { class: "btn-soft", onclick: async () => {
        const title = titleInput.value.trim();
        if (!title) { errMsg.textContent = "Titel fehlt"; errMsg.style.display = ""; return; }
        const person_ids = [...overlay.querySelectorAll("input[type=checkbox]:checked")]
          .map((cb) => parseInt(cb.value));
        const res = isEdit
          ? await api.patch(`api/tasks/${existing.id}`, { title, person_ids, due_date: dateInput.value || null })
          : await api.post("api/tasks", { title, person_ids, due_date: dateInput.value || null, recurrence: recurSel.value });
        if (res && res.detail) { errMsg.textContent = res.detail; errMsg.style.display = ""; return; }
        overlay.remove();
        render();
      }}, "Speichern")
    )
  ));
  document.body.appendChild(overlay);
  setTimeout(() => titleInput.focus(), 50);
}

/* ---------- Listen ---------- */

async function viewListen() {
  if (state.listId) return viewListDetail();
  const lists = await api.get("api/shopping/lists").catch(() => []);
  const rows = lists.map((l) =>
    el("div", { class: "list-row", onclick: () => { state.listId = l.id; state.listName = l.name; render(); } },
      el("span", { class: "ico" }, l.icon || icon("notes", 22)),
      el("span", { class: "name" }, l.name),
      l.open_count ? el("span", { class: "badge" }, String(l.open_count)) : null
    )
  );
  setMain(
    el("h1", {}, "Listen"),
    el("p", { class: "subtitle" }, "Einkaufs- und andere Listen"),
    ...rows,
    el("button", { class: "btn-ghost", onclick: addList }, icon("plus", 15), "Neue Liste")
  );
}

async function addList() {
  const name = prompt("Name der neuen Liste:");
  if (!name || !name.trim()) return;
  await api.post("api/shopping/lists", { name: name.trim() });
  render();
}

async function viewListDetail() {
  const items = await api.get(`api/shopping/lists/${state.listId}/items`);
  const open = items.filter((i) => !i.checked);
  const done = items.filter((i) => i.checked);

  const input  = el("input", { type: "text", placeholder: "Artikel hinzufügen …", autocomplete: "off", enterkeyhint: "done" });
  const sugBox = el("div", { class: "suggestions", style: "display:none" });

  async function submit(name) {
    const val = (name || input.value).trim();
    if (!val) return;
    input.value = "";
    sugBox.style.display = "none";
    await api.post(`api/shopping/lists/${state.listId}/items`, { name: val });
    render().then(() => document.querySelector(".add-row input")?.focus());
  }

  input.addEventListener("keydown", (e) => { if (e.key === "Enter") submit(); });
  input.addEventListener("input", async () => {
    const q = input.value.trim();
    if (q.length < 1) { sugBox.style.display = "none"; return; }
    const sugs = await api.get(`api/shopping/suggest?q=${encodeURIComponent(q)}`);
    sugBox.replaceChildren(...sugs
      .filter((s) => s.name.toLowerCase() !== q.toLowerCase())
      .map((s) => el("div", { onclick: () => submit(s.name) }, s.name)));
    sugBox.style.display = sugBox.children.length ? "block" : "none";
  });

  const itemLi = (i) =>
    el("li", { class: i.checked ? "checked" : "" },
      el("button", {
        class: "check",
        onclick: () => api.patch(`api/shopping/items/${i.id}`, { checked: !i.checked }).then(render),
      }, i.checked ? icon("check", 14) : ""),
      el("span", { class: "label" }, i.name),
      i.checked ? null : el("button", {
        class: "cat-tag",
        title: "Kategorie wählen",
        "aria-label": `Kategorie für ${i.name} wählen`,
        onclick: () => openCategoryPicker(i),
      }, i.category ? i.category : icon("tag", 12)),
      el("button", {
        class: "del",
        onclick: () => api.del(`api/shopping/items/${i.id}`).then(render),
      }, icon("x", 15))
    );

  // Offene Artikel nach Kategorie gruppieren (Supermarkt-Reihenfolge);
  // ohne vergebene Kategorien bleibt die Liste flach wie bisher.
  const catIndex = (c) => {
    const i = CATEGORIES.indexOf(c);
    return i === -1 ? CATEGORIES.length - 0.5 : i;
  };
  let openContent;
  if (!open.length) {
    openContent = emptyState("basket", "Nichts auf der Liste", "Alles eingekauft");
  } else if (!open.some((i) => i.category)) {
    openContent = el("ul", { class: "items" }, ...open.map(itemLi));
  } else {
    const groups = {};
    open.forEach((i) => {
      const c = i.category || "Sonstiges";
      (groups[c] = groups[c] || []).push(i);
    });
    const keys = Object.keys(groups).sort((a, b) => catIndex(a) - catIndex(b) || a.localeCompare(b));
    openContent = el("div", {}, ...keys.flatMap((c) => [
      el("p", { class: "section-label", style: "margin-top:12px" }, c),
      el("ul", { class: "items" }, ...groups[c].map(itemLi)),
    ]));
  }

  setMain(
    el("div", { class: "topbar" },
      el("button", { class: "back", onclick: () => { state.listId = null; render(); } }, icon("chevron-left", 24)),
      el("h1", {}, state.listName)
    ),
    el("div", { class: "add-row" }, input, el("button", { class: "add", onclick: () => submit() }, icon("plus", 20)), sugBox),
    openContent,
    done.length ? el("p", { class: "section-label" }, "Erledigt") : null,
    done.length ? el("ul", { class: "items" }, ...done.map(itemLi)) : null,
    done.length
      ? el("button", {
          class: "btn-soft",
          onclick: () => api.post(`api/shopping/lists/${state.listId}/clear-checked`).then(render),
        }, "Erledigte löschen")
      : null
  );
}

function openCategoryPicker(item) {
  const overlay = el("div", { class: "modal-overlay", onclick: (e) => { if (e.target === overlay) overlay.remove(); } });

  const row = (label, value) => {
    const current = (item.category || null) === value;
    return el("label", {
      class: "person-check-row cat-row",
      onclick: async () => {
        await api.patch(`api/shopping/items/${item.id}`, { category: value ?? "" });
        overlay.remove();
        render();
      },
    },
      el("span", { style: current ? "font-weight:800" : "" }, label),
      current ? icon("check", 16) : null
    );
  };

  overlay.appendChild(el("div", { class: "modal-card" },
    el("div", { class: "modal-handle" }),
    el("h2", { style: "margin-bottom:2px" }, item.name),
    el("p", { class: "form-field-label", style: "margin-bottom:8px" }, "Kategorie"),
    ...CATEGORIES.map((c) => row(c, c)),
    row("Keine Kategorie", null)
  ));
  document.body.appendChild(overlay);
}

/* ---------- Essen ---------- */

async function viewEssen() {
  const mon = weekMonday();
  const sun = new Date(mon); sun.setDate(mon.getDate() + 6);
  const start = isoDate(mon);
  const end   = isoDate(sun);
  const today = isoDate();

  const meals = await api.get(`api/meals?start=${start}&end=${end}`).catch(() => []);
  const mealMap = Object.fromEntries(meals.map((m) => [m.date, m]));

  const dayRows = [];
  for (let i = 0; i < 7; i++) {
    const d = new Date(mon); d.setDate(mon.getDate() + i);
    const day  = isoDate(d);
    const meal = mealMap[day];
    const dow  = d.getDay(); // 0=Sun
    const dayLabel  = DAYS_DE[dow === 0 ? 6 : dow - 1];
    const dateLabel = d.toLocaleDateString("de-DE", { day: "numeric", month: "numeric" });

    dayRows.push(el("div", {
      class: "meal-row" + (day === today ? " today" : ""),
      onclick: () => openMealForm(day, meal),
    },
      el("div", { class: "meal-day" },
        el("span", { class: "meal-day-name" }, dayLabel),
        el("span", { class: "meal-day-date" }, dateLabel)
      ),
      meal
        ? el("div", { class: "meal-content" },
            el("span", { class: "meal-title" }, meal.title),
            meal.ingredients?.length
              ? el("button", {
                  class: "ing-btn",
                  title: "Zutaten auf die Einkaufsliste setzen",
                  onclick: async (e) => { e.stopPropagation(); await ingredientsToList(meal); },
                }, icon("basket", 13), String(meal.ingredients.length))
              : null,
            meal.url
              ? el("a", { href: meal.url, target: "_blank", class: "meal-ext",
                  onclick: (e) => e.stopPropagation() }, icon("external-link", 15))
              : null
          )
        : el("span", { class: "meal-empty" }, "+ Hinzufügen"),
      meal
        ? el("button", {
            class: "del-btn",
            onclick: async (e) => { e.stopPropagation(); await api.del(`api/meals/${day}`); render(); },
          }, icon("x", 15))
        : null
    ));
  }

  setMain(
    el("h1", {}, "Essensplan"),
    el("p", { class: "subtitle" }, "Diese Woche · Abendessen"),
    ...dayRows,
    el("button", { class: "btn-ghost", style: "margin-top:8px",
      onclick: async () => {
        const res = await api.post("api/meals/copy-last-week");
        if (res.copied === 0) alert("Letzte Woche war leer oder diese Woche ist bereits vollständig.");
        render();
      }
    }, icon("arrow-back-up", 15), "Letzte Woche übernehmen")
  );
}

function openMealForm(day, existing) {
  const overlay = el("div", { class: "modal-overlay", onclick: (e) => { if (e.target === overlay) overlay.remove(); } });
  const d = new Date(day + "T12:00:00");
  const label = d.toLocaleDateString("de-DE", { weekday: "long", day: "numeric", month: "long" });

  const titleInput = el("input", { type: "text", placeholder: "Gericht", class: "form-input",
    value: existing?.title || "", autocomplete: "off" });
  const noteInput  = el("input", { type: "text", placeholder: "Notiz (optional)", class: "form-input",
    value: existing?.note || "" });
  const urlInput   = el("input", { type: "url", placeholder: "Link (optional)", class: "form-input",
    value: existing?.url || "" });
  const ingArea    = el("textarea", { class: "form-input", rows: "4",
    placeholder: "Zutaten — eine pro Zeile (optional)" });
  ingArea.value = (existing?.ingredients || []).join("\n");
  const ingHint = el("p", { class: "setting-hint", style: "display:none" },
    "Zutaten vom letzten Mal übernommen");
  const errMsg = el("p", { class: "err", style: "display:none" });

  // Gespeicherte Zutaten desselben Gerichts wiederverwenden
  titleInput.addEventListener("change", async () => {
    const t = titleInput.value.trim();
    if (!t || ingArea.value.trim()) return;
    const r = await api.get(`api/meals/dish-ingredients?title=${encodeURIComponent(t)}`).catch(() => null);
    if (r?.ingredients?.length) {
      ingArea.value = r.ingredients.join("\n");
      ingHint.style.display = "";
    }
  });

  overlay.appendChild(el("div", { class: "modal-card" },
    el("div", { class: "modal-handle" }),
    el("h2", { style: "margin-bottom:4px" }, label),
    el("p", { class: "form-field-label", style: "margin-bottom:12px" }, "Abendessen"),
    titleInput, noteInput, urlInput,
    el("p", { class: "form-field-label" }, "Zutaten"),
    ingArea, ingHint, errMsg,
    el("div", { class: "form-btns" },
      el("button", { class: "btn-ghost", onclick: () => overlay.remove() }, "Abbrechen"),
      el("button", { class: "btn-soft", onclick: async () => {
        const title = titleInput.value.trim();
        if (!title) { errMsg.textContent = "Titel fehlt"; errMsg.style.display = ""; return; }
        await api.put(`api/meals/${day}`, {
          title,
          note: noteInput.value.trim() || null,
          url:  urlInput.value.trim() || null,
          ingredients: ingArea.value.split("\n").map((s) => s.trim()).filter(Boolean),
        });
        overlay.remove();
        render();
      }}, "Speichern")
    )
  ));
  document.body.appendChild(overlay);
  setTimeout(() => titleInput.focus(), 50);
}

/* ---------- Einstellungen ---------- */

function mkToggle(checked, onchange) {
  const cb = Object.assign(document.createElement("input"), { type: "checkbox", checked });
  cb.addEventListener("change", () => onchange(cb.checked));
  const track = document.createElement("span");
  track.className = "toggle-track";
  const label = document.createElement("label");
  label.className = "toggle";
  label.append(cb, track);
  return { el: label, input: cb };
}

async function viewEinstellungen() {
  const [persons, calsRaw, notifSettings, notifSvcRaw, appSettings] = await Promise.all([
    api.get("api/persons").catch(() => []),
    api.get("api/calendar/calendars").catch(() => ({ error: "Nicht erreichbar" })),
    api.get("api/notifications/settings").catch(() => null),
    api.get("api/notifications/services").catch(() => ({ services: [] })),
    api.get("api/settings").catch(() => ({})),
  ]);
  const calendars = Array.isArray(calsRaw) ? calsRaw : [];
  const haError   = Array.isArray(calsRaw) ? null : (calsRaw?.detail || calsRaw?.error || "Nicht erreichbar");
  const notifSvc  = notifSvcRaw?.services || [];
  const ns = notifSettings || {
    enabled: false, notify_services: [], task_reminder_time: "08:00", event_lead_minutes: 30,
  };
  if (!Array.isArray(ns.notify_services)) ns.notify_services = [];

  function personCard(p) {
    return el("div", { class: "person-card" },
      el("span", { class: "person-avatar", style: `background:${p.color}` }, p.emoji || p.name[0]),
      el("div", { class: "person-info" },
        el("strong", {}, p.name)
      ),
      el("button", { class: "btn-icon", onclick: () => openPersonForm(p) }, icon("pencil", 16)),
      el("button", {
        class: "btn-icon del",
        onclick: async () => {
          if (!confirm(`"${p.name}" löschen?`)) return;
          await api.del(`api/persons/${p.id}`);
          render();
        },
      }, icon("x", 16))
    );
  }

  // ── Kalender-Karte ────────────────────────────────────────────────────────

  function calendarRow(c) {
    const colorInput = el("input", { type: "color", class: "cal-color", value: c.color,
      onchange: (e) => api.patch(`api/calendar/calendars/${c.entity_id}`, { color: e.target.value }) });
    const toggle = mkToggle(c.enabled, (on) =>
      api.patch(`api/calendar/calendars/${c.entity_id}`, { enabled: on }));
    return el("div", { class: "cal-row" },
      colorInput,
      el("div", { class: "cal-info" },
        el("strong", {}, c.name),
        el("span", { class: "muted cal-entity" }, c.entity_id)
      ),
      toggle.el
    );
  }

  const calCard = el("div", { class: "card" },
    el("h2", {}, icon("calendar", 17), "Kalender"),
    el("p", { class: "setting-hint", style: "margin-bottom:10px" },
      "Welche HA-Kalender in der App angezeigt werden — mit eigener Farbe."),
    calendars.length
      ? el("div", { class: "cal-list" }, ...calendars.map(calendarRow))
      : el("p", { class: "muted", style: "font-size:0.85rem" },
          haError ? "Keine HA-Verbindung" : "Keine Kalender in HA gefunden — z. B. die Integration „Lokaler Kalender“ anlegen.")
  );

  // ── Benachrichtigungen-Karte ──────────────────────────────────────────────

  const enabledCb = Object.assign(document.createElement("input"), {
    type: "checkbox", checked: ns.enabled,
  });

  // Gespeicherte Services bleiben wählbar, auch wenn HA gerade offline ist
  const allServices = [...new Set([...notifSvc, ...ns.notify_services])];
  const svcWrap = el("div", { class: "svc-list" });
  if (allServices.length === 0) {
    svcWrap.appendChild(el("p", { class: "muted", style: "font-size:0.85rem" },
      haError ? "Keine HA-Verbindung" : "Keine Notify-Services gefunden"));
  } else {
    allServices.forEach((s) => {
      const cb = el("input", { type: "checkbox", value: s });
      cb.checked = ns.notify_services.includes(s);
      svcWrap.appendChild(el("label", { class: "person-check-row" }, cb, " " + s));
    });
  }

  const timeInput = Object.assign(document.createElement("input"), {
    type: "time", className: "form-input", value: ns.task_reminder_time,
  });

  const leadSelect = document.createElement("select");
  leadSelect.className = "form-input";
  [15, 30, 60].forEach((m) =>
    leadSelect.appendChild(
      new Option(`${m} Minuten`, String(m), false, m === ns.event_lead_minutes)
    )
  );

  const statusMsg = document.createElement("p");
  statusMsg.style.cssText = "font-size:0.85rem;min-height:1.2em;margin-top:6px";
  function setStatus(cls, text) {
    statusMsg.className = cls;
    statusMsg.textContent = text;
    setTimeout(() => { statusMsg.textContent = ""; }, 3000);
  }

  const toggleEl = document.createElement("label");
  toggleEl.className = "toggle";
  toggleEl.appendChild(enabledCb);
  const toggleTrack = document.createElement("span");
  toggleTrack.className = "toggle-track";
  toggleEl.appendChild(toggleTrack);

  const notifCard = el("div", { class: "card" },
    el("h2", {}, icon("bell", 17), "Benachrichtigungen"),
    el("div", { class: "setting-row" },
      el("div", {},
        el("div", { class: "setting-label" }, "Push-Erinnerungen"),
        el("div", { class: "setting-hint" }, "Über HA Companion App")
      ),
      toggleEl
    ),
    el("p", { class: "form-field-label", style: "margin-top:4px" }, "Geräte (Notify-Services)"),
    svcWrap,
    el("p", { class: "form-field-label", style: "margin-top:10px" }, "Aufgaben-Erinnerung um"),
    timeInput,
    el("p", { class: "form-field-label", style: "margin-top:10px" }, "Termin-Vorlaufzeit"),
    leadSelect,
    statusMsg,
    el("div", { class: "form-btns", style: "margin-top:16px" },
      el("button", { class: "btn-ghost", onclick: async () => {
        setStatus("muted", "Sende…");
        const r = await api.post("api/notifications/test", {}).catch(() => null);
        r?.ok
          ? setStatus("ok", "✓ Testbenachrichtigung gesendet")
          : setStatus("err", "✗ Fehler — Service konfiguriert?");
      }}, "Test senden"),
      el("button", { class: "btn-soft", onclick: async () => {
        setStatus("muted", "Speichern…");
        const r = await api.put("api/notifications/settings", {
          enabled: enabledCb.checked,
          notify_services: [...svcWrap.querySelectorAll("input:checked")].map((cb) => cb.value),
          task_reminder_time: timeInput.value,
          event_lead_minutes: parseInt(leadSelect.value, 10),
        }).catch(() => null);
        r?.ok
          ? setStatus("ok", "✓ Gespeichert")
          : setStatus("err", "✗ Fehler beim Speichern");
      }}, "Speichern")
    )
  );

  const themeToggle = mkToggle(
    document.documentElement.dataset.theme === "dark",
    (on) => applyTheme(on ? "dark" : "light")
  );
  const themeCard = el("div", { class: "card" },
    el("h2", {}, icon("moon", 17), "Darstellung"),
    el("div", { class: "setting-row", style: "padding-bottom:4px" },
      el("div", {},
        el("div", { class: "setting-label" }, "Dunkles Design"),
        el("div", { class: "setting-hint" }, "Wird auf diesem Gerät gespeichert")
      ),
      themeToggle.el
    )
  );

  setMain(
    el("h1", {}, "Einstellungen"),
    el("p", { class: "subtitle" }, "Kalender, Personen & Benachrichtigungen"),

    el("div", { class: "card" },
      el("h2", {}, icon("home", 17), "Home Assistant"),
      haError
        ? el("p", { class: "err", style: "font-size:0.85rem" }, "Nicht verbunden: " + haError)
        : el("p", { class: "ok", style: "font-size:0.85rem" },
            `✓ Verbunden · ${calendars.length} Kalender gefunden`)
    ),

    themeCard,

    calCard,

    el("div", { class: "card" },
      el("h2", {}, icon("users", 17), "Familienmitglieder"),
      el("p", { class: "setting-hint", style: "margin-bottom:10px" },
        "Für Aufgaben-Zuweisung — Farbe und Emoji erscheinen als Avatar."),
      persons.length
        ? el("div", { class: "person-list" }, ...persons.map(personCard))
        : el("p", { class: "muted", style: "margin-bottom:12px" }, "Noch keine Personen angelegt"),
      el("button", { class: "btn-soft", onclick: () => openPersonForm(null) },
        icon("plus", 16), "Person hinzufügen")
    ),

    notifCard,

    (() => {
      const muellInput = el("input", {
        type: "text",
        class: "form-input",
        placeholder: "sensor.nachste_abholung",
        value: appSettings?.muell_entity || "",
      });
      const muellStatus = el("p", { style: "font-size:0.85rem;min-height:1.2em;margin-top:6px" });
      function setMuellStatus(cls, text) {
        muellStatus.className = cls;
        muellStatus.textContent = text;
        setTimeout(() => { muellStatus.textContent = ""; }, 3000);
      }
      return el("div", { class: "card" },
        el("h2", {}, "🗑️ Mülltag"),
        el("p", { class: "setting-hint", style: "margin-bottom:10px" },
          "HA-Entity, deren State z. B. \"Altpapier in 1 tagen\" enthält. Wird auf Heute angezeigt wenn heute oder morgen Abholung ist."),
        el("p", { class: "form-field-label" }, "Entity-ID"),
        muellInput,
        muellStatus,
        el("div", { class: "form-btns", style: "margin-top:12px" },
          el("button", { class: "btn-soft", onclick: async () => {
            setMuellStatus("muted", "Speichern…");
            const r = await api.patch("api/settings", { muell_entity: muellInput.value.trim() }).catch(() => null);
            r?.ok
              ? setMuellStatus("ok", "✓ Gespeichert")
              : setMuellStatus("err", "✗ Fehler beim Speichern");
          }}, "Speichern")
        )
      );
    })()
  );
}

function openPersonForm(existing) {
  const overlay = el("div", { class: "modal-overlay", onclick: (e) => { if (e.target === overlay) overlay.remove(); } });

  const nameInput  = el("input", { type: "text", placeholder: "Name", class: "form-input",
    value: existing?.name || "", autocomplete: "off" });
  const emojiInput = el("input", { type: "text", placeholder: "Emoji (z.B. 👩)", class: "form-input",
    value: existing?.emoji || "", maxlength: "2" });
  const colorInput = el("input", { type: "color", class: "form-input",
    value: existing?.color || "#4a90d9" });

  const errMsg = el("p", { class: "err", style: "display:none" });

  overlay.appendChild(el("div", { class: "modal-card" },
    el("div", { class: "modal-handle" }),
    el("h2", { style: "margin-bottom:14px" }, existing ? "Person bearbeiten" : "Neue Person"),
    nameInput,
    emojiInput,
    el("p", { class: "form-field-label" }, "Farbe"),
    colorInput,
    errMsg,
    el("div", { class: "form-btns" },
      el("button", { class: "btn-ghost", onclick: () => overlay.remove() }, "Abbrechen"),
      el("button", { class: "btn-soft", onclick: async () => {
        const name = nameInput.value.trim();
        if (!name) { errMsg.textContent = "Name fehlt"; errMsg.style.display = ""; return; }
        const payload = {
          name,
          emoji: emojiInput.value.trim() || null,
          color: colorInput.value,
        };
        if (existing) {
          await api.patch(`api/persons/${existing.id}`, payload);
        } else {
          await api.post("api/persons", payload);
        }
        overlay.remove();
        render();
      }}, "Speichern")
    )
  ));
  document.body.appendChild(overlay);
  setTimeout(() => nameInput.focus(), 50);
}

/* ---------- router ---------- */

const views = {
  heute:        viewHeute,
  kalender:     viewKalender,
  aufgaben:     viewAufgaben,
  listen:       viewListen,
  essen:        viewEssen,
  einstellungen: viewEinstellungen,
};

function switchTab(tab) {
  if (state.tab === tab && !state.listId) return;
  state.tab = tab;
  state.listId = null;
  document.querySelectorAll("nav.tabs button").forEach((b) =>
    b.classList.toggle("active", b.dataset.tab === tab));
  // Fade-out → swap content → fade-in
  $main.style.cssText = "opacity:0;transform:translateY(7px);transition:opacity 0.1s,transform 0.12s";
  setTimeout(async () => {
    await render();
    $main.style.cssText = "opacity:1;transform:translateY(0);transition:opacity 0.2s,transform 0.22s";
    setTimeout(() => { $main.style.cssText = ""; }, 240);
  }, 110);
}

async function render() {
  $main.dataset.view = state.tab; // für ansichts-spezifisches Desktop-Layout
  // Show spinner after 150 ms — fast responses won't flicker
  let loadTimer = setTimeout(showLoading, 150);
  try {
    await views[state.tab]();
  } catch (e) {
    setMain(
      el("p", { class: "err", style: "text-align:center;padding-top:32px" },
        "Fehler beim Laden"),
      el("p", { class: "muted", style: "text-align:center;font-size:0.85rem;margin-top:6px" },
        "Backend nicht erreichbar?"),
      el("button", { class: "btn-soft", style: "margin-top:20px", onclick: render },
        icon("refresh", 15), "Erneut versuchen")
    );
    console.error(e);
  } finally {
    clearTimeout(loadTimer);
  }
}

document.querySelectorAll("nav.tabs button").forEach((b) =>
  b.addEventListener("click", () => switchTab(b.dataset.tab)));

syncThemeColor();
connectWs();
render();
