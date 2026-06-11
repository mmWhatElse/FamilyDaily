/* FamilyDaily SPA — no build step, plain JS. */

const $main = document.getElementById("view");
const state = { tab: "heute", listId: null, listName: "" };

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
  return d.toISOString().slice(0, 10);
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
  const tomorrow = isoDate(new Date(Date.now() + 86400000));

  const [lists, tasks, meals, cal] = await Promise.all([
    api.get("api/shopping/lists").catch(() => []),
    api.get("api/tasks?view=today").catch(() => []),
    api.get(`api/meals?start=${today}&end=${today}`).catch(() => []),
    api.get(`api/calendar/events?start=${today}T00:00:00&end=${tomorrow}T00:00:00`).catch(() => null),
  ]);

  const openTotal = lists.reduce((s, l) => s + l.open_count, 0);
  const todayLabel = new Date().toLocaleDateString("de-DE", {
    weekday: "long", day: "numeric", month: "long",
  });
  const meal = meals[0];

  let calContent;
  if (!cal || cal.error) {
    calContent = el("p", { class: "muted", style: "font-size:0.9rem" }, "Kalender nicht verbunden — Einstellungen prüfen");
  } else if (cal.length === 0) {
    calContent = el("p", { class: "muted", style: "font-size:0.9rem" }, "Keine Termine heute");
  } else {
    calContent = el("ul", { class: "event-list" }, ...cal.map((ev) => {
      const time = fmtTime(ev.start);
      return el("li", { class: "event-item", style: `--pc:${ev.color}` },
        el("span", { class: "event-dot" }),
        el("span", { class: "event-body" },
          el("span", { class: "event-title" }, ev.summary),
          el("span", { class: "event-meta" },
            (ev.emoji ? ev.emoji + " " : "") + ev.person + (time ? " · " + time : "")
          )
        )
      );
    }));
  }

  let taskContent;
  if (tasks.length === 0) {
    taskContent = el("p", { class: "muted", style: "font-size:0.9rem" }, "Keine offenen Aufgaben heute");
  } else {
    taskContent = el("ul", { class: "task-list" }, ...tasks.map((t) =>
      el("li", { class: "task-item" + (t.done ? " done" : "") },
        el("button", {
          class: "check",
          onclick: () => api.patch(`api/tasks/${t.id}`, { done: !t.done }).then(render),
        }, t.done ? "✓" : ""),
        el("span", { class: "task-title" }, t.title)
      )
    ));
  }

  setMain(
    el("h1", {}, "Hallo Familie 👋"),
    el("p", { class: "subtitle" }, todayLabel),

    el("div", { class: "card" }, el("h2", {}, "Termine heute"), calContent),
    el("div", { class: "card" }, el("h2", {}, "Aufgaben heute"), taskContent),

    el("div", { class: "card" },
      el("h2", {}, "Abendessen"),
      meal
        ? el("p", { class: "status" },
            meal.url
              ? el("a", { href: meal.url, target: "_blank", class: "meal-link" }, meal.title)
              : meal.title
          )
        : el("p", {
            class: "status muted",
            style: "cursor:pointer",
            onclick: () => switchTab("essen"),
          }, "Noch nichts geplant — tippen zum Planen")
    ),

    el("div", {
      class: "card",
      style: "cursor:pointer",
      onclick: () => switchTab("listen"),
    },
      el("h2", {}, "Einkaufen"),
      openTotal
        ? el("p", { class: "status" },
            `🛒 ${openTotal} Artikel auf ${lists.filter((l) => l.open_count > 0).length === 1 ? "der Liste" : "den Listen"}`)
        : el("p", { class: "status muted" }, "Alles erledigt ✓")
    )
  );
}

/* ---------- Kalender ---------- */

async function viewKalender() {
  showLoading();
  const today = new Date();
  const start = isoDate(today);
  const endD = new Date(today); endD.setDate(today.getDate() + 14);
  const end = isoDate(endD);

  let events;
  try {
    events = await api.get(`api/calendar/events?start=${start}T00:00:00&end=${end}T23:59:59`);
    if (events && events.error) throw new Error(events.error);
  } catch (e) {
    setMain(
      el("h1", {}, "Kalender"),
      el("div", { class: "card", style: "border-left:3px solid var(--err)" },
        el("p", { class: "err" }, "HA-Kalender nicht erreichbar"),
        el("p", { class: "muted", style: "font-size:0.85rem;margin-top:6px" },
          "In Einstellungen die Kalender-Entitäten den Personen zuordnen.")
      )
    );
    return;
  }

  const grouped = {};
  for (const ev of events) {
    const day = (ev.start || "").slice(0, 10);
    if (!grouped[day]) grouped[day] = [];
    grouped[day].push(ev);
  }

  const dayEls = [];
  for (let i = 0; i < 14; i++) {
    const d = new Date(today); d.setDate(today.getDate() + i);
    const day = isoDate(d);
    const isToday = i === 0;
    const label = d.toLocaleDateString("de-DE", { weekday: "short", day: "numeric", month: "short" });
    const dayEvs = grouped[day] || [];

    const evEls = dayEvs.map((ev) => {
      const time = fmtTime(ev.start);
      return el("div", { class: "cal-event", style: `--pc:${ev.color}` },
        el("span", { class: "event-dot" }),
        el("span", { class: "cal-event-title" }, ev.summary),
        time ? el("span", { class: "cal-event-time" }, time) : null,
        el("button", {
          class: "del-btn",
          onclick: async (e) => {
            e.stopPropagation();
            if (!confirm(`"${ev.summary}" löschen?`)) return;
            await api.post("api/calendar/events/delete", { entity_id: ev.entity_id, uid: ev.uid });
            render();
          },
        }, "✕")
      );
    });

    dayEls.push(
      el("div", { class: "cal-day" + (dayEvs.length ? " has-events" : "") },
        el("div", { class: "cal-day-header" + (isToday ? " today" : "") }, label),
        ...evEls
      )
    );
  }

  setMain(
    el("h1", {}, "Kalender"),
    el("p", { class: "subtitle" }, "Nächste 14 Tage"),
    el("button", { class: "btn-soft", style: "margin-bottom:16px", onclick: () => openEventForm() },
      "+ Neuer Termin"),
    ...dayEls
  );
}

function openEventForm() {
  const overlay = el("div", { class: "modal-overlay", onclick: (e) => { if (e.target === overlay) overlay.remove(); } });

  const titleInput = el("input", { type: "text", placeholder: "Titel", class: "form-input", autocomplete: "off" });
  const dateInput  = el("input", { type: "date", class: "form-input", value: isoDate() });
  const timeStart  = el("input", { type: "time", class: "form-input", value: "09:00" });
  const timeEnd    = el("input", { type: "time", class: "form-input", value: "10:00" });
  const allDayCb   = el("input", { type: "checkbox" });
  const calSel     = el("select", { class: "form-input" }, el("option", { value: "" }, "Lädt …"));
  const errMsg     = el("p", { class: "err", style: "display:none" });

  api.get("api/persons").then((persons) => {
    const opts = persons.filter((p) => p.calendar_entity_id).map((p) =>
      el("option", { value: p.calendar_entity_id }, (p.emoji ? p.emoji + " " : "") + p.name)
    );
    calSel.replaceChildren(
      el("option", { value: "" }, opts.length ? "— Person wählen —" : "Keine Kalender konfiguriert"),
      ...opts
    );
  });

  allDayCb.addEventListener("change", () => {
    timeStart.style.display = allDayCb.checked ? "none" : "";
    timeEnd.style.display   = allDayCb.checked ? "none" : "";
  });

  overlay.appendChild(el("div", { class: "modal-card" },
    el("h2", { style: "margin-bottom:14px" }, "Neuer Termin"),
    titleInput,
    dateInput,
    el("label", { class: "form-label" }, allDayCb, " Ganztägig"),
    timeStart, timeEnd, calSel, errMsg,
    el("div", { class: "form-btns" },
      el("button", { class: "btn-ghost", onclick: () => overlay.remove() }, "Abbrechen"),
      el("button", { class: "btn-soft", onclick: async () => {
        const title = titleInput.value.trim();
        const calId = calSel.value;
        if (!title) { errMsg.textContent = "Titel fehlt"; errMsg.style.display = ""; return; }
        if (!calId) { errMsg.textContent = "Person / Kalender wählen"; errMsg.style.display = ""; return; }
        const allDay = allDayCb.checked;
        let evStart, evEnd;
        if (allDay) {
          evStart = dateInput.value;
          const ed = new Date(dateInput.value + "T12:00:00"); ed.setDate(ed.getDate() + 1);
          evEnd = isoDate(ed);
        } else {
          evStart = `${dateInput.value}T${timeStart.value}:00`;
          evEnd   = `${dateInput.value}T${timeEnd.value}:00`;
        }
        const res = await api.post("api/calendar/events", {
          entity_id: calId, summary: title, start: evStart, end: evEnd, all_day: allDay,
        });
        if (res && (res.detail || res.error)) {
          errMsg.textContent = res.detail || res.error;
          errMsg.style.display = "";
          return;
        }
        overlay.remove();
        render();
      }}, "Speichern")
    )
  ));
  document.body.appendChild(overlay);
  setTimeout(() => titleInput.focus(), 50);
}

/* ---------- Aufgaben ---------- */

async function viewAufgaben() {
  let fetchOk = true;
  const [tasks, persons] = await Promise.all([
    api.get("api/tasks").catch(() => { fetchOk = false; return []; }),
    api.get("api/persons").catch(() => []),
  ]);
  const personMap = Object.fromEntries(persons.map((p) => [p.id, p]));
  const open = tasks.filter((t) => !t.done);
  const done = tasks.filter((t) => t.done);

  function taskRow(t) {
    const pips = (t.person_ids || []).map((pid) => {
      const p = personMap[pid];
      return p ? el("span", { class: "person-pip", style: `background:${p.color}`, title: p.name },
        p.emoji || p.name[0]) : null;
    });
    const recurBadge = t.recurrence && t.recurrence !== "none"
      ? el("span", { class: "recur-badge" }, "↻ " + RECUR_LABEL[t.recurrence]) : null;
    const dueLbl = t.due_date
      ? el("span", {
          class: "due-lbl" + (!t.done && t.due_date < isoDate() ? " overdue" : ""),
        }, fmtDate(t.due_date))
      : null;

    return el("li", { class: "task-item" + (t.done ? " done" : "") },
      el("button", {
        class: "check",
        onclick: () => api.patch(`api/tasks/${t.id}`, { done: !t.done }).then(render),
      }, t.done ? "✓" : ""),
      el("div", { class: "task-body" },
        el("span", { class: "task-title" }, t.title),
        el("div", { class: "task-meta" }, ...pips, dueLbl, recurBadge)
      ),
      el("button", {
        class: "del-btn",
        onclick: async () => {
          if (t.template_id) {
            const series = confirm("Auch alle künftigen Wiederholungen löschen?");
            await api.del(`api/tasks/${t.id}?series=${series}`);
          } else {
            await api.del(`api/tasks/${t.id}`);
          }
          render();
        },
      }, "✕")
    );
  }

  setMain(
    el("h1", {}, "Aufgaben"),
    el("button", { class: "btn-soft", style: "margin-bottom:16px",
      onclick: () => openTaskForm(persons) }, "+ Neue Aufgabe"),
    fetchOk
      ? (open.length
          ? el("ul", { class: "task-list" }, ...open.map(taskRow))
          : el("p", { class: "empty" }, "Alles erledigt 🎉"))
      : el("p", { class: "empty" }, "Backend nicht erreichbar"),
    done.length ? el("p", { class: "section-label" }, "Erledigt") : null,
    done.length ? el("ul", { class: "task-list" }, ...done.map(taskRow)) : null
  );
}

function openTaskForm(persons) {
  const overlay = el("div", { class: "modal-overlay", onclick: (e) => { if (e.target === overlay) overlay.remove(); } });

  const titleInput = el("input", { type: "text", placeholder: "Aufgabe", class: "form-input", autocomplete: "off" });
  const dateInput  = el("input", { type: "date", class: "form-input" });
  const recurSel   = el("select", { class: "form-input" },
    el("option", { value: "none" }, "Keine Wiederholung"),
    el("option", { value: "daily" }, "Täglich"),
    el("option", { value: "weekly" }, "Wöchentlich"),
    el("option", { value: "monthly" }, "Monatlich"),
  );
  const personChecks = persons.map((p) =>
    el("label", { class: "person-check-row" },
      el("input", { type: "checkbox", value: String(p.id) }),
      el("span", { class: "person-pip", style: `background:${p.color}` }, p.emoji || p.name[0]),
      " " + p.name
    )
  );
  const errMsg = el("p", { class: "err", style: "display:none" });

  overlay.appendChild(el("div", { class: "modal-card" },
    el("h2", { style: "margin-bottom:14px" }, "Neue Aufgabe"),
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
        const res = await api.post("api/tasks", {
          title,
          person_ids,
          due_date: dateInput.value || null,
          recurrence: recurSel.value,
        });
        if (res && res.detail) { errMsg.textContent = res.detail; errMsg.style.display = ""; return; }
        overlay.remove();
        render();
      }}, "Speichern")
    )
  ));
  document.body.appendChild(overlay);
  setTimeout(() => titleInput.focus(), 50);
}

/* ---------- Listen (no tab button — accessed via Heute card) ---------- */

async function viewListen() {
  if (state.listId) return viewListDetail();
  const lists = await api.get("api/shopping/lists").catch(() => []);
  const rows = lists.map((l) =>
    el("div", { class: "list-row", onclick: () => { state.listId = l.id; state.listName = l.name; render(); } },
      el("span", { class: "ico" }, l.icon || "📝"),
      el("span", { class: "name" }, l.name),
      l.open_count ? el("span", { class: "badge" }, String(l.open_count)) : null
    )
  );
  setMain(
    el("div", { class: "topbar" },
      el("button", { class: "back", onclick: () => switchTab("heute") }, "‹"),
      el("h1", {}, "Listen")
    ),
    el("p", { class: "subtitle" }, "Einkaufs- und andere Listen"),
    ...rows,
    el("button", { class: "btn-ghost", onclick: addList }, "+ Neue Liste")
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
      }, i.checked ? "✓" : ""),
      el("span", { class: "label" }, i.name),
      el("button", {
        class: "del",
        onclick: () => api.del(`api/shopping/items/${i.id}`).then(render),
      }, "✕")
    );

  setMain(
    el("div", { class: "topbar" },
      el("button", { class: "back", onclick: () => { state.listId = null; render(); } }, "‹"),
      el("h1", {}, state.listName)
    ),
    el("div", { class: "add-row" }, input, el("button", { class: "add", onclick: () => submit() }, "+"), sugBox),
    open.length
      ? el("ul", { class: "items" }, ...open.map(itemLi))
      : el("p", { class: "empty" }, "Nichts auf der Liste 🎉"),
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
            meal.url
              ? el("a", { href: meal.url, target: "_blank", class: "meal-ext",
                  onclick: (e) => e.stopPropagation() }, "↗")
              : null
          )
        : el("span", { class: "meal-empty" }, "+ Hinzufügen"),
      meal
        ? el("button", {
            class: "del-btn",
            onclick: async (e) => { e.stopPropagation(); await api.del(`api/meals/${day}`); render(); },
          }, "✕")
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
    }, "↩ Letzte Woche übernehmen")
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
  const errMsg = el("p", { class: "err", style: "display:none" });

  overlay.appendChild(el("div", { class: "modal-card" },
    el("h2", { style: "margin-bottom:4px" }, label),
    el("p", { class: "form-field-label", style: "margin-bottom:12px" }, "Abendessen"),
    titleInput, noteInput, urlInput, errMsg,
    el("div", { class: "form-btns" },
      el("button", { class: "btn-ghost", onclick: () => overlay.remove() }, "Abbrechen"),
      el("button", { class: "btn-soft", onclick: async () => {
        const title = titleInput.value.trim();
        if (!title) { errMsg.textContent = "Titel fehlt"; errMsg.style.display = ""; return; }
        await api.put(`api/meals/${day}`, {
          title,
          note: noteInput.value.trim() || null,
          url:  urlInput.value.trim() || null,
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

async function viewEinstellungen() {
  const [persons, haRaw] = await Promise.all([
    api.get("api/persons").catch(() => []),
    api.get("api/persons/ha-calendars").catch(() => ({ error: "Nicht erreichbar" })),
  ]);
  const haCalendars = Array.isArray(haRaw) ? haRaw : [];
  const haError     = haRaw?.error;

  function personCard(p) {
    return el("div", { class: "person-card" },
      el("span", { class: "person-avatar", style: `background:${p.color}` }, p.emoji || p.name[0]),
      el("div", { class: "person-info" },
        el("strong", {}, p.name),
        el("span", { class: "muted", style: "font-size:0.8rem" },
          p.calendar_entity_id ? "📅 " + p.calendar_entity_id : "Kein Kalender")
      ),
      el("button", { class: "btn-icon", onclick: () => openPersonForm(p, haCalendars) }, "✎"),
      el("button", {
        class: "btn-icon del",
        onclick: async () => {
          if (!confirm(`"${p.name}" löschen?`)) return;
          await api.del(`api/persons/${p.id}`);
          render();
        },
      }, "✕")
    );
  }

  setMain(
    el("h1", {}, "Einstellungen"),
    el("p", { class: "subtitle" }, "Personen & Kalender"),

    el("div", { class: "card" },
      el("h2", {}, "Home Assistant"),
      haError
        ? el("p", { class: "err", style: "font-size:0.85rem" }, "Nicht verbunden: " + haError)
        : el("p", { class: "ok", style: "font-size:0.85rem" },
            `✓ ${haCalendars.length} Kalender verfügbar`)
    ),

    el("div", { class: "card" },
      el("h2", {}, "Familienmitglieder"),
      persons.length
        ? el("div", { class: "person-list" }, ...persons.map(personCard))
        : el("p", { class: "muted", style: "margin-bottom:12px" }, "Noch keine Personen angelegt"),
      el("button", { class: "btn-soft", onclick: () => openPersonForm(null, haCalendars) },
        "+ Person hinzufügen")
    )
  );
}

function openPersonForm(existing, haCalendars) {
  const overlay = el("div", { class: "modal-overlay", onclick: (e) => { if (e.target === overlay) overlay.remove(); } });

  const nameInput  = el("input", { type: "text", placeholder: "Name", class: "form-input",
    value: existing?.name || "", autocomplete: "off" });
  const emojiInput = el("input", { type: "text", placeholder: "Emoji (z.B. 👩)", class: "form-input",
    value: existing?.emoji || "", maxlength: "2" });
  const colorInput = el("input", { type: "color", class: "form-input",
    value: existing?.color || "#4a90d9" });
  const calSel = el("select", { class: "form-input" },
    el("option", { value: "" }, "— Keinen —"),
    ...haCalendars.map((c) => el("option", { value: c.entity_id }, c.name || c.entity_id))
  );
  if (existing?.calendar_entity_id) calSel.value = existing.calendar_entity_id;

  const errMsg = el("p", { class: "err", style: "display:none" });

  overlay.appendChild(el("div", { class: "modal-card" },
    el("h2", { style: "margin-bottom:14px" }, existing ? "Person bearbeiten" : "Neue Person"),
    nameInput,
    emojiInput,
    el("p", { class: "form-field-label" }, "Farbe"),
    colorInput,
    el("p", { class: "form-field-label" }, "HA-Kalender"),
    calSel,
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
          calendar_entity_id: calSel.value || null,
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
  state.tab = tab;
  state.listId = null;
  document.querySelectorAll("nav.tabs button").forEach((b) =>
    b.classList.toggle("active", b.dataset.tab === tab));
  render();
}

async function render() {
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
        "↻ Erneut versuchen")
    );
    console.error(e);
  } finally {
    clearTimeout(loadTimer);
  }
}

document.querySelectorAll("nav.tabs button").forEach((b) =>
  b.addEventListener("click", () => switchTab(b.dataset.tab)));

connectWs();
render();
