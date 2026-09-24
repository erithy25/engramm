"""Energy meter: parsing and counter arithmetic, and honest absence."""

from pathlib import Path

import pytest

from experiments import energy
from experiments.energy import _rapl_delta_uj, measure_energy, parse_powermetrics, rapl_domains

SAMPLE = """Machine model: Mac16,12
*** Sampled system activity (Wed Jul  6 10:00:00 2026 +0200) (100.50ms elapsed) ***

**** Processor usage ****
CPU Power: 900 mW
GPU Power: 50 mW
ANE Power: 0 mW
Combined Power (CPU + GPU + ANE): 950 mW

*** Sampled system activity (Wed Jul  6 10:00:00 2026 +0200) (99.50ms elapsed) ***

CPU Power: 1900 mW
GPU Power: 100 mW
Combined Power (CPU + GPU + ANE): 2000 mW

*** Sampled system activity (Wed Jul  6 10:00:00 2026 +0200) (40.00ms elapsed) ***
CPU Power: 700 mW
"""


def test_powermetrics_uses_only_the_combined_line_and_each_samples_own_interval():
    energy_mj, covered_ms = parse_powermetrics(SAMPLE)
    assert covered_ms == pytest.approx(200.0)          # the truncated block is skipped
    assert energy_mj == pytest.approx(950 * 0.1005 + 2000 * 0.0995)


def _fake_rapl(root: Path, values: dict[str, int], max_range: int = 1000) -> None:
    for name, value in values.items():
        d = root / name
        d.mkdir(parents=True)
        (d / "energy_uj").write_text(str(value))
        (d / "max_energy_range_uj").write_text(str(max_range))


def test_rapl_sums_packages_only_and_handles_wraparound(tmp_path):
    _fake_rapl(tmp_path, {"intel-rapl:0": 100, "intel-rapl:1": 900, "intel-rapl:0:0": 5})
    domains = rapl_domains(tmp_path)
    assert [d.name for d in domains] == ["intel-rapl:0", "intel-rapl:1"]
    # package 0 advanced by 50; package 1 wrapped: 900 -> 1000 -> 30 = 130
    assert _rapl_delta_uj(domains, [100, 900], [150, 30]) == 180


def test_no_power_interface_means_none_not_an_estimate(monkeypatch):
    monkeypatch.setattr(energy, "backend", lambda: None)
    result = measure_energy(lambda: None, 10)
    assert result["available"] is False
    assert result["mj_per_call"] is None and result["mj_per_call_above_idle"] is None
    assert "not measured" in result["note"]
