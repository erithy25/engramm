import { type ReactNode, useEffect, useRef, useState } from "react";
import { api } from "../api";
import type { Texts } from "../i18n";
import type { MemoryItem } from "../types";

function Modal(props: { id: string; open: boolean; onClose: () => void; title: string; closeLabel: string;
                        children: ReactNode }) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const d = ref.current;
    if (!d) return;
    if (props.open && !d.open) d.showModal();
    if (!props.open && d.open) d.close();
  }, [props.open]);
  return (
    <dialog
      id={props.id}
      ref={ref}
      className="dialog"
      onClose={props.onClose}
      onClick={(e) => {
        if (e.target === ref.current) props.onClose();
      }}
    >
      <div className="dialog-head">
        <h2>{props.title}</h2>
        <button className="icon-btn" type="button" aria-label={props.closeLabel} onClick={props.onClose}>
          ✕
        </button>
      </div>
      {props.children}
    </dialog>
  );
}

export function MemoryDialog({ open, onClose, t }: { open: boolean; onClose: () => void; t: Texts }) {
  const [items, setItems] = useState<MemoryItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    setItems(null);
    setError(null);
    api.memory().then(setItems, (e: unknown) => setError(e instanceof Error ? e.message : String(e)));
  }, [open]);

  const forget = async (source: string) => {
    setBusy(source);
    try {
      await api.forget(source);
      setItems((cur) => (cur ?? []).filter((i) => i.source !== source));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(null);
    }
  };

  return (
    <Modal id="memoryDialog" open={open} onClose={onClose} title={t.memory} closeLabel={t.close}>
      <p className="muted">{t.memorySub}</p>
      <ul className="memory-list" id="memoryList">
        {error && <li>{error}</li>}
        {items !== null && items.length === 0 && <li className="muted">{t.noMemory}</li>}
        {items?.map((it) => (
          <li key={it.source}>
            <span>{it.preview}</span>
            <button className="forget" type="button" disabled={busy === it.source} onClick={() => forget(it.source)}>
              {t.forget}
            </button>
          </li>
        ))}
      </ul>
    </Modal>
  );
}

export function AboutDialog({ open, onClose, t }: { open: boolean; onClose: () => void; t: Texts }) {
  return (
    <Modal id="aboutDialog" open={open} onClose={onClose} title={t.about} closeLabel={t.close}>
      <p>
        {t.aboutIntroBefore}
        <b>{t.aboutIntroBold}</b>
        {t.aboutIntroAfter}
      </p>
      <ul className="about-list">
        <li>{t.about1}</li>
        <li>{t.about2}</li>
        <li>{t.about3}</li>
        <li>{t.about4}</li>
      </ul>
      <p className="muted">{t.aboutLimits}</p>
    </Modal>
  );
}
