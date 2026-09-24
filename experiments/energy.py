"""Energy per operation — measured where the hardware exposes it, never estimated.

Two backends, tried in order:

* **RAPL** (Linux, Intel/AMD): the package energy counters under
  ``/sys/class/powercap/intel-rapl:<n>/energy_uj``, read before and after,
  with counter wrap-around handled via ``max_energy_range_uj``. Only
  top-level package domains are summed — their sub-domains (cores, uncore,
  DRAM) are already contained in them, and adding them would double-count.
* **powermetrics** (macOS, the reference machine): a sampler started for the
  duration of the measurement, ``powermetrics --samplers cpu_power -i <ms>``,
  run through ``sudo -n`` (it needs root and must not prompt). Energy is the
  sum over samples of *Combined Power (CPU + GPU + ANE)* × the sample's own
  elapsed time. Only the combined line is used — the historical harness
  averaged the CPU, GPU and combined lines together, which is wrong
  (``docs/AUDIT_2026-08.md``).

If neither is available — as in the Linux container, which has no power
interface — the result says so and carries ``None``. No figure is ever
derived from CPU time and a nominal TDP: that would be an estimate, and the
project does not publish estimates as measurements.

The figure is whole-package energy while the operation runs, including idle
draw; an idle baseline of the same duration is measured next to it and
reported separately, so both readings are available.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

RAPL_ROOT = Path("/sys/class/powercap")
_SAMPLE = re.compile(r"\*\*\* Sampled system activity .*?\(([\d.]+)ms elapsed\)")
_COMBINED = re.compile(r"Combined Power \(CPU \+ GPU \+ ANE\):\s*([\d.]+)\s*mW")


# ---------------------------------------------------------------------------
# RAPL
# ---------------------------------------------------------------------------

def rapl_domains(root: Path = RAPL_ROOT) -> list[Path]:
    """Readable top-level package domains (``intel-rapl:<n>``, not ``:<n>:<m>``)."""
    if not root.is_dir():
        return []
    domains = []
    for d in sorted(root.glob("intel-rapl:*")):
        if d.name.count(":") != 1:
            continue
        try:
            int((d / "energy_uj").read_text())
        except (OSError, ValueError):
            continue
        domains.append(d)
    return domains


def _rapl_read(domains: list[Path]) -> list[int]:
    return [int((d / "energy_uj").read_text()) for d in domains]


def _rapl_delta_uj(domains: list[Path], before: list[int], after: list[int]) -> int:
    total = 0
    for d, a, b in zip(domains, before, after):
        if b >= a:
            total += b - a
        else:
            total += int((d / "max_energy_range_uj").read_text()) - a + b
    return total


# ---------------------------------------------------------------------------
# powermetrics
# ---------------------------------------------------------------------------

def parse_powermetrics(text: str) -> tuple[float, float]:
    """Energy (mJ) and covered time (ms) from powermetrics text output.

    Each sample block opens with ``*** Sampled system activity … (X ms
    elapsed) ***`` and contains one ``Combined Power (CPU + GPU + ANE)`` line;
    energy is Σ combined_mW × elapsed_ms / 1000. Blocks without a combined
    line (e.g. a truncated last block) are skipped, and so is their time.
    """
    energy_mj = covered_ms = 0.0
    blocks = _SAMPLE.split(text)
    # split() with one group yields [pre, elapsed1, body1, elapsed2, body2, ...]
    for elapsed, body in zip(blocks[1::2], blocks[2::2]):
        match = _COMBINED.search(body)
        if match is None:
            continue
        ms = float(elapsed)
        energy_mj += float(match.group(1)) * ms / 1000.0
        covered_ms += ms
    return energy_mj, covered_ms


def _powermetrics_available() -> bool:
    if sys.platform != "darwin" or shutil.which("powermetrics") is None:
        return False
    probe = subprocess.run(["sudo", "-n", "true"], capture_output=True)
    return probe.returncode == 0


# ---------------------------------------------------------------------------
# The measurement
# ---------------------------------------------------------------------------

def backend() -> str | None:
    if rapl_domains():
        return "rapl"
    if _powermetrics_available():
        return "powermetrics"
    return None


def _measure_once(fn: Callable[[], Any], repeats: int, source: str,
                  interval_ms: int) -> tuple[float, float]:
    """Run ``fn`` ``repeats`` times; return (energy_mJ, seconds)."""
    if source == "rapl":
        domains = rapl_domains()
        before = _rapl_read(domains)
        start = time.perf_counter()
        for _ in range(repeats):
            fn()
        seconds = time.perf_counter() - start
        return _rapl_delta_uj(domains, before, _rapl_read(domains)) / 1000.0, seconds
    sampler = subprocess.Popen(
        ["sudo", "-n", "powermetrics", "--samplers", "cpu_power", "-i", str(interval_ms)],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    time.sleep(interval_ms / 1000.0)          # let the first sample window open
    start = time.perf_counter()
    for _ in range(repeats):
        fn()
    seconds = time.perf_counter() - start
    time.sleep(interval_ms / 1000.0)
    sampler.terminate()
    output, _ = sampler.communicate(timeout=30)
    energy_mj, covered_ms = parse_powermetrics(output)
    # The sampler also covered the two guard intervals; scale to the run.
    if covered_ms <= 0:
        raise RuntimeError("powermetrics produced no usable sample")
    return energy_mj * (seconds * 1000.0) / covered_ms, seconds


def measure_energy(fn: Callable[[], Any], repeats: int, *, idle_baseline: bool = True,
                   interval_ms: int = 100) -> dict[str, Any]:
    """Package energy per call of ``fn``, or an explicit "not available".

    Returns a record fragment: ``mj_per_call`` (whole package, idle included),
    ``mj_per_call_above_idle`` (minus an idle window of equal length),
    the backend, and the measured duration. In an environment without a
    power interface every energy field is ``None`` and ``available`` is false.
    """
    source = backend()
    if source is None:
        return {"available": False, "source": None, "mj_per_call": None,
                "mj_per_call_above_idle": None, "calls": repeats,
                "note": "not measured: no power interface (no readable RAPL counters, "
                        "no passwordless powermetrics)"}
    energy_mj, seconds = _measure_once(fn, repeats, source, interval_ms)
    result: dict[str, Any] = {"available": True, "source": source, "calls": repeats,
                              "seconds": seconds, "energy_mj_total": energy_mj,
                              "mj_per_call": energy_mj / repeats}
    if idle_baseline:
        idle_mj, idle_s = _measure_once(lambda: time.sleep(seconds), 1, source, interval_ms)
        idle_per_s = idle_mj / idle_s if idle_s > 0 else 0.0
        result["idle_mw"] = idle_per_s
        result["mj_per_call_above_idle"] = (energy_mj - idle_per_s * seconds) / repeats
    else:
        result["mj_per_call_above_idle"] = None
    return result
