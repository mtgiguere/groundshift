"""
Mutation audit: randomly sample and run N mutations against core business logic.

Applies operator-flip mutations one at a time, runs the relevant unit tests,
reverts, and reports survivors. No external dependencies — uses only stdlib
and the project's existing pytest setup.

Target files and their paired test files are hardcoded to the highest-value
business logic: zone detectors, aggregator, plugin score methods.

Usage:
    python scripts/mutation_audit.py [--sample 50] [--seed 42]
"""

from __future__ import annotations

import argparse
import random
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

# ---------------------------------------------------------------------------
# Target files -> their paired test files
# ---------------------------------------------------------------------------

_TARGETS: dict[Path, Path] = {
    Path("groundshift/core/opportunity/gain_zone_detector.py"): Path(
        "tests/unit/core/opportunity/test_gain_zone_detector.py"
    ),
    Path("groundshift/core/opportunity/loss_zone_detector.py"): Path(
        "tests/unit/core/opportunity/test_loss_zone_detector.py"
    ),
    Path("groundshift/core/aggregator.py"): Path("tests/unit/core/test_aggregator.py"),
    Path("groundshift/core/envelope/threshold.py"): Path(
        "tests/unit/core/envelope/test_threshold.py"
    ),
    Path("groundshift/core/imagery/divergence.py"): Path(
        "tests/unit/core/imagery/test_divergence.py"
    ),
    Path("groundshift/core/calibration/anchor_scorer.py"): Path(
        "tests/unit/core/calibration/test_anchor_scorer.py"
    ),
    Path("groundshift/models/suitability_modifier.py"): Path(
        "tests/unit/models/test_suitability_modifier.py"
    ),
    Path("groundshift/models/bounding_box.py"): Path("tests/unit/models/test_bounding_box.py"),
    Path("groundshift/plugins/frost_risk.py"): Path("tests/unit/plugins/test_frost_risk_plugin.py"),
    Path("groundshift/plugins/drought_stress.py"): Path(
        "tests/unit/plugins/test_drought_stress_plugin.py"
    ),
    Path("groundshift/plugins/heat_stress.py"): Path(
        "tests/unit/plugins/test_heat_stress_plugin.py"
    ),
    Path("groundshift/plugins/groundwater.py"): Path(
        "tests/unit/plugins/test_groundwater_plugin.py"
    ),
    Path("groundshift/plugins/pest_disease.py"): Path(
        "tests/unit/plugins/test_pest_disease_plugin.py"
    ),
    Path("groundshift/plugins/phenology.py"): Path(
        "tests/unit/plugins/test_phenology_plugin.py"
    ),
    Path("groundshift/plugins/cooperative_infra.py"): Path(
        "tests/unit/plugins/test_cooperative_infra_plugin.py"
    ),
    Path("groundshift/plugins/land_tenure.py"): Path(
        "tests/unit/plugins/test_land_tenure_plugin.py"
    ),
}

# Operator substitutions: (find, replace).
# Longer patterns listed first so " <= " is matched before " < ".
_OP_MUTATIONS: list[tuple[str, str]] = [
    (" <= ", " >= "),
    (" >= ", " <= "),
    (" < ", " > "),
    (" > ", " < "),
    (" == ", " != "),
    (" != ", " == "),
    (" and ", " or "),
    (" or ", " and "),
    (".min()", ".max()"),
    (".max()", ".min()"),
]


# ---------------------------------------------------------------------------
# Pure helpers — unit-tested
# ---------------------------------------------------------------------------


@dataclass
class Mutation:
    file: Path
    line: int
    original: str
    mutant: str
    description: str


def collect_mutations(path: Path) -> list[Mutation]:
    """Return all operator-flip mutation candidates for a source file."""
    lines = path.read_text(encoding="utf-8").splitlines()
    mutations: list[Mutation] = []
    in_docstring = False
    for i, line in enumerate(lines, start=1):
        stripped = line.lstrip()
        if stripped.startswith("#"):
            continue
        # Toggle docstring state on lines with an odd number of triple-quotes.
        # Each such line is itself a delimiter — skip it regardless of state.
        for quote in ('"""', "'''"):
            if line.count(quote) % 2 == 1:
                in_docstring = not in_docstring
                break
        if in_docstring or '"""' in line or "'''" in line:
            continue
        for find, replace in _OP_MUTATIONS:
            if find in line:
                mutant = line.replace(find, replace, 1)
                op_name = find.strip()
                mutations.append(
                    Mutation(
                        file=path,
                        line=i,
                        original=line,
                        mutant=mutant,
                        description=f"{op_name} -> {replace.strip()} at line {i}",
                    )
                )
    return mutations


def apply_mutation(path: Path, line_no: int, mutated_line: str) -> None:
    """Replace line_no (1-based) in path with mutated_line."""
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    eol = "\r\n" if lines[line_no - 1].endswith("\r\n") else "\n"
    lines[line_no - 1] = mutated_line.rstrip("\r\n") + eol
    path.write_text("".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# I/O boundary — not unit-tested
# ---------------------------------------------------------------------------


def _run_tests(test_file: Path) -> bool:
    """Return True if tests PASS (mutation survived — the bad outcome)."""
    result = subprocess.run(
        [sys.executable, "-m", "pytest", str(test_file), "-x", "-q", "--tb=no", "--no-header"],
        capture_output=True,
    )
    return result.returncode == 0


def run_audit(sample: int = 50, seed: int | None = None) -> None:
    rng = random.Random(seed)

    all_mutations: list[tuple[Mutation, Path]] = []
    for target, test_file in _TARGETS.items():
        if target.exists() and test_file.exists():
            for m in collect_mutations(target):
                all_mutations.append((m, test_file))

    total_available = len(all_mutations)
    if total_available == 0:
        print("No mutation candidates found.")
        return

    sampled = rng.sample(all_mutations, min(sample, total_available))
    print(f"Collected {total_available} candidates across {len(_TARGETS)} files.")
    print(f"Running {len(sampled)} randomly sampled mutations...\n")

    killed = 0
    survived: list[Mutation] = []

    for i, (mutation, test_file) in enumerate(sampled, 1):
        original = mutation.file.read_text(encoding="utf-8")
        try:
            apply_mutation(mutation.file, mutation.line, mutation.mutant)
            if _run_tests(test_file):
                survived.append(mutation)
                status = "SURVIVED"
            else:
                killed += 1
                status = "killed"
        finally:
            mutation.file.write_text(original, encoding="utf-8")
        print(
            f"  [{i:2d}/{len(sampled)}] {mutation.file.name}:{mutation.line} "
            f"{mutation.description} -> {status}"
        )

    print(f"\n{'=' * 60}")
    kill_rate = killed / len(sampled) if sampled else 0.0
    print(f"Results: {killed} killed / {len(survived)} survived / {len(sampled)} run")
    print(f"Kill rate: {kill_rate:.0%}")

    if survived:
        print(f"\nSurviving mutations — test gaps to address ({len(survived)}):")
        for m in survived:
            print(f"\n  {m.file}:{m.line}  [{m.description}]")
            print(f"  - {m.original.strip()}")
            print(f"  + {m.mutant.strip()}")
    else:
        print("\nNo survivors. Test suite catches all sampled mutations.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample", type=int, default=50, help="Number of mutations to run.")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for reproducibility.")
    args = parser.parse_args()
    run_audit(sample=args.sample, seed=args.seed)
