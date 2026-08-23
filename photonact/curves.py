"""Curve file parsing and validation."""

from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class CurveMetadata:
    """Human-readable provenance and physical meaning of a device curve."""

    name: str = "unnamed"
    input_unit: str = "arbitrary_unit"
    output_unit: str = "arbitrary_unit"
    source: str = "unspecified"
    valid_min: float | None = None
    valid_max: float | None = None
    normalized: bool = False
    license: str = "unspecified"
    citation: str = ""
    notes: str = ""

    @classmethod
    def from_dict(cls, values: dict[str, Any]) -> CurveMetadata:
        """Create metadata while rejecting unknown keys."""
        allowed = {field.name for field in fields(cls)}
        unknown = set(values) - allowed
        if unknown:
            raise ValueError(f"Unknown metadata fields: {sorted(unknown)}")
        return cls(**values)

    def to_dict(self) -> dict[str, Any]:
        """Return JSON-serializable metadata."""
        return asdict(self)


@dataclass(frozen=True)
class CurveData:
    """Validated curve points and their metadata."""

    input_power: tuple[float, ...]
    output_power: tuple[float, ...]
    branch: tuple[str, ...]
    metadata: CurveMetadata

    def select_branch(self, branch: str) -> CurveData:
        """Return only points from one named branch."""
        indexes = [index for index, value in enumerate(self.branch) if value == branch]
        if not indexes:
            raise ValueError(f"Curve has no {branch!r} branch")
        return CurveData(
            tuple(self.input_power[index] for index in indexes),
            tuple(self.output_power[index] for index in indexes),
            tuple(self.branch[index] for index in indexes),
            self.metadata,
        )

    def to_dict(self) -> dict[str, Any]:
        """Return the canonical JSON representation."""
        return {
            "metadata": self.metadata.to_dict(),
            "points": [
                {"input_power": x, "output_power": y, "branch": branch}
                for x, y, branch in zip(
                    self.input_power, self.output_power, self.branch, strict=True
                )
            ],
        }


def _read_csv(path: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    with path.open(newline="", encoding="utf-8") as stream:
        points = list(csv.DictReader(stream))
    sidecar = path.with_suffix(".meta.json")
    metadata = json.loads(sidecar.read_text(encoding="utf-8")) if sidecar.exists() else {}
    return points, metadata


def _read_json(path: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return payload, {}
    if not isinstance(payload, dict) or "points" not in payload:
        raise ValueError("JSON curve must be a point list or contain 'points'")
    return payload["points"], payload.get("metadata", {})


def load_curve(path: str | Path) -> CurveData:
    """Load and validate a CSV or JSON optical response curve."""
    curve_path = Path(path)
    if curve_path.suffix.lower() == ".csv":
        points, metadata_values = _read_csv(curve_path)
    elif curve_path.suffix.lower() == ".json":
        points, metadata_values = _read_json(curve_path)
    else:
        raise ValueError("Curve path must end in .csv or .json")
    if len(points) < 2:
        raise ValueError("A curve needs at least two points")
    try:
        x = [float(point["input_power"]) for point in points]
        y = [float(point["output_power"]) for point in points]
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("Every point needs numeric input_power and output_power") from error
    branches = [str(point.get("branch", "single")).strip().lower() for point in points]
    metadata = CurveMetadata.from_dict(metadata_values)
    valid_min = min(x) if metadata.valid_min is None else metadata.valid_min
    valid_max = max(x) if metadata.valid_max is None else metadata.valid_max
    if valid_min > min(x) or valid_max < max(x) or valid_min >= valid_max:
        raise ValueError("Metadata valid range must contain all curve points")
    metadata = CurveMetadata.from_dict(
        {**metadata.to_dict(), "valid_min": valid_min, "valid_max": valid_max}
    )
    for branch in set(branches):
        branch_x = [value for value, label in zip(x, branches, strict=True) if label == branch]
        if len(branch_x) < 2 or any(a >= b for a, b in zip(branch_x, branch_x[1:], strict=False)):
            raise ValueError(f"Input points in branch {branch!r} must be strictly increasing")
    return CurveData(tuple(x), tuple(y), tuple(branches), metadata)
