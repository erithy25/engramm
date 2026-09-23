"""L2: the append-only event log and exact replay.

Every state change of an :class:`engramm.memory.Engramm` — T1 learning, T2
refinement, T3 removal — is appended to the log *before* it is applied. The
log is therefore the source of truth: replaying it into a fresh instance
reproduces the state bit for bit, and so do all predictions.

Crash safety comes from the framing, not from luck. Each record is::

    [u32 payload length][u32 CRC-32 of payload][payload]

A process killed mid-write leaves a record whose length prefix points past
the end of the file, or whose checksum does not match. :func:`replay` stops
at the first such record and reports how many bytes it discarded — the
state is then exactly the state after the last complete event, never a
half-applied one. That is the property the M2b persistence gate tests with
a hard byte cut (``experiments/m2b.py``).

The log records *effects*, not decisions: a refinement event stores which
episode utilities moved by how much and which prototypes changed, rather
than asking the replayer to re-run the classification. Replay is therefore
independent of retrieval details and cannot drift from the live run.
"""

from __future__ import annotations

import json
import os
import struct
import zlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, BinaryIO

import numpy as np

MAGIC = b"ENGRAMM-L2\x00\x01"

_HEADER = ord("H")
_LEARN = ord("L")
_REFINE = ord("R")
_REMOVE = ord("X")

_REASONS = {"absorb": 1, "evict": 2, "other": 0}
_REASON_NAMES = {v: k for k, v in _REASONS.items()}


class EventLog:
    """Append-only writer. One instance per open log file.

    ``sync=True`` calls ``fsync`` after every record, which survives power
    loss as well as process death, at a large cost in throughput. The
    default flushes to the operating system after every record, which
    survives the process being killed — the failure the M2b gate models.
    """

    def __init__(self, path: Path | str, sync: bool = False) -> None:
        self.path = Path(path)
        self.sync = bool(sync)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        exists = self.path.exists() and self.path.stat().st_size > 0
        self._handle: BinaryIO = open(self.path, "ab")
        if not exists:
            self._handle.write(MAGIC)
            self._flush()
        self.events_written = 0
        self._dimension: int | None = None

    def close(self) -> None:
        self._handle.close()

    def __enter__(self) -> EventLog:
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()

    def _flush(self) -> None:
        self._handle.flush()
        if self.sync:
            os.fsync(self._handle.fileno())

    def _append(self, payload: bytes) -> None:
        self._handle.write(struct.pack(">II", len(payload), zlib.crc32(payload)))
        self._handle.write(payload)
        self._flush()
        self.events_written += 1

    # -- event encoders (called by Engramm before applying the change) --------

    def write_header(self, model: Any) -> None:
        self._dimension = model.dimension
        meta = {"dimension": model.dimension, "seed": model.seed,
                "config": model.config.to_dict()}
        self._append(bytes([_HEADER]) + json.dumps(meta, sort_keys=True).encode("utf-8"))

    def learn(self, labels: list[str], packed: np.ndarray) -> None:
        parts = [bytes([_LEARN]), struct.pack(">I", len(labels))]
        for label in labels:
            raw = label.encode("utf-8")
            parts.append(struct.pack(">H", len(raw)) + raw)
        parts.append(np.ascontiguousarray(packed, dtype=np.uint8).tobytes())
        self._append(b"".join(parts))

    def refine(self, positions: np.ndarray | None, util_delta: np.ndarray | None,
               true_class: int, predicted: int, key: np.ndarray) -> None:
        positions = (np.zeros(0, dtype=np.int64) if positions is None
                     else np.asarray(positions, dtype=np.int64))
        deltas = (np.zeros(0, dtype=np.int8) if util_delta is None
                  else np.asarray(util_delta, dtype=np.int8))
        self._append(b"".join([
            bytes([_REFINE]),
            struct.pack(">Iii", positions.size, int(true_class), int(predicted)),
            positions.astype(">u4").tobytes(),
            deltas.tobytes(),
            np.ascontiguousarray(key, dtype=np.uint8).tobytes(),
        ]))

    def remove(self, positions: np.ndarray, reason: str) -> None:
        positions = np.asarray(positions, dtype=np.int64)
        self._append(b"".join([
            bytes([_REMOVE]),
            struct.pack(">BI", _REASONS.get(reason, 0), positions.size),
            positions.astype(">u4").tobytes(),
        ]))


@dataclass(frozen=True)
class ReplayReport:
    """What a replay read, applied, and discarded."""

    events_applied: int
    bytes_read: int
    bytes_discarded: int
    removals_by_reason: dict[str, int]

    @property
    def torn(self) -> bool:
        return self.bytes_discarded > 0


def read_events(path: Path | str, limit: int | None = None
                ) -> tuple[list[tuple[int, bytes]], int, int]:
    """Return ``(records, bytes_consumed, bytes_discarded)``.

    ``limit`` stops after that many events (the header counts as one),
    which is how a reference "state after n events" is rebuilt.
    """
    data = Path(path).read_bytes()
    if not data.startswith(MAGIC):
        raise ValueError(f"{path} is not an ENGRAMM L2 log")
    offset = len(MAGIC)
    records: list[tuple[int, bytes]] = []
    while offset + 8 <= len(data):
        if limit is not None and len(records) >= limit:
            break
        length, checksum = struct.unpack_from(">II", data, offset)
        start, end = offset + 8, offset + 8 + length
        if end > len(data) or length == 0:
            break
        payload = data[start:end]
        if zlib.crc32(payload) != checksum:
            break
        records.append((payload[0], payload[1:]))
        offset = end
    return records, offset, len(data) - offset


def replay(path: Path | str, limit: int | None = None,
           cache_bytes: int | None = None) -> tuple[Any, ReplayReport]:
    """Rebuild an :class:`~engramm.memory.Engramm` from its log.

    Applies events through the same ``_apply_*`` methods the live instance
    uses, so replay and live learning cannot disagree about what an event
    means. The rebuilt instance has no log attached.
    """
    from engramm.memory import DEFAULT_CACHE_BYTES, Engramm, FusionConfig

    records, consumed, discarded = read_events(path, limit)
    if not records or records[0][0] != _HEADER:
        raise ValueError(f"{path}: log has no header event")
    meta = json.loads(records[0][1].decode("utf-8"))
    model = Engramm(meta["dimension"], meta["seed"], FusionConfig(**meta["config"]),
                    log=None,
                    cache_bytes=DEFAULT_CACHE_BYTES if cache_bytes is None else cache_bytes)
    n_bytes = model.dimension // 8
    removals: dict[str, int] = {}

    for kind, body in records[1:]:
        if kind == _LEARN:
            (count,) = struct.unpack_from(">I", body, 0)
            offset = 4
            labels = []
            for _ in range(count):
                (size,) = struct.unpack_from(">H", body, offset)
                offset += 2
                labels.append(body[offset:offset + size].decode("utf-8"))
                offset += size
            packed = np.frombuffer(body[offset:offset + count * n_bytes],
                                   dtype=np.uint8).reshape(count, n_bytes)
            model._apply_learn(packed.copy(), labels)
        elif kind == _REFINE:
            k, true_class, predicted = struct.unpack_from(">Iii", body, 0)
            offset = 12
            positions = np.frombuffer(body[offset:offset + 4 * k], dtype=">u4").astype(np.int64)
            offset += 4 * k
            deltas = np.frombuffer(body[offset:offset + k], dtype=np.int8).astype(np.int64)
            offset += k
            key = np.frombuffer(body[offset:offset + n_bytes], dtype=np.uint8).copy()
            model._apply_refine(positions if k else None, deltas if k else None,
                                true_class, predicted, key)
        elif kind == _REMOVE:
            reason, count = struct.unpack_from(">BI", body, 0)
            positions = np.frombuffer(body[5:5 + 4 * count], dtype=">u4").astype(np.int64)
            model.episodes.remove(positions)
            name = _REASON_NAMES.get(reason, "other")
            removals[name] = removals.get(name, 0) + int(count)
        elif kind == _HEADER:
            raise ValueError(f"{path}: second header event")
        else:
            raise ValueError(f"{path}: unknown event type {kind!r}")

    return model, ReplayReport(events_applied=len(records), bytes_read=consumed,
                               bytes_discarded=discarded, removals_by_reason=removals)
