"""ENGRAMM — hyperdimensional computing classifier (from-scratch rebuild).

The original implementation was lost (see ``docs/AUDIT_2026-08.md``). This
package is the reimplementation, built from the preserved design documents
in ``docs/``: prototypes, episodic memory with score fusion, T1/T2/T3
learning and the L2 event log. Every point where the recovered
specification was silent is recorded in ``docs/DEVIATIONS.md``.

Modules
-------
``engramm.repro``
    Seeding, environment capture, and the versioned result-record schema.
``engramm.core``
    VSA algebra, item memory, and the prototype classifier.
``engramm.metrics``
    Hamming distance, similarity, accuracy, macro-F1.
``engramm.encoders``
    Text n-gram and MNIST pixel encoders.
``engramm.memory``
    The full pipeline: episodic memory, score fusion, T1/T2/T3.
``engramm.persistence``
    The L2 append-only event log and exact (crash) replay.
"""

from engramm.core import (
    DEFAULT_DIMENSION,
    HALVE_THRESHOLD,
    ItemMemory,
    PrototypeClassifier,
    TieContext,
    bind,
    bundle,
    from_signed,
    pack_bits,
    permute,
    resolve_tie,
    to_signed,
    unbind,
    unpack_bits,
)
from engramm.memory import Engramm, EpisodicMemory, FusionConfig
from engramm.persistence import EventLog, replay
from engramm.metrics import (
    accuracy,
    hamming,
    macro_f1,
    popcount_rows,
    sim_from_dh,
)
from engramm.repro import (
    SCHEMA_VERSION,
    collect_environment,
    determinism_digest,
    digest_hash,
    git_revision,
    is_canonical_environment,
    peak_rss_mb,
    set_all_seeds,
    stable_label_order,
    write_result,
)

__version__ = "2.0.0.dev0"

__all__ = [
    # core
    "DEFAULT_DIMENSION",
    "HALVE_THRESHOLD",
    "ItemMemory",
    "PrototypeClassifier",
    "TieContext",
    "bind",
    "bundle",
    "from_signed",
    "pack_bits",
    "permute",
    "resolve_tie",
    "to_signed",
    "unbind",
    "unpack_bits",
    # full pipeline
    "Engramm",
    "EpisodicMemory",
    "FusionConfig",
    "EventLog",
    "replay",
    # metrics
    "accuracy",
    "hamming",
    "macro_f1",
    "popcount_rows",
    "sim_from_dh",
    # reproducibility
    "SCHEMA_VERSION",
    "collect_environment",
    "determinism_digest",
    "digest_hash",
    "git_revision",
    "is_canonical_environment",
    "peak_rss_mb",
    "set_all_seeds",
    "stable_label_order",
    "write_result",
    "__version__",
]
