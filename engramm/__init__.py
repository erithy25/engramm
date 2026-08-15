"""ENGRAMM — hyperdimensional computing classifier (from-scratch rebuild).

The original implementation was lost (see the repository README's Status
section). This package is the reimplementation, built from the preserved
design documents in ``docs/`` — deliberately smaller than the original:
no HNSW index, no episodic memory, no consolidation phases. Core first,
measured, then extended.

Modules
-------
``engramm.repro``
    Seeding, environment capture, and the versioned result-record schema.
``engramm.core``
    Item memory and classifier (added in step B2).
``engramm.encoders``
    Text n-gram and MNIST pixel encoders (added in step B4).
``engramm.metrics``
    Hamming distance, similarity, accuracy, macro-F1 (added in step B2).
"""

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
