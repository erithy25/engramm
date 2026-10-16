import { useCallback, useEffect, useState } from "react";
import { api } from "../api";
import type { Texts } from "../i18n";
import { type ChannelChange, type ChannelName, type NetworkLogEntry, type NetworkStatus, SEARCH_ENGINES,
         type SearchEngine } from "../types";
import { Modal } from "./Dialogs";

const POLL_MS = 3000;

function message(e: unknown): string {
  return e instanceof Error ? e.message : String(e);
}

function size(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1 << 20) return `${(n / 1024).toFixed(1)} kB`;
  return `${(n / (1 << 20)).toFixed(1)} MB`;
}

function time(ts: string): string {
  const d = new Date(ts);
  return Number.isNaN(d.getTime()) ? ts : d.toLocaleString(undefined, { dateStyle: "short", timeStyle: "medium" });
}

function Switch(props: { id: string; label: string; checked: boolean; disabled: boolean;
                         onChange: (on: boolean) => void }) {
  return (
    <label className="switch" title={props.label}>
      <input
        id={props.id}
        type="checkbox"
        role="switch"
        aria-label={props.label}
        checked={props.checked}
        disabled={props.disabled}
        onChange={(e) => props.onChange(e.target.checked)}
      />
      <span aria-hidden="true" />
    </label>
  );
}

function LogTable({ log, t }: { log: NetworkLogEntry[]; t: Texts }) {
  if (log.length === 0) return <p className="muted" id="netLogEmpty">{t.netLogEmpty}</p>;
  const names: Record<string, string> = t.channelNames;
  return (
    <div className="net-log-wrap">
      <table className="net-log" id="netLog">
        <thead>
          <tr>
            {t.netLogHead.map((h) => (
              <th key={h}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {log.map((x, i) => (
            <tr key={`${x.ts}-${i}`} className={x.ok ? undefined : "failed"} title={x.error ?? x.via}>
              <td>{time(x.ts)}</td>
              <td>{names[x.channel] ?? x.channel}</td>
              <td>{x.host}</td>
              <td>{x.what}</td>
              <td>{x.ok ? size(x.bytes) : (x.error ?? "–")}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function isEngine(v: string): v is SearchEngine {
  return (SEARCH_ENGINES as readonly string[]).includes(v);
}

/** The Brave Search API key: typed here, sent once, never shown again (the server only says whether one is set). */
function BraveKey(props: { isSet: boolean; busy: boolean; t: Texts; onSave: (key: string) => void }) {
  const { isSet, busy, t, onSave } = props;
  const [key, setKey] = useState("");
  const valid = /^[\x21-\x7e]{8,200}$/.test(key.trim());
  return (
    <div className="field">
      <label htmlFor="netBraveKey">{t.braveKey}</label>
      {isSet ? (
        <div className="field-row">
          <span className="key-set" id="netBraveKeySet">{t.braveKeySet}</span>
          <button className="mini" type="button" id="netBraveKeyRemove" disabled={busy} onClick={() => onSave("")}>
            {t.braveKeyRemove}
          </button>
        </div>
      ) : (
        <form
          className="field-row"
          onSubmit={(e) => {
            e.preventDefault();
            if (!valid) return;
            onSave(key.trim());
            setKey("");
          }}
        >
          <input id="netBraveKey" type="password" autoComplete="off" spellCheck={false} value={key}
                 placeholder="BSA…" disabled={busy} onChange={(e) => setKey(e.target.value)} />
          <button className="mini" type="submit" disabled={busy || !valid}>{t.braveKeySave}</button>
        </form>
      )}
      <p className="muted field-hint">{t.braveKeyHint}</p>
    </div>
  );
}

/** The three network channels (all off until switched on) and the network log. */
export function NetworkDialog(props: { open: boolean; onClose: () => void; t: Texts;
                                       onStatus: (s: NetworkStatus) => void }) {
  const { open, onClose, t, onStatus } = props;
  const [net, setNet] = useState<NetworkStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const apply = useCallback(
    (s: NetworkStatus) => {
      setNet(s);
      onStatus(s);
    },
    [onStatus],
  );

  useEffect(() => {
    if (!open) return;
    let stop = false;
    let timer: number | undefined;
    const poll = async () => {
      try {
        const s = await api.network();
        if (stop) return;
        apply(s);
        setError(null);
      } catch (e) {
        if (stop) return;
        setError(message(e));
      }
      timer = window.setTimeout(poll, POLL_MS);
    };
    void poll();
    return () => {
      stop = true;
      window.clearTimeout(timer);
    };
  }, [open, apply]);

  const change = async (c: ChannelChange, key: string) => {
    setBusy(key);
    try {
      apply(await api.setNetwork(c));
      setError(null);
    } catch (e) {
      setError(message(e));
    } finally {
      setBusy(null);
    }
  };

  const refresh = async () => {
    setBusy("refresh");
    try {
      apply(await api.refreshFeeds());
      setError(null);
    } catch (e) {
      setError(message(e));
    } finally {
      setBusy(null);
    }
  };

  const body = () => {
    if (net === null) return error ? null : <p className="muted">{t.netLoading}</p>;
    if (!net.available) return <p id="netUnavailable">{t.netUnavailable}</p>;
    const ch = net.channels;
    const selected = net.feeds.filter((f) => f.selected).map((f) => f.id);
    const toggleFeed = (id: string, on: boolean) => {
      const next = on ? [...selected, id] : selected.filter((x) => x !== id);
      void change({ channel: "feeds", feeds: next }, `feed:${id}`);
    };
    const toggle = (channel: ChannelName) => (on: boolean) => void change({ channel, enabled: on }, channel);
    const engine: SearchEngine = ch.search.engine ?? "auto";
    const keySet = ch.search.brave_key_set === true;
    return (
      <>
        <section className="channel" data-channel="shelf">
          <div className="channel-head">
            <div>
              <b>{t.shelfTitle}</b>
              <p className="muted">{t.shelfDesc}</p>
            </div>
            <Switch id="netShelf" label={t.shelfTitle} checked={ch.shelf.enabled}
                    disabled={busy !== null || (!net.shelf && !ch.shelf.enabled)} onChange={toggle("shelf")} />
          </div>
          <p className="channel-info">
            {net.shelf ? t.shelfInfo(net.shelf.docs.toLocaleString(), net.shelf.date) : t.shelfMissing}
          </p>
        </section>

        <section className="channel" data-channel="feeds">
          <div className="channel-head">
            <div>
              <b>{t.feedsTitle}</b>
              <p className="muted">{t.feedsDesc}</p>
            </div>
            <Switch id="netFeeds" label={t.feedsTitle} checked={ch.feeds.enabled} disabled={busy !== null}
                    onChange={toggle("feeds")} />
          </div>
          {ch.feeds.enabled && (
            <div className="feed-list" id="feedList">
              {net.feeds.map((f) => {
                const st = net.feed_state[f.id];
                return (
                  <label className="check" key={f.id}>
                    <input type="checkbox" checked={f.selected} disabled={busy !== null}
                           onChange={(e) => toggleFeed(f.id, e.target.checked)} />
                    <span>
                      {f.title}
                      {f.selected && st && !st.ok && (
                        <span className="bad-text" title={st.error}> · {t.feedFailed}</span>
                      )}
                    </span>
                  </label>
                );
              })}
            </div>
          )}
          <p className="channel-info">
            <span id="feedItems">{t.feedsItems(net.feed_items)}</span>
            <button className="mini" type="button" id="refreshFeeds" onClick={() => void refresh()}
                    disabled={!ch.feeds.enabled || busy !== null || selected.length === 0}>
              {busy === "refresh" ? t.refreshing : t.refreshFeeds}
            </button>
          </p>
        </section>

        <section className="channel" data-channel="search">
          <div className="channel-head">
            <div>
              <b>{t.searchTitle}</b>
              <p className="muted">{t.searchDesc}</p>
            </div>
            <Switch id="netSearch" label={t.searchTitle} checked={ch.search.enabled} disabled={busy !== null}
                    onChange={toggle("search")} />
          </div>
          <p className="channel-info warn-text" id="searchPrivacy">{t.searchPrivacy}</p>
          <div className="search-options">
            <div className="field">
              <label htmlFor="netEngine">{t.searchEngine}</label>
              <select
                id="netEngine"
                value={engine}
                disabled={busy !== null}
                onChange={(e) => {
                  const v = e.target.value;
                  if (isEngine(v)) void change({ channel: "search", engine: v }, "engine");
                }}
              >
                {SEARCH_ENGINES.map((x) => (
                  <option key={x} value={x}>
                    {t.searchEngines[x]}
                  </option>
                ))}
              </select>
              {engine === "brave" && !keySet && <p className="field-hint bad-text">{t.braveMissing}</p>}
            </div>
            <BraveKey isSet={keySet} busy={busy !== null} t={t}
                      onSave={(key) => void change({ channel: "search", brave_key: key }, "brave-key")} />
          </div>
        </section>

        <h3 className="net-log-title">{t.netLog}</h3>
        <LogTable log={net.log} t={t} />
      </>
    );
  };

  return (
    <Modal id="networkDialog" open={open} onClose={onClose} title={t.network} closeLabel={t.close} wide>
      <p className="muted">{t.netIntro}</p>
      {error && <p className="error-text">{error}</p>}
      {body()}
    </Modal>
  );
}
