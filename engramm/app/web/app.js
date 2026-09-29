/* ENGRAMM Chat – the page. No framework, no build step: this file is served as is. */
(() => {
  "use strict";

  const $ = (id) => document.getElementById(id);
  const STORE = "engramm.conversations.v1";
  const THEME = "engramm.theme";
  const LANG = "engramm.lang";

  // -- interface texts (English first, German switchable) ------------------------------------
  const I18N = {
    en: {
      conversations: "Conversations", closeSidebar: "Close sidebar", openSidebar: "Open sidebar", newChat: "New chat",
      history: "History", memory: "What ENGRAMM knows", about: "About ENGRAMM", otherLanguage: "Deutsch",
      darkMode: "Dark mode", lightMode: "Light mode", pill: "· no neural network",
      pillTitle: "Answers by counting, rules and hypervectors — no neural network",
      emptyTitle: "How can I help?",
      emptySub: "Ask me anything, tell me about yourself, or just chat. I show where every fact comes from.",
      placeholder: "Message ENGRAMM …", message: "Message", send: "Send",
      hint: "ENGRAMM works without a neural network and shows its sources — it can still be wrong. Check the source.",
      close: "Close", memorySub: "What you told ENGRAMM. “Forget” deletes it for real — not just hidden.",
      aboutIntro: "ENGRAMM is a chat assistant that works <b>without a neural network</b>: counting, rules and hypervectors.",
      about1: "Facts come with their source — nothing is invented on purpose.",
      about2: "Remembers what you tell it (“My sister is called Anna”) — and truly forgets on request (“Forget my sister”).",
      about3: "Small talk, jokes, explanations (“Tell me about volcanoes”), calculations and unit conversion.",
      about4: "Runs entirely on your computer. Same question, same answer.",
      aboutLimits: "Limits: English only for now, no internet, weaker at long creative writing. When unsure, ENGRAMM says so.",
      today: "Today", earlier: "Earlier", untitled: "New chat", deleteChat: "Delete chat",
      loading: "loading its knowledge … (about a minute)", ready: "ready", loadError: "error while loading",
      offline: "no connection", sentences: (n) => ` · ${n} million sentences read`, quick: " · quick mode",
      quickTitle: "Quick mode: small sentence index. Full version: bash scripts/setup_mac.sh --full",
      sure: "confident", sureTitle: "Confidence above the threshold", unsure: "not sure",
      unsureTitle: "Best guess below the threshold", learned: "remembered", forgot: "forgotten",
      fromMemory: "from your memory", understoodAs: "understood as: ", seconds: "response time",
      openSource: "Open source", copy: "Copy", copied: "Copied", copyFailed: "Not possible", evidence: "Evidence",
      hideEvidence: "Hide evidence", tool: "calculated", article: "article", safety: "help", memoryChip: "memory",
      noMemory: "Nothing yet. Tell ENGRAMM something, e.g. “My name is Alex.”", forget: "Forget",
      connectionLost: "No connection to ENGRAMM.", error: (n) => `Error ${n}`,
      wikipedia: "Wikipedia · ", web: "Web · ", toldMe: "you told me",
      suggestions: [
        { title: "Hi! My name is Alex.", sub: "Say hello — ENGRAMM remembers you" },
        { title: "Tell me about black holes", sub: "An explanation with its source" },
        { title: "Who wrote Pride and Prejudice?", sub: "A fact with evidence" },
        { title: "Tell me a joke", sub: "Or a fun fact" },
      ],
    },
    de: {
      conversations: "Unterhaltungen", closeSidebar: "Seitenleiste schließen", openSidebar: "Seitenleiste öffnen",
      newChat: "Neuer Chat", history: "Verlauf", memory: "Was ENGRAMM weiß", about: "Über ENGRAMM",
      otherLanguage: "English", darkMode: "Dunkles Design", lightMode: "Helles Design", pill: "· ohne neuronales Netz",
      pillTitle: "Antworten nur durch Zählen, Regeln und Hypervektoren – ohne neuronales Netz",
      emptyTitle: "Wie kann ich helfen?",
      emptySub: "Frag etwas, erzähl von dir oder plaudere einfach – auf Englisch. Zu jedem Fakt gibt es die Quelle.",
      placeholder: "Nachricht an ENGRAMM (auf Englisch) …", message: "Nachricht", send: "Senden",
      hint: "ENGRAMM arbeitet ohne neuronales Netz und zeigt seine Quellen – und kann sich trotzdem irren. Prüfe die Quelle.",
      close: "Schließen", memorySub: "Was du ENGRAMM erzählt hast. „Vergessen“ löscht es wirklich – nicht nur versteckt.",
      aboutIntro: "ENGRAMM ist ein Chat, der <b>ohne neuronales Netz</b> arbeitet: nur Zählen, Regeln und Hypervektoren.",
      about1: "Fakten mit Quelle – nichts wird absichtlich erfunden.",
      about2: "Merkt sich, was du erzählst („My sister is called Anna“) – und vergisst es auf Befehl wirklich („Forget my sister“).",
      about3: "Smalltalk, Witze, Erklärungen („Tell me about volcanoes“), Rechnen und Einheiten umrechnen.",
      about4: "Läuft komplett auf deinem Rechner. Gleiche Frage – gleiche Antwort.",
      aboutLimits: "Grenzen: vorerst nur Englisch, kein Internet, schwächer bei langen kreativen Texten. Bei Unsicherheit sagt ENGRAMM das.",
      today: "Heute", earlier: "Früher", untitled: "Neuer Chat", deleteChat: "Chat löschen",
      loading: "lädt sein Wissen … (etwa eine Minute)", ready: "bereit", loadError: "Fehler beim Laden",
      offline: "keine Verbindung", sentences: (n) => ` · ${n} Mio. Sätze gelesen`, quick: " · Schnellmodus",
      quickTitle: "Schnellmodus: kleiner Satzindex. Volle Version: bash scripts/setup_mac.sh --full",
      sure: "sicher", sureTitle: "Konfidenz über der Schwelle", unsure: "unsicher",
      unsureTitle: "Beste Vermutung unter der Schwelle", learned: "gemerkt", forgot: "vergessen",
      fromMemory: "aus deinem Gedächtnis", understoodAs: "verstanden als: ", seconds: "Antwortzeit",
      openSource: "Quelle öffnen", copy: "Kopieren", copied: "Kopiert", copyFailed: "Nicht möglich", evidence: "Beleg",
      hideEvidence: "Beleg ausblenden", tool: "berechnet", article: "Artikel", safety: "Hilfe", memoryChip: "Gedächtnis",
      noMemory: "Noch nichts. Erzähl ENGRAMM etwas, z. B. „My name is Alex.“", forget: "Vergessen",
      connectionLost: "Keine Verbindung zu ENGRAMM.", error: (n) => `Fehler ${n}`,
      wikipedia: "Wikipedia · ", web: "Web · ", toldMe: "von dir erzählt",
      suggestions: [
        { title: "Hi! My name is Alex.", sub: "Sag Hallo – ENGRAMM merkt sich dich" },
        { title: "Tell me about black holes", sub: "Eine Erklärung mit Quelle" },
        { title: "Who wrote Pride and Prejudice?", sub: "Ein Fakt mit Beleg" },
        { title: "Tell me a joke", sub: "Oder ein Fun Fact" },
      ],
    },
  };
  let lang = "en";
  const T = (key, ...args) => {
    const v = (I18N[lang] && I18N[lang][key]) ?? I18N.en[key];
    return typeof v === "function" ? v(...args) : v;
  };

  function applyLanguage(l) {
    lang = I18N[l] ? l : "en";
    document.documentElement.lang = lang;
    document.querySelectorAll("[data-i18n]").forEach((el) => { el.textContent = T(el.dataset.i18n); });
    document.querySelectorAll("[data-i18n-html]").forEach((el) => { el.innerHTML = T(el.dataset.i18nHtml); });
    document.querySelectorAll("[data-i18n-aria]").forEach((el) => el.setAttribute("aria-label", T(el.dataset.i18nAria)));
    document.querySelectorAll("[data-i18n-title]").forEach((el) => { el.title = T(el.dataset.i18nTitle); });
    document.querySelectorAll("[data-i18n-placeholder]").forEach((el) => { el.placeholder = T(el.dataset.i18nPlaceholder); });
    renderSuggestions();
    applyTheme(storage.get(THEME, null));
  }

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
    if (!res.ok) throw new Error(data.error || T("error", res.status));
    return data;
  }

  // -- health / loading ------------------------------------------------------------------------
  let health = null;
  async function pollHealth() {
    try {
      health = await api("/api/health");
      renderStatus();
      if (health.error || health.ready) { if (health.ready) { state.ready = true; updateSend(); } return; }
    } catch {
      health = { offline: true };
      renderStatus();
    }
    setTimeout(pollHealth, 1500);
  }

  function renderStatus() {
    const box = $("status"), text = $("statusText");
    box.title = "";
    if (!health) { box.className = "status"; text.textContent = "…"; return; }
    if (health.offline) { box.className = "status error"; text.textContent = T("offline"); return; }
    if (health.error) { box.className = "status error"; text.textContent = T("loadError"); box.title = health.error; return; }
    if (!health.ready) { box.className = "status"; text.textContent = T("loading"); return; }
    box.className = "status ready";
    text.textContent = T("ready");
    const more = document.createElement("span");
    more.className = "status-more";
    more.textContent = T("sentences", (health.sentences / 1e6).toFixed(1)) + (health.mode === "quick" ? T("quick") : "");
    if (health.mode === "quick") box.title = T("quickTitle");
    text.append(more);
  }

  // -- sidebar -------------------------------------------------------------------------------
  function renderSidebar() {
    const nav = $("conversations");
    nav.replaceChildren();
    const today = new Date().toDateString();
    const groups = [[T("today"), []], [T("earlier"), []]];
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
        t.className = "conv-title"; t.textContent = c.title || T("untitled");
        const del = document.createElement("button");
        del.className = "conv-del"; del.textContent = "✕"; del.title = T("deleteChat");
        del.setAttribute("aria-label", T("deleteChat"));
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
    if (animate) typeOut(textEl, full); else { textEl.textContent = full; textEl.dataset.done = "1"; }

    const k = reply.kind;
    if (k === "answer" && reply.via === "lookup") meta.append(chip(T("sure"), "sure", null, T("sureTitle")));
    if (k === "unknown" && reply.guess) meta.append(chip(T("unsure"), "unsure", null, T("unsureTitle")));
    if (k === "learned") meta.append(chip(T("learned"), "memory"));
    if (k === "forgot") meta.append(chip(T("forgot"), "memory"));
    if (k === "memory") meta.append(chip(T("memoryChip"), "memory"));
    if (k === "tool") meta.append(chip(T("tool"), "sure"));
    if (k === "safety") meta.append(chip(T("safety"), "unsure"));
    if (reply.source && reply.source.kind === "user") {
      meta.append(chip(T("toldMe"), "memory"));
    } else if (reply.source && reply.source.title) {
      const prefix = reply.source.kind === "wikipedia" ? T("wikipedia") : reply.source.kind === "web" ? T("web") : "";
      meta.append(chip(prefix + reply.source.title, "", reply.source.url, T("openSource")));
    }
    if (reply.resolved) meta.append(chip(T("understoodAs") + reply.resolved, "", null));
    if (typeof reply.seconds === "number") meta.append(chip(`${reply.seconds.toFixed(2)} s`, "", null, T("seconds")));

    const copyBtn = el.querySelector('[data-act="copy"]');
    copyBtn.textContent = T("copy");
    evBtn.textContent = T("evidence");
    if (reply.evidence && k !== "about") {
      evBtn.hidden = false;
      evBox.replaceChildren(highlight(reply.evidence, reply.answer || reply.guess));
      evBtn.onclick = () => { evBox.hidden = !evBox.hidden; evBtn.textContent = evBox.hidden ? T("evidence") : T("hideEvidence"); };
    }
    copyBtn.onclick = async (e) => {
      try { await navigator.clipboard.writeText(full); e.target.textContent = T("copied"); }
      catch { e.target.textContent = T("copyFailed"); }
      setTimeout(() => (e.target.textContent = T("copy")), 1200);
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
    delete el.dataset.done;
    const words = text.split(/(\s+)/);
    const step = Math.max(1, Math.ceil(words.length / 40));
    let i = 0;
    const tick = () => {
      el.textContent += words.slice(i, i + step).join("");
      i += step;
      scrollDown(false);
      if (i < words.length) setTimeout(tick, 18);
      else el.dataset.done = "1";
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
      reply = { error: e.message || T("connectionLost") };
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
      li.className = "muted"; li.textContent = T("noMemory");
      list.append(li);
      return;
    }
    for (const it of items) {
      const li = document.createElement("li");
      const s = document.createElement("span"); s.textContent = it.preview;
      const b = document.createElement("button"); b.className = "forget"; b.textContent = T("forget");
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
    $("themeLabel").textContent = dark ? T("lightMode") : T("darkMode");
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
  function renderSuggestions() {
    const box = $("suggestions");
    box.replaceChildren();
    for (const s of T("suggestions")) {
      const b = document.createElement("button");
      b.className = "suggestion"; b.type = "button";
      const t = document.createElement("b"); t.textContent = s.title;
      const d = document.createElement("span"); d.textContent = s.sub;
      b.append(t, d);
      b.onclick = () => send(s.title);
      box.append(b);
    }
  }

  function toggleLanguage() {
    const next = lang === "en" ? "de" : "en";
    storage.set(LANG, next);
    applyLanguage(next);
    renderSidebar(); renderThread(); renderStatus();
  }

  function init() {
    applyLanguage(storage.get(LANG, "en"));
    $("composer").addEventListener("submit", (e) => { e.preventDefault(); send($("input").value); });
    $("input").addEventListener("input", () => { autosize(); updateSend(); });
    $("input").addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey && !e.isComposing) { e.preventDefault(); send($("input").value); }
    });
    $("newChat").onclick = newConversation;
    $("openMemory").onclick = openMemory;
    $("openAbout").onclick = () => $("aboutDialog").showModal();
    $("toggleTheme").onclick = toggleTheme;
    $("toggleLang").onclick = toggleLanguage;
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
