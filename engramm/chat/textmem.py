"""The chat's memory without the language model: your texts, logged, exactly forgettable.

The chat only needs what you told it (``user_texts``); the 4 GB language-model tables are not
needed for that. ``LoggedTextMemory`` keeps the texts in a dict and writes every change first
to an event log with the same framing as the language model's ``user.log`` (``[u32 len][u32
crc32][kind + body]``, torn tails discarded), so a crash never loses or half-applies a change.

Migration: on first start, when ``chat_memory.log`` does not exist yet but the language model's
``user.log`` does, its learn / forget events are replayed into the new log — what you told the
old app is still known.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from engramm.lm.log import _F, _H, _T, LMEventLog, _read_str
from engramm.persistence import read_events

HEADER = {"kind": "engramm-text-memory", "version": 1}


class LoggedTextMemory:
    def __init__(self, path: Path | str, import_from: Path | str | None = None):
        self.path = Path(path)
        self.user_texts: dict[str, str] = {}
        fresh = not self.path.exists() or self.path.stat().st_size <= 12
        if not fresh:
            self._replay(self.path, own=True)
        self.log = LMEventLog(self.path)
        if fresh:
            self.log._append(bytes([_H]) + json.dumps(HEADER).encode())
            if import_from is not None and Path(import_from).exists():
                old = LoggedTextMemory.__new__(LoggedTextMemory)
                old.user_texts = {}
                old._replay(Path(import_from), own=False)
                for sid, text in old.user_texts.items():
                    self.learn_text(text, sid)

    def _replay(self, path: Path, own: bool) -> None:
        records, _, _ = read_events(path)
        if not records or records[0][0] != _H:
            raise ValueError(f"{path}: no header")
        if own:
            head = json.loads(records[0][1].decode())
            if head.get("kind") != HEADER["kind"]:
                raise ValueError(f"{path}: not a text-memory log")
        for kind, body in records[1:]:
            if kind == _T:
                sid, off = _read_str(body, 0)
                text, _ = _read_str(body, off)
                self.user_texts[sid] = text
            elif kind == _F:
                sid, _ = _read_str(body, 0)
                self.user_texts.pop(sid, None)

    def learn_text(self, text: str, source_id: str) -> None:
        if source_id in self.user_texts:
            raise ValueError(f"source {source_id!r} already learnt")
        self.log.learn_text(source_id, text)
        self.user_texts[source_id] = text

    def forget(self, source_id: str) -> str:
        if source_id not in self.user_texts:
            raise KeyError(source_id)
        self.log.forget(source_id)
        del self.user_texts[source_id]
        return "user"

    def state_digest(self) -> str:
        h = hashlib.sha256()
        for sid, text in sorted(self.user_texts.items()):
            h.update(f"{sid}\x00{text}\x01".encode())
        return h.hexdigest()

    def close(self) -> None:
        self.log.close()
