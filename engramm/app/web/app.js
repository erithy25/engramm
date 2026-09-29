/* ENGRAMM Chat – the page. No framework, no build step: this file is served as is. */
(() => {
  "use strict";

  const $ = (id) => document.getElementById(id);
  const STORE = "engramm.conversations.v1";
  const THEME = "engramm.theme";
  const SUGGESTIONS = [
    { title: "Who wrote Pride and Prejudice?", sub: "Eine Faktenfrage mit Quelle" },
    { title: "When did the Berlin Wall fall?", sub: "Datum nachschlagen" },
    { title: "My name is Alex and I live in Hamburg.", sub: "ENGRAMM merkt sich etwas über dich" },
    { title: "What is my name?", sub: "…und erinnert sich daran" },
  ];

  // -- storage (never breaks the page: private mode or blocked storage just means no history) --
  const storage = {
    get(key, fallback) {
      try { const v = localStorage.getItem(key); return v === null ? fallback : JSON.parse(v); }
      catch { return fallback; }
    },
    set(key, value) { try { localStorage.setItem(key, JSON.stringify(value)); } catch { /* ignore */ } },
  };

  const state = {
    conversations: storage.get(STORE, []),
    activeId: null,
    ready: false,
    busy: false,
  };

  const uid = () => (crypto.randomUUID ? crypto.randomUUID() : String(Date.now()) + Math.random().toString(16).slice(2));
  const save = () => storage.set(STORE, state.conversations.slice(0, 200));
  const active = () => state.conversations.find((c) => c.id === state.activeId) || null;

  // -- api ------------------------------------------------------------------------------------
  async function api(path, body) {
    const res = await fetch(path, body === undefined ? {} : {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
    });
    let data = {};
    try { data = await res.json(); } catch { /* keep {} */ }
    if (!res.ok) throw new Error(data.error || `Fehler ${res.status}`);
    return data;
  }

  // -- health / loading ------------------------------------------------------------------------
  async function pollHealth() {
    const box = $("status"), text = $("statusText");
    try {
      const h = await api("/api/health");
      if (h.error) {
        box.className = "status error"; text.textContent = "Fehler beim Laden"; box.title = h.error;
        return;
      }
      if (h.ready) {
        state.ready = true; box.className = "status ready";
        text.textContent = "bereit";
        const more = document.createElement("span");
        more.className = "status-more";
        more.textContent = ` · ${(h.sentences / 1e6).toFixed(1)} Mio. Sätze gelesen`;
        text.append(more);
        updateSend();
        return;
      }
      box.className = "status"; text.textContent = "lädt sein Wissen … (etwa eine Minute)";
    } catch {
      box.className = "status error"; text.textContent = "keine Verbindung";
    }
    setTimeout(pollHealth, 1500);
  }

  // -- sidebar -------------------------------------------------------------------------------
  function renderSidebar() {
    const nav = $("conversations");
    nav.replaceChildren();
    const today = new Date().toDateString();
    const groups = [["Heute", []], ["Früher", []]];
    for (const c of state.conversations) {
      (new Date(c.updated).toDateString() === today ? groups[0][1] : groups[1][1]).push(c);
    }
    for (const [label, list] of groups) {
      if (!list.length) continue;
      const g = document.createElement("div");
      g.className = "conv-group"; g.textContent = label; nav.append(g);
      for (const c of list) {
        const row = document.createElement("div");
        row.className = "conv" + (c.id === state.activeId ? " active" : "");
        row.tabIndex = 0;
        row.setAttribute("role", "button");
        const t = document.createElement("span");
        t.className = "conv-title"; t.textContent = c.title || "Neuer Chat";
        const del = document.createElement("button");
        del.className = "conv-del"; del.textContent = "✕"; del.title = "Chat löschen";
        del.setAttribute("aria-label", "Chat löschen");
        del.addEventListener("click", (e) => { e.stopPropagation(); removeConversation(c.id); });
        row.append(t, del);
        row.addEventListener("click", () => openConversation(c.id));
        row.addEventListener("keydown", (e) => { if (e.key === "Enter") openConversation(c.id); });
        nav.append(row);
      }
    }
  }

  function newConversation() {
    state.activeId = null;
    renderThread();
    renderSidebar();
    closeSidebar();
    $("input").focus();
  }

  function openConversation(id) {
    state.activeId = id;
    renderThread();
    renderSidebar();
    closeSidebar();
  }

  function removeConversation(id) {
    state.conversations = state.conversations.filter((c) => c.id !== id);
    if (state.activeId === id) state.activeId = null;
    save(); renderSidebar(); renderThread();
  }

  // -- thread --------------------------------------------------------------------------------
  function renderThread() {
    const thread = $("thread");
    thread.querySelectorAll(".msg").forEach((m) => m.remove());
    const conv = active();
    $("empty").hidden = !!(conv && conv.messages.length);
    if (!conv) return;
    for (const m of conv.messages) {
      if (m.role === "user") addUser(m.text);
      else addAssistant(m.reply, false);
    }
    scrollDown(false);
  }

  function addUser(text) {
    const el = document.createElement("article");
    el.className = "msg user";
    const b = document.createElement("div");
    b.className = "bubble"; b.textContent = text;
    el.append(b);
    $("thread").append(el);
    return el;
  }

  function addTyping() {
    const el = $("tplAssistant").content.firstElementChild.cloneNode(true);
    el.querySelector(".text").innerHTML = '<span class="typing"><i></i><i></i><i></i></span>';
    el.querySelector(".actions").hidden = true;
    $("thread").append(el);
    scrollDown();
    return el;
  }

  function chip(text, cls, href, title) {
    const c = document.createElement(href ? "a" : "span");
    c.className = "chip" + (cls ? " " + cls : "");
    c.textContent = text;
    if (title) c.title = title;
    if (href) { c.href = href; c.target = "_blank"; c.rel = "noopener noreferrer"; }
    return c;
  }

  function fillAssistant(el, reply, animate) {
    const textEl = el.querySelector(".text");
    const meta = el.querySelector(".meta");
    const evBtn = el.querySelector('[data-act="evidence"]');
    const evBox = el.querySelector(".evidence");
    el.querySelector(".actions").hidden = false;
    meta.replaceChildren();

    if (reply.error) {
      textEl.innerHTML = "";
      const s = document.createElement("span");
      s.className = "error-text"; s.textContent = reply.error;
      textEl.append(s);
      return;
    }

    const full = reply.text || "";
    if (animate) typeOut(textEl, full); else textEl.textContent = full;

    if (reply.kind === "answer" && reply.via === "lookup") meta.append(chip("sicher", "sure", null, "Konfidenz über der Schwelle"));
    if (reply.kind === "unknown" && reply.guess) meta.append(chip("unsicher", "unsure", null, "Beste Vermutung unter der Schwelle"));
    if (reply.kind === "learned") meta.append(chip("gemerkt", "memory"));
    if (reply.kind === "forgot") meta.append(chip("vergessen", "memory"));
    if (reply.answer && (reply.via === "facts" || reply.via === "memory")) meta.append(chip("aus deinem Gedächtnis", "memory"));
    if (reply.source && reply.source.title) {
      const prefix = reply.source.kind === "wikipedia" ? "Wikipedia · " : reply.source.kind === "web" ? "Web · " : "";
      meta.append(chip(prefix + reply.source.title, "", reply.source.url, "Quelle öffnen"));
    }
    if (reply.resolved) meta.append(chip("verstanden als: " + reply.resolved, "", null));
    if (typeof reply.seconds === "number") meta.append(chip(`${reply.seconds.toFixed(2)} s`, "", null, "Antwortzeit"));

    if (reply.evidence) {
      evBtn.hidden = false;
      evBox.replaceChildren(highlight(reply.evidence, reply.answer || reply.guess));
      evBtn.onclick = () => { evBox.hidden = !evBox.hidden; evBtn.textContent = evBox.hidden ? "Beleg" : "Beleg ausblenden"; };
    }
    el.querySelector('[data-act="copy"]').onclick = async (e) => {
      try { await navigator.clipboard.writeText(full); e.target.textContent = "Kopiert"; }
      catch { e.target.textContent = "Nicht möglich"; }
      setTimeout(() => (e.target.textContent = "Kopieren"), 1200);
    };
  }

  function addAssistant(reply, animate) {
    const el = $("tplAssistant").content.firstElementChild.cloneNode(true);
    $("thread").append(el);
    fillAssistant(el, reply, animate);
    return el;
  }

  function highlight(sentence, part) {
    const frag = document.createDocumentFragment();
    const i = part ? sentence.toLowerCase().indexOf(part.toLowerCase()) : -1;
    if (i < 0) { frag.append(sentence); return frag; }
    const mark = document.createElement("mark");
    mark.textContent = sentence.slice(i, i + part.length);
    frag.append(sentence.slice(0, i), mark, sentence.slice(i + part.length));
    return frag;
  }

  function typeOut(el, text) {
    el.textContent = "";
    const words = text.split(/(\s+)/);
    const step = Math.max(1, Math.ceil(words.length / 40));
    let i = 0;
    const tick = () => {
      el.textContent += words.slice(i, i + step).join("");
      i += step;
      scrollDown(false);
      if (i < words.length) setTimeout(tick, 18);
    };
    tick();
  }

  function scrollDown(smooth = true) {
    const t = $("thread");
    t.scrollTo({ top: t.scrollHeight, behavior: smooth ? "smooth" : "auto" });
  }

  // -- sending -------------------------------------------------------------------------------
  function updateSend() {
    $("send").disabled = !state.ready || state.busy || !$("input").value.trim();
  }

  async function send(text) {
    text = text.trim();
    if (!text || !state.ready || state.busy) return;
    let conv = active();
    if (!conv) {
      conv = { id: uid(), title: text.slice(0, 60), updated: Date.now(), messages: [] };
      state.conversations.unshift(conv);
      state.activeId = conv.id;
    }
    conv.messages.push({ role: "user", text });
    conv.updated = Date.now();
    state.conversations = [conv, ...state.conversations.filter((c) => c !== conv)];
    save(); renderSidebar();
    $("empty").hidden = true;
    addUser(text);
    $("input").value = ""; autosize();
    state.busy = true; updateSend();
    const pending = addTyping();
    let reply;
    try {
      reply = await api("/api/chat", { conversation: conv.id, message: text });
    } catch (e) {
      reply = { error: e.message || "Keine Verbindung zu ENGRAMM." };
    }
    fillAssistant(pending, reply, !reply.error);
    conv.messages.push({ role: "assistant", reply });
    conv.updated = Date.now();
    save();
    state.busy = false; updateSend();
    $("input").focus();
  }

  function autosize() {
    const t = $("input");
    t.style.height = "auto";
    t.style.height = Math.min(t.scrollHeight, 200) + "px";
  }

  // -- memory dialog -------------------------------------------------------------------------
  async function openMemory() {
    const dlg = $("memoryDialog"), list = $("memoryList");
    list.replaceChildren();
    dlg.showModal();
    let items = [];
    try { items = (await api("/api/memory")).items; }
    catch (e) { const li = document.createElement("li"); li.textContent = e.message; list.append(li); return; }
    if (!items.length) {
      const li = document.createElement("li");
      li.className = "muted"; li.textContent = "Noch nichts. Erzähl ENGRAMM etwas, z. B. „My name is Alex.“";
      list.append(li);
      return;
    }
    for (const it of items) {
      const li = document.createElement("li");
      const s = document.createElement("span"); s.textContent = it.preview;
      const b = document.createElement("button"); b.className = "forget"; b.textContent = "Vergessen";
      b.onclick = async () => {
        b.disabled = true;
        try { await api("/api/memory/forget", { source: it.source }); li.remove(); }
        catch (e) { b.disabled = false; b.textContent = e.message; }
      };
      li.append(s, b); list.append(li);
    }
  }

  // -- theme ---------------------------------------------------------------------------------
  function applyTheme(t) {
    if (t) document.documentElement.dataset.theme = t; else delete document.documentElement.dataset.theme;
    const dark = t ? t === "dark" : matchMedia("(prefers-color-scheme: dark)").matches;
    $("themeLabel").textContent = dark ? "Helles Design" : "Dunkles Design";
  }
  function toggleTheme() {
    const cur = document.documentElement.dataset.theme
      || (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
    const next = cur === "dark" ? "light" : "dark";
    storage.set(THEME, next); applyTheme(next);
  }

  // -- mobile sidebar ------------------------------------------------------------------------
  function openSidebar() { $("sidebar").classList.add("open"); $("scrim").hidden = false; }
  function closeSidebar() { $("sidebar").classList.remove("open"); $("scrim").hidden = true; }

  // -- start ---------------------------------------------------------------------------------
  function init() {
    applyTheme(storage.get(THEME, null));
    for (const s of SUGGESTIONS) {
      const b = document.createElement("button");
      b.className = "suggestion"; b.type = "button";
      const t = document.createElement("b"); t.textContent = s.title;
      const d = document.createElement("span"); d.textContent = s.sub;
      b.append(t, d);
      b.onclick = () => send(s.title);
      $("suggestions").append(b);
    }
    $("composer").addEventListener("submit", (e) => { e.preventDefault(); send($("input").value); });
    $("input").addEventListener("input", () => { autosize(); updateSend(); });
    $("input").addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey && !e.isComposing) { e.preventDefault(); send($("input").value); }
    });
    $("newChat").onclick = newConversation;
    $("openMemory").onclick = openMemory;
    $("openAbout").onclick = () => $("aboutDialog").showModal();
    $("toggleTheme").onclick = toggleTheme;
    $("openSidebar").onclick = openSidebar;
    $("closeSidebar").onclick = closeSidebar;
    $("scrim").onclick = closeSidebar;
    document.querySelectorAll("[data-close]").forEach((b) => (b.onclick = () => b.closest("dialog").close()));
    document.querySelectorAll("dialog").forEach((d) =>
      d.addEventListener("click", (e) => { if (e.target === d) d.close(); }));
    document.addEventListener("keydown", (e) => {
      if ((e.metaKey || e.ctrlKey) && e.shiftKey && e.key.toLowerCase() === "o") { e.preventDefault(); newConversation(); }
    });
    state.activeId = state.conversations[0] ? state.conversations[0].id : null;
    renderSidebar(); renderThread();
    pollHealth();
    $("input").focus();
  }

  init();
})();
