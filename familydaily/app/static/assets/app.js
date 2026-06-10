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
  patch: (url, body) =>
    fetch(url, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }).then((r) => r.json()),
  del: (url) => fetch(url, { method: "DELETE" }),
};

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

/* ---------- live updates ---------- */

function connectWs() {
  const proto = location.protocol === "https:" ? "wss:" : "ws:";
  const base = location.pathname.replace(/\/$/, "");
  const ws = new WebSocket(`${proto}//${location.host}${base}/api/ws`);
  ws.onmessage = (ev) => {
    const msg = JSON.parse(ev.data);
    if (msg.type === "shopping" && (state.tab === "listen" || state.tab === "heute")) {
      render();
    }
  };
  ws.onclose = () => setTimeout(connectWs, 3000);
  setInterval(() => { if (ws.readyState === 1) ws.send("ping"); }, 30000);
}

/* ---------- views ---------- */

async function viewHeute() {
  const lists = await api.get("api/shopping/lists");
  const openTotal = lists.reduce((s, l) => s + l.open_count, 0);
  const today = new Date().toLocaleDateString("de-DE", {
    weekday: "long", day: "numeric", month: "long",
  });
  $main.replaceChildren(
    el("h1", {}, "Hallo Familie 👋"),
    el("p", { class: "subtitle" }, today),
    el("div", { class: "card" },
      el("h2", {}, "Einkaufen"),
      openTotal
        ? el("p", { class: "status", onclick: () => switchTab("listen"), style: "cursor:pointer" },
            `🛒 ${openTotal} Artikel auf ${lists.filter(l => l.open_count > 0).length === 1 ? "der Liste" : "den Listen"}`)
        : el("p", { class: "status muted" }, "Alles erledigt ✓")
    ),
    el("div", { class: "card" },
      el("h2", {}, "Termine"),
      el("p", { class: "status muted" }, "Kalender kommt in M4")
    ),
    el("div", { class: "card" },
      el("h2", {}, "Abendessen"),
      el("p", { class: "status muted" }, "Essensplan kommt in M5")
    )
  );
}

async function viewListen() {
  if (state.listId) return viewListDetail();
  const lists = await api.get("api/shopping/lists");
  const rows = lists.map((l) =>
    el("div", { class: "list-row", onclick: () => { state.listId = l.id; state.listName = l.name; render(); } },
      el("span", { class: "ico" }, l.icon || "📝"),
      el("span", { class: "name" }, l.name),
      l.open_count ? el("span", { class: "badge" }, String(l.open_count)) : null
    )
  );
  $main.replaceChildren(
    el("h1", {}, "Listen"),
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

  const input = el("input", {
    type: "text", placeholder: "Artikel hinzufügen …",
    autocomplete: "off", enterkeyhint: "done",
  });
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

  $main.replaceChildren(
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

function viewPlatzhalter(title, hint) {
  $main.replaceChildren(
    el("h1", {}, title),
    el("p", { class: "subtitle" }, hint),
    el("p", { class: "empty" }, "Kommt bald 🚧")
  );
}

/* ---------- router ---------- */

const views = {
  heute: viewHeute,
  kalender: () => viewPlatzhalter("Kalender", "Familienkalender — kommt in M4"),
  listen: viewListen,
  essen: () => viewPlatzhalter("Essen", "Essensplan — kommt in M5"),
};

function switchTab(tab) {
  state.tab = tab;
  state.listId = null;
  document.querySelectorAll("nav.tabs button").forEach((b) =>
    b.classList.toggle("active", b.dataset.tab === tab));
  render();
}

async function render() {
  await views[state.tab]();
}

document.querySelectorAll("nav.tabs button").forEach((b) =>
  b.addEventListener("click", () => switchTab(b.dataset.tab)));

connectWs();
render();
