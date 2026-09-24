from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

STEPS = [
    "analyze_bravo_network.py",
    "map_bravo_network.py",
    "build_coverage_grid.py",
    "build_expansion_screen.py",
    "analyze_screen_diagnostics.py",
    "build_decision_matrix.py",
    "build_readme_maps.py",
]


def main() -> None:
    for script in STEPS:
        path = ROOT / "src" / script
        print(f"\n=== Running {script} ===")
        subprocess.run(
            [sys.executable, str(path)],
            cwd=ROOT,
            check=True,
        )

    print("\nAnalysis complete. See outputs/ and data/processed/.")


if __name__ == "__main__":
    main()