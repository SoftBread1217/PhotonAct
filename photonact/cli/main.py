"""Command-line entry point."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from photonact.curves import load_curve
from photonact.demo import open_demo, render_demo
from photonact.prepare import PrepareOptions, prepare_curve


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
    prepare_parser = subparsers.add_parser(
        "prepare", help="convert a local CSV/XLSX table to a documented curve"
    )
    prepare_parser.add_argument("source", type=Path)
    prepare_parser.add_argument("--output-dir", type=Path, required=True)
    prepare_parser.add_argument("--name", required=True)
    prepare_parser.add_argument("--input-column")
    prepare_parser.add_argument("--output-column")
    prepare_parser.add_argument("--branch-column")
    prepare_parser.add_argument("--up-input-column")
    prepare_parser.add_argument("--up-output-column")
    prepare_parser.add_argument("--down-input-column")
    prepare_parser.add_argument("--down-output-column")
    prepare_parser.add_argument("--sheet")
    prepare_parser.add_argument("--start-row", type=int, default=1)
    prepare_parser.add_argument("--end-row", type=int)
    prepare_parser.add_argument("--sort", action="store_true")
    prepare_parser.add_argument(
        "--transform", choices=["direct", "input-times-transmittance"], default="direct"
    )
    prepare_parser.add_argument("--input-unit", required=True)
    prepare_parser.add_argument("--output-unit", required=True)
    prepare_parser.add_argument("--source-description", required=True)
    prepare_parser.add_argument(
        "--data-kind", choices=["measured", "simulated", "digitized", "synthetic"], required=True
    )
    prepare_parser.add_argument("--license", required=True)
    prepare_parser.add_argument("--citation", default="")
    prepare_parser.add_argument("--wavelength-nm", type=float)
    prepare_parser.add_argument("--polarization", default="")
    prepare_parser.add_argument("--lower-threshold", type=float)
    prepare_parser.add_argument("--upper-threshold", type=float)
    demo_parser = subparsers.add_parser(
        "demo", help="generate a local interactive hysteresis explorer"
    )
    demo_parser.add_argument("curve", nargs="?", default="sample_phh")
    demo_parser.add_argument(
        "--output",
        type=Path,
        default=Path("photonact_demo.html"),
        help="HTML output path (default: photonact_demo.html)",
    )
    demo_parser.add_argument(
        "--no-open",
        action="store_true",
        help="write the HTML without opening a browser",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the PhotonAct CLI and return a process exit code."""
    arguments = _parser().parse_args(argv)
    if arguments.command == "prepare":
        options = PrepareOptions(
            name=arguments.name,
            input_column=arguments.input_column,
            output_column=arguments.output_column,
            branch_column=arguments.branch_column,
            up_input_column=arguments.up_input_column,
            up_output_column=arguments.up_output_column,
            down_input_column=arguments.down_input_column,
            down_output_column=arguments.down_output_column,
            sheet=arguments.sheet,
            start_row=arguments.start_row,
            end_row=arguments.end_row,
            sort=arguments.sort,
            transform=arguments.transform,
            input_unit=arguments.input_unit,
            output_unit=arguments.output_unit,
            source_description=arguments.source_description,
            data_kind=arguments.data_kind,
            license=arguments.license,
            citation=arguments.citation,
            wavelength_nm=arguments.wavelength_nm,
            polarization=arguments.polarization,
            lower_threshold=arguments.lower_threshold,
            upper_threshold=arguments.upper_threshold,
        )
        paths = prepare_curve(arguments.source, arguments.output_dir, options)
        for path in paths:
            print(path)
        return 0
    if arguments.command == "demo":
        output = render_demo(resolve_curve_path(arguments.curve), arguments.output)
        print(f"Wrote interactive demo: {output}")
        if not arguments.no_open:
            open_demo(output)
        return 0
    if arguments.command != "inspect":
        raise AssertionError("Unreachable command")
    curve = load_curve(resolve_curve_path(arguments.curve))
    branches = sorted(set(curve.branch))
    branch_ranges = {
        branch: [
            min(x for x, label in zip(curve.input_power, curve.branch, strict=True)
                if label == branch),
            max(x for x, label in zip(curve.input_power, curve.branch, strict=True)
                if label == branch),
        ]
        for branch in branches
    }
    warnings = [
        f"Metadata {field} is unspecified"
        for field in ("source", "data_kind", "license")
        if getattr(curve.metadata, field) == "unspecified"
    ]
    summary = {
        "metadata": curve.metadata.to_dict(),
        "points": len(curve.input_power),
        "branches": branches,
        "branch_ranges": branch_ranges,
        "input_range": [min(curve.input_power), max(curve.input_power)],
        "output_range": [min(curve.output_power), max(curve.output_power)],
        "hysteresis_thresholds": (
            [curve.metadata.lower_threshold, curve.metadata.upper_threshold]
            if curve.metadata.lower_threshold is not None
            else None
        ),
        "warnings": warnings,
    }
    print(json.dumps(summary, indent=2))
    return 0
