import { useCallback, useEffect, useState } from "react";
import { api } from "../api";
import type { Texts } from "../i18n";
import type { ChannelChange, ChannelName, NetworkLogEntry, NetworkStatus } from "../types";
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

/** The three network channels (all off until switched on), the Tor state and the network log. */
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
    const torMissing = net.tor === "unavailable";
    const selected = net.feeds.filter((f) => f.selected).map((f) => f.id);
    const toggleFeed = (id: string, on: boolean) => {
      const next = on ? [...selected, id] : selected.filter((x) => x !== id);
      void change({ channel: "feeds", feeds: next }, `feed:${id}`);
    };
    const toggle = (channel: ChannelName) => (on: boolean) => void change({ channel, enabled: on }, channel);
    const usesTor = (ch.messenger.enabled && ch.messenger.tor !== false) || (ch.shelf.enabled && ch.shelf.tor === true);
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
          {ch.shelf.enabled && (
            <label className="check">
              <input type="checkbox" id="netShelfTor" checked={ch.shelf.tor === true}
                     disabled={busy !== null || (torMissing && ch.shelf.tor !== true)}
                     onChange={(e) => void change({ channel: "shelf", tor: e.target.checked }, "shelf-tor")} />
              <span>{t.shelfTor}</span>
            </label>
          )}
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

        <section className="channel" data-channel="messenger">
          <div className="channel-head">
            <div>
              <b>{t.messengerTitle}</b>
              <p className="muted">{t.messengerDesc}</p>
            </div>
            <Switch id="netMessenger" label={t.messengerTitle} checked={ch.messenger.enabled} disabled={busy !== null}
                    onChange={toggle("messenger")} />
          </div>
          {ch.messenger.enabled && (
            <>
              <label className="check">
                <input type="checkbox" id="netMessengerTor" checked={ch.messenger.tor !== false}
                       disabled={busy !== null}
                       onChange={(e) => void change({ channel: "messenger", tor: e.target.checked }, "messenger-tor")} />
                <span>{t.messengerTor}</span>
              </label>
              {ch.messenger.tor === false && <p className="channel-info warn-text">{t.messengerDirect}</p>}
            </>
          )}
        </section>

        {(usesTor || torMissing) && (
          <p className={"channel-info" + (net.tor.startsWith("failed") ? " bad-text" : "")} id="torState">
            {t.torState(net.tor)}
          </p>
        )}

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
