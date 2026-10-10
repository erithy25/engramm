import { type ReactElement, useEffect, useRef, useState } from "react";
import type { Texts } from "../i18n";
import { isError, type StoredReply } from "../types";
import { Mark } from "./Icons";

interface Props {
  reply: StoredReply | null; // null while waiting
  animate: boolean;
  t: Texts;
  onTyped?: () => void;
}

function Chip(props: { text: string; cls?: string; href?: string | null; title?: string }) {
  const cls = "chip" + (props.cls ? ` ${props.cls}` : "");
  if (props.href) {
    return (
      <a className={cls} href={props.href} target="_blank" rel="noopener noreferrer" title={props.title}>
        {props.text}
      </a>
    );
  }
  return (
    <span className={cls} title={props.title}>
      {props.text}
    </span>
  );
}

function Highlighted({ sentence, part }: { sentence: string; part: string | null }) {
  const i = part ? sentence.toLowerCase().indexOf(part.toLowerCase()) : -1;
  if (!part || i < 0) return <>{sentence}</>;
  return (
    <>
      {sentence.slice(0, i)}
      <mark>{sentence.slice(i, i + part.length)}</mark>
      {sentence.slice(i + part.length)}
    </>
  );
}

/** Types the reply out word by word; ``data-done`` marks the end (the browser test waits for it). */
function useTypedText(full: string, animate: boolean, onTyped?: () => void): [string, boolean] {
  const [shown, setShown] = useState(animate ? "" : full);
  const [done, setDone] = useState(!animate);
  const onTypedRef = useRef(onTyped);
  onTypedRef.current = onTyped;
  useEffect(() => {
    if (!animate) {
      setShown(full);
      setDone(true);
      return;
    }
    const words = full.split(/(\s+)/);
    const step = Math.max(1, Math.ceil(words.length / 40));
    let i = 0;
    let timer: number | undefined;
    setShown("");
    setDone(false);
    const tick = () => {
      i += step;
      setShown(words.slice(0, i).join(""));
      onTypedRef.current?.();
      if (i < words.length) timer = window.setTimeout(tick, 18);
      else setDone(true);
    };
    tick();
    return () => window.clearTimeout(timer);
  }, [full, animate]);
  return [shown, done];
}

export function AssistantMessage({ reply, animate, t, onTyped }: Props) {
  const [showEvidence, setShowEvidence] = useState(false);
  const [copyLabel, setCopyLabel] = useState<string | null>(null);
  const full = reply && !isError(reply) ? reply.text : "";
  const [shown, done] = useTypedText(full, animate && reply !== null && !isError(reply), onTyped);

  if (reply === null) {
    return (
      <article className="msg assistant">
        <span className="avatar" aria-hidden="true">
          <Mark />
        </span>
        <div className="bubble">
          <div className="text">
            <span className="typing">
              <i />
              <i />
              <i />
            </span>
          </div>
        </div>
      </article>
    );
  }
  if (isError(reply)) {
    return (
      <article className="msg assistant">
        <span className="avatar" aria-hidden="true">
          <Mark />
        </span>
        <div className="bubble">
          <div className="text" data-done="1">
            <span className="error-text">{reply.error}</span>
          </div>
        </div>
      </article>
    );
  }
  const k = reply.kind;
  const chips: ReactElement[] = [];
  if (k === "answer" && (reply.via === "lookup" || reply.via === "atlas")) {
    chips.push(<Chip key="s" text={t.sure} cls="sure" title={t.sureTitle} />);
  }
  if (k === "unknown" && reply.guess) chips.push(<Chip key="u" text={t.unsure} cls="unsure" title={t.unsureTitle} />);
  if (k === "learned") chips.push(<Chip key="l" text={t.learned} cls="memory" />);
  if (k === "forgot") chips.push(<Chip key="f" text={t.forgot} cls="memory" />);
  if (k === "memory") chips.push(<Chip key="m" text={t.memoryChip} cls="memory" />);
  if (k === "tool") chips.push(<Chip key="t" text={t.tool} cls="sure" />);
  if (k === "safety") chips.push(<Chip key="h" text={t.safety} cls="unsure" />);
  if (k === "writing") chips.push(<Chip key="w" text={t.writing} cls="memory" />);
  const src = reply.source;
  if (src?.kind === "user") {
    chips.push(<Chip key="src" text={t.toldMe} cls="memory" />);
  } else if (src?.title) {
    const prefix =
      src.kind === "wikipedia" || src.kind === "shelf"
        ? t.wikipedia
        : src.kind === "web"
          ? t.web
          : src.kind === "feed"
            ? t.news
            : "";
    const name = src.kind === "web" && src.site ? `${src.title} (${src.site})` : src.title;
    const when = src.as_of ? ` · ${t.asOf}${src.as_of}` : "";
    chips.push(<Chip key="src" text={prefix + name + when} href={src.url} title={t.openSource} />);
    if (src.kind === "shelf" || src.kind === "feed" || src.kind === "web") {
      chips.push(<Chip key="via" text={t.via[src.kind]} cls="net" />);
    }
  }
  if (reply.resolved) chips.push(<Chip key="r" text={t.understoodAs + reply.resolved} />);
  if (typeof reply.seconds === "number") {
    chips.push(<Chip key="sec" text={`${reply.seconds.toFixed(2)} s`} cls="sec" title={t.seconds} />);
  }
  const hasEvidence = Boolean(reply.evidence) && k !== "about";

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(full);
      setCopyLabel(t.copied);
    } catch {
      setCopyLabel(t.copyFailed);
    }
    window.setTimeout(() => setCopyLabel(null), 1200);
  };

  return (
    <article className="msg assistant">
      <span className="avatar" aria-hidden="true">
        <Mark />
      </span>
      <div className="bubble">
        <div className="text" {...(done ? { "data-done": "1" } : {})}>
          {shown}
        </div>
        <div className="meta">{chips}</div>
        <div className="actions">
          <button className="mini" data-act="copy" onClick={copy} type="button">
            {copyLabel ?? t.copy}
          </button>
          {hasEvidence && (
            <button className="mini" data-act="evidence" type="button" onClick={() => setShowEvidence((v) => !v)}>
              {showEvidence ? t.hideEvidence : t.evidence}
            </button>
          )}
        </div>
        {hasEvidence && showEvidence && reply.evidence && (
          <blockquote className="evidence">
            <Highlighted sentence={reply.evidence} part={reply.answer ?? reply.guess} />
          </blockquote>
        )}
      </div>
    </article>
  );
}
