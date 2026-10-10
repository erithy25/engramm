import type { Texts } from "../i18n";
import type { Conversation } from "../types";
import { GlobeIcon, InfoIcon, ListIcon, Mark, MoonIcon, NetworkIcon, PlusIcon } from "./Icons";

interface Props {
  t: Texts;
  open: boolean;
  conversations: Conversation[];
  activeId: string | null;
  dark: boolean;
  onNew: () => void;
  onOpen: (id: string) => void;
  onDelete: (id: string) => void;
  onClose: () => void;
  onMemory: () => void;
  /** "on"/"off" when the server has network channels; null hides the entry */
  netLabel: string | null;
  netOn: boolean;
  onNetwork: () => void;
  onAbout: () => void;
  onTheme: () => void;
  onLanguage: () => void;
}

export function Sidebar(p: Props) {
  const today = new Date().toDateString();
  const groups: [string, Conversation[]][] = [
    [p.t.today, p.conversations.filter((c) => new Date(c.updated).toDateString() === today)],
    [p.t.earlier, p.conversations.filter((c) => new Date(c.updated).toDateString() !== today)],
  ];
  return (
    <aside className={"sidebar" + (p.open ? " open" : "")} id="sidebar" aria-label={p.t.conversations}>
      <div className="brand">
        <Mark />
        <span className="brand-name">engramm</span>
        <button className="icon-btn only-mobile" id="closeSidebar" type="button" aria-label={p.t.closeSidebar}
                onClick={p.onClose}>
          ✕
        </button>
      </div>
      <button className="new-chat" id="newChat" type="button" onClick={p.onNew}>
        <PlusIcon />
        <span>{p.t.newChat}</span>
      </button>
      <nav className="conversations" id="conversations" aria-label={p.t.history}>
        {groups.map(([label, list]) =>
          list.length === 0 ? null : (
            <div key={label}>
              <div className="conv-group">{label}</div>
              {list.map((c) => (
                <div
                  key={c.id}
                  className={"conv" + (c.id === p.activeId ? " active" : "")}
                  role="button"
                  tabIndex={0}
                  onClick={() => p.onOpen(c.id)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") p.onOpen(c.id);
                  }}
                >
                  <span className="conv-title">{c.title || p.t.untitled}</span>
                  <button
                    className="conv-del"
                    type="button"
                    title={p.t.deleteChat}
                    aria-label={p.t.deleteChat}
                    onClick={(e) => {
                      e.stopPropagation();
                      p.onDelete(c.id);
                    }}
                  >
                    ✕
                  </button>
                </div>
              ))}
            </div>
          ),
        )}
      </nav>
      <div className="sidebar-foot">
        <button className="side-link" id="openMemory" type="button" onClick={p.onMemory}>
          <ListIcon />
          <span>{p.t.memory}</span>
        </button>
        {p.netLabel !== null && (
          <button className="side-link" id="openNetwork" type="button" onClick={p.onNetwork}>
            <NetworkIcon />
            <span>
              {p.t.network} · <span className={p.netOn ? "net-on" : "muted"} id="netLabel">{p.netLabel}</span>
            </span>
          </button>
        )}
        <button className="side-link" id="toggleTheme" type="button" onClick={p.onTheme}>
          <MoonIcon />
          <span id="themeLabel">{p.dark ? p.t.lightMode : p.t.darkMode}</span>
        </button>
        <button className="side-link" id="toggleLang" type="button" onClick={p.onLanguage}>
          <GlobeIcon />
          <span>{p.t.otherLanguage}</span>
        </button>
        <button className="side-link" id="openAbout" type="button" onClick={p.onAbout}>
          <InfoIcon />
          <span>{p.t.about}</span>
        </button>
      </div>
    </aside>
  );
}
