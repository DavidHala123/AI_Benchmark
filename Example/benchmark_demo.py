"""Small benchmark helper for the palletization solver."""

from __future__ import annotations

from pathlib import Path
from statistics import mean
from time import perf_counter

from src.palletizer.io import load_problem_from_json
from src.palletizer.solver import solve_palletization


def main() -> int:
    config_path = Path(__file__).resolve().parents[1] / "Data" / "sample_problem.json"
    bin_config, items = load_problem_from_json(config_path)

    timings = []
    for _ in range(10):
        start = perf_counter()
        solve_palletization(bin_config, items)
        timings.append((perf_counter() - start) * 1000.0)

    print(f"Average solve time over 10 runs: {mean(timings):.2f} ms")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
