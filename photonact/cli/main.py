"""Command-line entry point."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from photonact.curves import load_curve


def resolve_curve_path(value: str) -> Path:
    """Resolve a local path or the bundled sample name."""
    path = Path(value)
    if path.exists():
        return path
    bundled = Path(__file__).parents[1] / "data" / f"{value}.csv"
    if value in {"sample_phh", "phh_1535nm"} and bundled.exists():
        return bundled
    raise FileNotFoundError(f"Curve not found: {value}")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="photonact", description="Optical curve tools")
    subparsers = parser.add_subparsers(dest="command", required=True)
    inspect_parser = subparsers.add_parser("inspect", help="validate and summarize a curve")
    inspect_parser.add_argument("curve")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the PhotonAct CLI and return a process exit code."""
    arguments = _parser().parse_args(argv)
    if arguments.command != "inspect":
        raise AssertionError("Unreachable command")
    curve = load_curve(resolve_curve_path(arguments.curve))
    summary = {
        "metadata": curve.metadata.to_dict(),
        "points": len(curve.input_power),
        "branches": sorted(set(curve.branch)),
        "input_range": [min(curve.input_power), max(curve.input_power)],
        "output_range": [min(curve.output_power), max(curve.output_power)],
        "hysteresis_thresholds": (
            [curve.metadata.lower_threshold, curve.metadata.upper_threshold]
            if curve.metadata.lower_threshold is not None
            else None
        ),
    }
    print(json.dumps(summary, indent=2))
    return 0
