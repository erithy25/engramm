# Independent reproduction

`independent/` is a second implementation of the classifier, written by a
separate agent session **from `docs/SPEC_REBUILD.md` alone** — without access
to `engramm/`, `experiments/`, `data/*.py`, `tests/`, `legacy/`, `results/`,
any cache or the git history — reading only the five raw data archives. This
is the procedure the README defines as independent reproduction (Method,
step 3).

It is kept here as evidence, not as a second library: nothing imports it.
Its report with the full 185-row conformance table is `independent/REPORT.md`;
the comparison against the committed records is
`results/repro/independent_verification.json`.

Run (reads the raw archives from a directory `data/` next to the scripts):

    cd reproduction/independent
    mkdir -p data && ln -s ../../../data/cache/{wili-2018.zip,*-ubyte.gz} data/
    env -u PYTHONPATH ../../.venv/bin/python -I run_all.py

What it establishes: the specification is complete, and the benchmark
predictions are deterministic on this platform (bit-identical predictions
for WiLI 10-shot, MNIST T1, MNIST T1 + T2 and the full MNIST pipeline, seed
42). What it does not establish: replication by a third party on different
hardware.
