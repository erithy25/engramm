import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { api } from "./api";
import { AssistantMessage } from "./components/AssistantMessage";
import { AboutDialog, MemoryDialog } from "./components/Dialogs";
import { NetworkDialog } from "./components/NetworkDialog";
import { Mark, MenuIcon, SendIcon } from "./components/Icons";
import { PACKS_LINK, packName, Sidebar } from "./components/Sidebar";
import { isLang, type Lang, TEXTS } from "./i18n";
import { load, save, uid } from "./storage";
import type { Conversation, Health, Message, NetworkStatus, StoredReply } from "./types";

const STORE = "engramm.conversations.v1";
const THEME = "engramm.theme";
const LANG = "engramm.lang";
const MAX_MESSAGE = 12000;

const isConversations = (v: unknown): v is Conversation[] =>
  Array.isArray(v) && v.every((c) => typeof c === "object" && c !== null && "id" in c && "messages" in c);
const isTheme = (v: unknown): v is "light" | "dark" => v === "light" || v === "dark";

type Status = { kind: "connecting" } | { kind: "offline" } | { kind: "health"; health: Health };

export function App() {
  const [conversations, setConversations] = useState<Conversation[]>(() => load(STORE, [], isConversations));
  const [activeId, setActiveId] = useState<string | null>(() => conversations[0]?.id ?? null);
  const [lang, setLang] = useState<Lang>(() => load(LANG, "en", isLang));
  const [theme, setTheme] = useState<"light" | "dark" | null>(() => load(THEME, null as "light" | "dark" | null,
    (v): v is "light" | "dark" | null => v === null || isTheme(v)));
  const [status, setStatus] = useState<Status>({ kind: "connecting" });
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [pending, setPending] = useState<string | null>(null);      // conversation waiting for a reply
  const [animateLast, setAnimateLast] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [memoryOpen, setMemoryOpen] = useState(false);
  const [aboutOpen, setAboutOpen] = useState(false);
  const [networkOpen, setNetworkOpen] = useState(false);
  const [network, setNetwork] = useState<NetworkStatus | null>(null);
  const threadRef = useRef<HTMLElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const t = TEXTS[lang];

  // dark like the website unless you chose light (the choice is kept)
  const dark = theme !== "light";
  // desktop app (loaded with ?desktop=1)
  const desktop = useMemo(() => new URLSearchParams(window.location.search).has("desktop"), []);
  const ready = status.kind === "health" && status.health.ready;
  const active = useMemo(() => conversations.find((c) => c.id === activeId) ?? null, [conversations, activeId]);

  useEffect(() => save(STORE, conversations.slice(0, 200)), [conversations]);
  useEffect(() => {
    document.documentElement.lang = lang;
    save(LANG, lang);
  }, [lang]);
  useEffect(() => {
    if (theme) document.documentElement.dataset.theme = theme;
    else delete document.documentElement.dataset.theme;
  }, [theme]);

  // health: poll until ready or failed
  useEffect(() => {
    let stop = false;
    let timer: number | undefined;
    const poll = async () => {
      try {
        const h = await api.health();
        if (stop) return;
        setStatus({ kind: "health", health: h });
        if (h.ready || h.error) return;
      } catch {
        if (stop) return;
        setStatus({ kind: "offline" });
      }
      timer = window.setTimeout(poll, 1500);
    };
    void poll();
    return () => {
      stop = true;
      window.clearTimeout(timer);
    };
  }, []);

  // network channels: shown in the sidebar once the server is ready (hidden when it has none)
  useEffect(() => {
    if (!ready) return;
    api.network().then(setNetwork, () => setNetwork(null));
  }, [ready]);
  const netOn =
    network !== null && network.available && Object.values(network.channels).some((c) => c.enabled);
  const netLabel = network !== null && network.available ? (netOn ? t.netOn : t.netOff) : null;

  // desktop app (loaded with ?desktop=1): source links open in the system browser, not in the app window
  useEffect(() => {
    if (!desktop) return;
    const onClick = (e: MouseEvent) => {
      const target = e.target instanceof Element ? e.target.closest("a[href]") : null;
      if (!(target instanceof HTMLAnchorElement)) return;
      if (!/^https?:\/\//.test(target.href) || target.origin === window.location.origin) return;
      e.preventDefault();
      api.open(target.href).catch(() => undefined);
    };
    document.addEventListener("click", onClick);
    return () => document.removeEventListener("click", onClick);
  }, [desktop]);

  const scrollDown = useCallback((smooth = true) => {
    const el = threadRef.current;
    if (el) el.scrollTo({ top: el.scrollHeight, behavior: smooth ? "smooth" : "auto" });
  }, []);
  useLayoutEffect(() => scrollDown(false), [activeId, scrollDown]);

  const autosize = () => {
    const el = inputRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
  };

  const send = async (raw: string) => {
    const text = raw.trim();
    if (!text || !ready || busy) return;
    let conv = active;
    const now = Date.now();
    if (!conv) {
      conv = { id: uid(), title: text.slice(0, 60), updated: now, messages: [] };
      setActiveId(conv.id);
    }
    const convId = conv.id;
    const userMsg: Message = { role: "user", text };
    const withUser: Conversation = { ...conv, updated: now, messages: [...conv.messages, userMsg] };
    setConversations((cur) => [withUser, ...cur.filter((c) => c.id !== convId)]);
    setInput("");
    window.setTimeout(autosize, 0);
    setBusy(true);
    setPending(convId);
    setAnimateLast(true);
    let reply: StoredReply;
    try {
      reply = await api.chat(convId, text);
    } catch (e) {
      reply = { error: e instanceof Error ? e.message : t.connectionLost };
    }
    setConversations((cur) =>
      cur.map((c) =>
        c.id === convId
          ? { ...c, updated: Date.now(), messages: [...c.messages, { role: "assistant", reply }] }
          : c,
      ),
    );
    setPending(null);
    setBusy(false);
    window.setTimeout(() => {
      scrollDown();
      inputRef.current?.focus();
    }, 0);
  };

  const newChat = () => {
    setActiveId(null);
    setSidebarOpen(false);
    setAnimateLast(false);
    inputRef.current?.focus();
  };
  const openChat = (id: string) => {
    setActiveId(id);
    setSidebarOpen(false);
    setAnimateLast(false);
  };
  const deleteChat = (id: string) => {
    setConversations((cur) => cur.filter((c) => c.id !== id));
    if (activeId === id) setActiveId(null);
  };

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.shiftKey && e.key.toLowerCase() === "o") {
        e.preventDefault();
        newChat();
      }
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  });

  const statusView = (() => {
    if (status.kind === "connecting") return { cls: "status", text: "…", title: "" };
    if (status.kind === "offline") return { cls: "status error", text: t.offline, title: "" };
    const h = status.health;
    if (h.error) return { cls: "status error", text: t.loadError, title: h.error };
    if (!h.ready) return { cls: "status", text: t.loading, title: "" };
    const more = t.sentences(((h.sentences ?? 0) / 1e6).toFixed(1)) + (h.mode === "quick" ? t.quick : "");
    return { cls: "status ready", text: t.ready, more, title: h.mode === "quick" ? t.quickTitle : "" };
  })();

  const health = status.kind === "health" ? status.health : null;
  const packLabel = desktop ? packName(health?.pack?.name ?? "") : null;
  const loadError = health?.error ?? null;

  const messages = active?.messages ?? [];
  const lastAssistant = messages.reduce((acc, m, i) => (m.role === "assistant" ? i : acc), -1);

  return (
    <div className="app" id="app">
      <Sidebar
        t={t}
        open={sidebarOpen}
        conversations={conversations}
        activeId={activeId}
        dark={dark}
        onNew={newChat}
        onOpen={openChat}
        onDelete={deleteChat}
        onClose={() => setSidebarOpen(false)}
        onMemory={() => setMemoryOpen(true)}
        netLabel={netLabel}
        netOn={netOn}
        onNetwork={() => setNetworkOpen(true)}
        packLabel={packLabel}
        onAbout={() => setAboutOpen(true)}
        onTheme={() => {
          const next = dark ? "light" : "dark";
          setTheme(next);
          save(THEME, next);
        }}
        onLanguage={() => setLang(lang === "en" ? "de" : "en")}
      />
      {sidebarOpen && <div className="scrim" id="scrim" onClick={() => setSidebarOpen(false)} />}

      <main className="main">
        <header className="topbar">
          <button className="icon-btn only-mobile" id="openSidebar" type="button" aria-label={t.openSidebar}
                  onClick={() => setSidebarOpen(true)}>
            <MenuIcon />
          </button>
          <div className="model-pill" title={t.pillTitle}>
            <span className="pill-word">engramm</span> <span className="muted">{t.pill.replace(/^·\s*/, "")}</span>
          </div>
          <div className={statusView.cls} id="status" title={statusView.title}>
            <span className="dot" />
            <span id="statusText">
              {statusView.text}
              {"more" in statusView && <span className="status-more">{statusView.more}</span>}
            </span>
          </div>
        </header>

        <section className="thread" id="thread" aria-live="polite" ref={threadRef}>
          {messages.length === 0 && pending === null && (
            <div className="empty" id="empty">
              <div className="empty-mark" aria-hidden="true">
                <Mark />
              </div>
              <h1>{t.emptyTitle}</h1>
              <p className="muted">{t.emptySub}</p>
              {loadError ? (
                <div className="load-error" id="loadError" role="alert">
                  <b>{t.loadErrorTitle}</b>
                  <code>{loadError}</code>
                  <p className="muted">{t.loadErrorHint}</p>
                  {desktop && (
                    <a className="pill-link" href={PACKS_LINK}>
                      {t.openPacks}
                    </a>
                  )}
                </div>
              ) : (
                <div className="suggestions" id="suggestions">
                  {t.suggestions.map((s) => (
                    <button key={s.title} className="suggestion" type="button" onClick={() => void send(s.title)}>
                      <b>{s.title}</b>
                      <span>{s.sub}</span>
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}
          {messages.map((m, i) =>
            m.role === "user" ? (
              <article className="msg user" key={i}>
                <div className="bubble">{m.text}</div>
              </article>
            ) : (
              <AssistantMessage
                key={i}
                reply={m.reply}
                t={t}
                animate={animateLast && i === lastAssistant}
                onTyped={() => scrollDown(false)}
              />
            ),
          )}
          {pending !== null && pending === activeId && <AssistantMessage reply={null} animate={false} t={t} />}
        </section>

        <footer className="composer-wrap">
          <form
            className="composer"
            id="composer"
            autoComplete="off"
            onSubmit={(e) => {
              e.preventDefault();
              void send(input);
            }}
          >
            <textarea
              id="input"
              ref={inputRef}
              rows={1}
              placeholder={t.placeholder}
              aria-label={t.message}
              maxLength={MAX_MESSAGE}
              value={input}
              autoFocus
              onChange={(e) => {
                setInput(e.target.value);
                autosize();
              }}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
                  e.preventDefault();
                  void send(input);
                }
              }}
            />
            <button type="submit" className="send" id="send" aria-label={t.send}
                    disabled={!ready || busy || !input.trim()}>
              <SendIcon />
            </button>
          </form>
          <p className="hint muted">{t.hint}</p>
        </footer>
      </main>

      <MemoryDialog open={memoryOpen} onClose={() => setMemoryOpen(false)} t={t} />
      <AboutDialog open={aboutOpen} onClose={() => setAboutOpen(false)} t={t} />
      <NetworkDialog open={networkOpen} onClose={() => setNetworkOpen(false)} t={t} onStatus={setNetwork} />
    </div>
  );
}

