"""Tests for the reproducibility layer: seeding, provenance, run records."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from engramm.repro import (
    SCHEMA_VERSION,
    git_revision,
    set_all_seeds,
    write_result,
)


def test_untracked_files_do_not_mark_a_run_dirty(tmp_path: Path) -> None:
    """A run's own result files must not disqualify its later seeds.

    Writing a record leaves an untracked file behind. Counting that as
    "dirty" marked every seed after the first as uncitable — a defect found
    on the first real MNIST run and fixed by scoping `dirty` to tracked
    modifications.
    """
    import subprocess

    repo = tmp_path / "repo"
    repo.mkdir()
    run = lambda *a: subprocess.run(a, cwd=repo, capture_output=True, check=True)
    run("git", "init", "-q")
    run("git", "config", "user.email", "t@example.com")
    run("git", "config", "user.name", "t")
    (repo / "code.py").write_text("x = 1\n")
    run("git", "add", "code.py")
    run("git", "commit", "-qm", "initial")

    import engramm.repro as repro
    original = repro._REPO_ROOT
    try:
        repro._REPO_ROOT = repo
        clean = repro.git_revision()
        assert clean["dirty"] is False and clean["untracked"] == 0

        (repo / "result.json").write_text("{}")
        with_untracked = repro.git_revision()
        assert with_untracked["dirty"] is False, "untracked file must not set dirty"
        assert with_untracked["untracked"] == 1

        (repo / "code.py").write_text("x = 2\n")
        modified = repro.git_revision()
        assert modified["dirty"] is True, "a tracked modification must set dirty"
    finally:
        repro._REPO_ROOT = original


def test_record_carries_the_provenance_fields(tmp_path: Path) -> None:
    """Every record must be attributable to code, seed and environment."""
    path = write_result(
        task="synthetic", seed=42,
        result={"accuracy": 0.5, "macro_f1": 0.5},
        hyperparams={"dimension": 512},
        wall_seconds=1.0,
        results_dir=tmp_path,
    )
    import json
    record = json.loads(path.read_text())
    assert record["schema_version"] == SCHEMA_VERSION
    assert set(record["git"]) == {"commit", "dirty", "untracked"}
    assert record["environment"]["canonical"] in (True, False)
    assert record["runtime"]["peak_rss_mb"] > 0


def test_records_are_append_only_even_within_one_second(tmp_path: Path) -> None:
    """Two records of the same task and seed must both survive.

    Filenames carry a one-second timestamp, so back-to-back writes used to
    collide and silently overwrite the earlier record — a violation of the
    guarantee the whole ``results/`` convention rests on.
    """
    import json

    first = write_result(task="t", seed=1, result={"accuracy": 0.1},
                         hyperparams={}, wall_seconds=0.1, results_dir=tmp_path)
    second = write_result(task="t", seed=1, result={"accuracy": 0.9},
                          hyperparams={}, wall_seconds=0.1, results_dir=tmp_path)

    assert first != second
    assert len(list(tmp_path.glob("t_1_*.json"))) == 2
    assert json.loads(first.read_text())["result"]["accuracy"] == 0.1
    assert json.loads(second.read_text())["result"]["accuracy"] == 0.9


def test_seeding_is_reproducible_and_seed_sensitive() -> None:
    a = set_all_seeds(42).integers(0, 1000, 20)
    b = set_all_seeds(42).integers(0, 1000, 20)
    c = set_all_seeds(43).integers(0, 1000, 20)
    assert np.array_equal(a, b)
    assert not np.array_equal(a, c)
