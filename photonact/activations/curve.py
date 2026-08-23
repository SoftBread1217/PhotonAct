"""Differentiable piecewise-linear curve activation."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import torch
from torch import Tensor, nn

from photonact.curves import CurveData, load_curve

Extrapolation = Literal["clamp", "linear", "error"]


class CurveActivation(nn.Module):
    """Turn sampled device response points into a differentiable PyTorch layer."""

    def __init__(
        self,
        curve: CurveData,
        *,
        branch: str | None = None,
        normalize_input: bool = False,
        normalize_output: bool = False,
        extrapolation: Extrapolation = "clamp",
    ) -> None:
        """Initialize interpolation, normalization, and range policy."""
        super().__init__()
        if extrapolation not in {"clamp", "linear", "error"}:
            raise ValueError(f"Unsupported extrapolation: {extrapolation}")
        labels = set(curve.branch)
        if branch is not None:
            curve = curve.select_branch(branch)
        elif len(labels) > 1:
            raise ValueError("Multi-branch curve requires an explicit branch")
        x = torch.tensor(curve.input_power, dtype=torch.float64)
        y = torch.tensor(curve.output_power, dtype=torch.float64)
        self.input_min = float(x[0])
        self.input_max = float(x[-1])
        self.output_min = float(y.min())
        self.output_max = float(y.max())
        self.normalize_input = normalize_input
        self.normalize_output = normalize_output
        self.extrapolation = extrapolation
        self.metadata = curve.metadata
        if normalize_input:
            x = (x - x[0]) / (x[-1] - x[0])
        if normalize_output:
            span = y.max() - y.min()
            if span == 0:
                raise ValueError("Cannot normalize a constant output curve")
            y = (y - y.min()) / span
        self.x_points: Tensor
        self.y_points: Tensor
        self.register_buffer("x_points", x)
        self.register_buffer("y_points", y)

    @classmethod
    def from_file(cls, path: str | Path, **kwargs: object) -> CurveActivation:
        """Build a curve activation directly from CSV or JSON."""
        return cls(load_curve(path), **kwargs)  # type: ignore[arg-type]

    @property
    def effective_input_range(self) -> tuple[float, float]:
        """Return the range expected by the layer after optional normalization."""
        return (0.0, 1.0) if self.normalize_input else (self.input_min, self.input_max)

    def forward(self, values: Tensor) -> Tensor:
        """Interpolate values with piecewise-constant, meaningful gradients."""
        original_dtype = values.dtype
        x = self.x_points.to(dtype=values.dtype)
        y = self.y_points.to(dtype=values.dtype)
        low, high = float(x[0]), float(x[-1])
        if self.extrapolation == "error" and bool(((values < low) | (values > high)).any()):
            raise ValueError(f"Input outside valid range [{low}, {high}]")
        interpolation_values = values.clamp(low, high) if self.extrapolation == "clamp" else values
        indexes = torch.searchsorted(x, interpolation_values.contiguous(), right=True) - 1
        indexes = indexes.clamp(0, x.numel() - 2)
        x0, x1 = x[indexes], x[indexes + 1]
        y0, y1 = y[indexes], y[indexes + 1]
        output = y0 + (interpolation_values - x0) * (y1 - y0) / (x1 - x0)
        return output.to(dtype=original_dtype)
