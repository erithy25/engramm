import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { api } from "./api";
import { AssistantMessage } from "./components/AssistantMessage";
import { AboutDialog, MemoryDialog } from "./components/Dialogs";
import { NetworkDialog } from "./components/NetworkDialog";
import { MenuIcon, SendIcon } from "./components/Icons";
import { Sidebar } from "./components/Sidebar";
import { isLang, type Lang, TEXTS } from "./i18n";
import { load, save, uid } from "./storage";
import type { Conversation, Health, Message, ModelId, ModelInfo, NetworkStatus, StoredReply } from "./types";

const STORE = "engramm.conversations.v1";
const THEME = "engramm.theme";
const LANG = "engramm.lang";
const MODEL = "engramm.model";
const MAX_MESSAGE = 12000;

const isConversations = (v: unknown): v is Conversation[] =>
  Array.isArray(v) && v.every((c) => typeof c === "object" && c !== null && "id" in c && "messages" in c);
const isTheme = (v: unknown): v is "light" | "dark" => v === "light" || v === "dark";
const isModelId = (v: unknown): v is ModelId => v === "engramm" || v === "sela-1" || v === "sela-2";

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
  // null until known: the page's stored choice, else the server's (the desktop app starts with empty page storage)
  const [model, setModel] = useState<ModelId | null>(() =>
    load(MODEL, null as ModelId | null, (v): v is ModelId | null => v === null || isModelId(v)));
  const [models, setModels] = useState<ModelInfo[] | null>(null);
  const [pollRound, setPollRound] = useState(0);                     // a new round of health polling (after "Try again")
  const [retrying, setRetrying] = useState(false);
  const [copied, setCopied] = useState(false);
  const threadRef = useRef<HTMLElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const t = TEXTS[lang];

  const systemDark = typeof matchMedia === "function" && matchMedia("(prefers-color-scheme: dark)").matches;
  const dark = theme ? theme === "dark" : systemDark;
  const ready = status.kind === "health" && status.health.ready;
  const serverUp = status.kind === "health";
  const selaAvailable = models?.find((m) => m.id === "sela-1")?.available === true;
  const sela2Available = models?.find((m) => m.id === "sela-2")?.available === true;
  // the chosen model; Sela-1 only where the app ships it (a saved choice survives builds without it)
  const activeModel: ModelId =
    model === "sela-1" && selaAvailable ? "sela-1" : model === "sela-2" && sela2Available ? "sela-2" : "engramm";
  const sela = activeModel === "sela-1";
  const sela2 = activeModel === "sela-2";
  // Sela-1 and Sela-2 write while ENGRAMM's index is still loading (Sela-2 then chats without sources)
  const canSend = sela || sela2 ? serverUp : ready;
  const active = useMemo(() => conversations.find((c) => c.id === activeId) ?? null, [conversations, activeId]);

  useEffect(() => save(STORE, conversations.slice(0, 200)), [conversations]);
  useEffect(() => {
    if (model !== null) save(MODEL, model);
  }, [model]);
  // which models this server offers (an older server without /api/models: ENGRAMM only)
  useEffect(() => {
    if (!serverUp) return;
    api.models().then(
      (r) => {
        setModels(r.models);
        setModel((m) => m ?? (isModelId(r.last) ? r.last : "engramm"));
      },
      () => setModels([]),
    );
  }, [serverUp, ready]);
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
  }, [pollRound]);

  const loadError = status.kind === "health" ? status.health.error : null;
  const retryLoad = async () => {
    setRetrying(true);
    try {
      setStatus({ kind: "health", health: await api.reload() });
    } catch {
      // the next health poll shows what is wrong
    }
    setRetrying(false);
    setCopied(false);
    setPollRound((n) => n + 1);
  };
  const copyError = async () => {
    if (!loadError) return;
    try {
      await navigator.clipboard.writeText(loadError);
      setCopied(true);
    } catch {
      // no clipboard (an old webview): the text is selectable
    }
  };

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
    if (!new URLSearchParams(window.location.search).has("desktop")) return;
    const onClick = (e: MouseEvent) => {
      const target = e.target instanceof Element ? e.target.closest("a[href]") : null;
      if (!(target instanceof HTMLAnchorElement)) return;
      if (!/^https?:\/\//.test(target.href) || target.origin === window.location.origin) return;
      e.preventDefault();
      api.open(target.href).catch(() => undefined);
    };
    document.addEventListener("click", onClick);
    return () => document.removeEventListener("click", onClick);
  }, []);

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
    if (!text || !canSend || busy) return;
    const used = activeModel;
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
      reply = await api.chat(convId, text, used);
    } catch (e) {
      reply = { error: e instanceof Error ? e.message : t.connectionLost };
    }
    setConversations((cur) =>
      cur.map((c) =>
        c.id === convId
          ? { ...c, updated: Date.now(), messages: [...c.messages, { role: "assistant", reply, model: used }] }
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
          <div className="model-pill" id="modelPill" title={sela ? t.pillSelaTitle : sela2 ? t.pillSela2Title : t.pillTitle}>
            {sela ? "Sela-1 135M" : sela2 ? "Sela-2" : "ENGRAMM"}{" "}
            <span className="muted">{sela ? t.pillSela : sela2 ? t.pillSela2 : t.pill}</span>
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
          {loadError && !sela && !sela2 && (
            <div className="load-error" id="loadError" role="alert">
              <b>{t.loadErrorTitle}</b>
              <p className="muted">
                {t.loadErrorHelp}
                {(selaAvailable || sela2Available) && <> {t.loadErrorSela}</>}
              </p>
              <pre id="loadErrorText">{loadError}</pre>
              <div className="load-error-actions">
                <button type="button" className="btn" id="retryLoad" disabled={retrying} onClick={() => void retryLoad()}>
                  {retrying ? t.retrying : t.retry}
                </button>
                <button type="button" className="btn ghost" id="copyError" onClick={() => void copyError()}>
                  {copied ? t.copied : t.copyError}
                </button>
              </div>
            </div>
          )}
          {messages.length === 0 && pending === null && (
            <div className="empty" id="empty">
              <img src="./logo.svg" alt="" className="empty-logo" width={72} height={72} />
              <h1>{t.emptyTitle}</h1>
              <p className="muted">{sela ? t.emptySubSela : sela2 ? t.emptySubSela2 : t.emptySub}</p>
              <div className="suggestions" id="suggestions">
                {(sela ? t.suggestionsSela : sela2 ? t.suggestionsSela2 : t.suggestions).map((s) => (
                  <button key={s.title} className="suggestion" type="button" onClick={() => void send(s.title)}>
                    <b>{s.title}</b>
                    <span>{s.sub}</span>
                  </button>
                ))}
              </div>
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
              placeholder={sela ? t.placeholderSela : sela2 ? t.placeholderSela2 : t.placeholder}
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
            <select
              id="model"
              className="model-select"
              aria-label={t.modelLabel}
              title={t.modelLabel}
              value={activeModel}
              disabled={busy}
              onChange={(e) => {
                const v = e.target.value;
                if (isModelId(v)) setModel(v);
                inputRef.current?.focus();
              }}
            >
              <option value="engramm">{t.modelEngramm}</option>
              <option value="sela-1" disabled={!selaAvailable}>
                {selaAvailable ? t.modelSela : t.modelSelaMissing}
              </option>
              <option value="sela-2" disabled={!sela2Available}>
                {sela2Available ? t.modelSela2 : t.modelSela2Missing}
              </option>
            </select>
            <button type="submit" className="send" id="send" aria-label={t.send}
                    disabled={!canSend || busy || !input.trim()}>
              <SendIcon />
            </button>
          </form>
          <p className="hint muted" id="hint">{sela ? t.hintSela : sela2 ? t.hintSela2 : t.hint}</p>
        </footer>
      </main>

      <MemoryDialog open={memoryOpen} onClose={() => setMemoryOpen(false)} t={t} />
      <AboutDialog open={aboutOpen} onClose={() => setAboutOpen(false)} t={t} />
      <NetworkDialog open={networkOpen} onClose={() => setNetworkOpen(false)} t={t} onStatus={setNetwork} />
    </div>
  );
}

