"""Event log for ENGRAMM-LM: learn / forget / consolidate, exact replay.

Reuses the L2 framing of :class:`engramm.persistence.EventLog`
(``[u32 len][u32 crc32][kind + body]``, torn tails discarded). Kinds:

* ``H`` header: the base model's digest (replay refuses a different base);
* ``T`` learn: source id + text;
* ``F`` forget: source id;
* ``E`` epoch: consolidate.

The log is written *before* the change is applied, as in L2.
"""

from __future__ import annotations

import json
import struct
from pathlib import Path

from engramm.persistence import EventLog, read_events

_H, _T, _F, _E = ord("H"), ord("T"), ord("F"), ord("E")


def _str(s: str) -> bytes:
    raw = s.encode("utf-8")
    return struct.pack(">I", len(raw)) + raw


def _read_str(body: bytes, off: int) -> tuple[str, int]:
    (n,) = struct.unpack_from(">I", body, off)
    return body[off + 4:off + 4 + n].decode("utf-8"), off + 4 + n


class LMEventLog(EventLog):
    def write_lm_header(self, model) -> None:
        self._append(bytes([_H]) + json.dumps({"base": model.base_digest(), "seed": model.seed,
                                               "epoch": model.epoch}).encode())

    def learn_text(self, source_id: str, text: str) -> None:
        self._append(bytes([_T]) + _str(source_id) + _str(text))

    def forget(self, source_id: str) -> None:
        self._append(bytes([_F]) + _str(source_id))

    def consolidate(self) -> None:
        self._append(bytes([_E]))


class LoggedModel:
    """A model whose every change goes through the log first."""

    def __init__(self, model, log_path: Path | str):
        self.model = model
        self.log = LMEventLog(log_path)
        if self.log.events_written == 0 and Path(log_path).stat().st_size <= 12:
            self.log.write_lm_header(model)

    def learn_text(self, text: str, source_id: str) -> None:
        self.log.learn_text(source_id, text)
        self.model.learn_text(text, source_id)

    def forget(self, source_id: str) -> str:
        self.log.forget(source_id)
        return self.model.forget(source_id)


def replay_lm(path: Path | str, model, consolidate_log=None):
    """Apply a log to ``model`` (a freshly loaded base). Returns (model, n_events, bytes_discarded)."""
    records, _, discarded = read_events(path)
    if not records or records[0][0] != _H:
        raise ValueError(f"{path}: no ENGRAMM-LM header")
    head = json.loads(records[0][1].decode())
    if head["base"] != model.base_digest():
        raise ValueError("log was written against a different base model")
    for kind, body in records[1:]:
        if kind == _T:
            sid, off = _read_str(body, 0)
            text, _ = _read_str(body, off)
            model.learn_text(text, sid)
        elif kind == _F:
            sid, _ = _read_str(body, 0)
            model.forget(sid)
        elif kind == _E:
            model = model.consolidate(log=consolidate_log)
        else:
            raise ValueError(f"unknown event kind {kind}")
    return model, len(records), discarded
