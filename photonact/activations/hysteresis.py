"""Explicit-state hysteresis activation."""

from __future__ import annotations

from pathlib import Path

import torch
from torch import Tensor, nn

from photonact.activations.curve import CurveActivation, Extrapolation
from photonact.curves import CurveData, load_curve


class HysteresisActivation(nn.Module):
    """Interpolate low/high branches with explicit Schmitt-trigger-like state."""

    def __init__(
        self,
        curve: CurveData,
        *,
        lower_threshold: float | None = None,
        upper_threshold: float | None = None,
        low_state_branch: str = "up",
        high_state_branch: str = "down",
        extrapolation: Extrapolation = "clamp",
    ) -> None:
        """Initialize branch curves and switching thresholds.

        The state is intentionally not stored on the module. Callers pass it into ``forward`` and
        receive the next state, which keeps batched and serialized trajectories reproducible.
        """
        super().__init__()
        lower = curve.metadata.lower_threshold if lower_threshold is None else lower_threshold
        upper = curve.metadata.upper_threshold if upper_threshold is None else upper_threshold
        if lower is None or upper is None:
            raise ValueError("HysteresisActivation requires lower and upper thresholds")
        if lower >= upper:
            raise ValueError("lower_threshold must be less than upper_threshold")

        self.low_curve = CurveActivation(
            curve, branch=low_state_branch, extrapolation=extrapolation
        )
        self.high_curve = CurveActivation(
            curve, branch=high_state_branch, extrapolation=extrapolation
        )
        if self.low_curve.effective_input_range != self.high_curve.effective_input_range:
            raise ValueError("Hysteresis branches must have the same input range")
        low, high = self.low_curve.effective_input_range
        if not low <= lower < upper <= high:
            raise ValueError("Hysteresis thresholds must be inside the branch input range")

        self.low_state_branch = low_state_branch
        self.high_state_branch = high_state_branch
        self.metadata = curve.metadata
        self._lower_threshold: Tensor
        self._upper_threshold: Tensor
        self.register_buffer("_lower_threshold", torch.tensor(lower, dtype=torch.float64))
        self.register_buffer("_upper_threshold", torch.tensor(upper, dtype=torch.float64))

    @classmethod
    def from_file(cls, path: str | Path, **kwargs: object) -> HysteresisActivation:
        """Build a hysteresis activation directly from CSV or JSON."""
        return cls(load_curve(path), **kwargs)  # type: ignore[arg-type]

    @property
    def lower_threshold(self) -> float:
        """Return the high-to-low switching threshold."""
        return float(self._lower_threshold.item())

    @property
    def upper_threshold(self) -> float:
        """Return the low-to-high switching threshold."""
        return float(self._upper_threshold.item())

    @staticmethod
    def _broadcast_state(state: Tensor | bool, values: Tensor) -> Tensor:
        state_tensor = torch.as_tensor(state, dtype=torch.bool, device=values.device)
        try:
            return torch.broadcast_to(state_tensor, values.shape)
        except RuntimeError as error:
            raise ValueError("State must be broadcastable to the input shape") from error

    def forward(self, values: Tensor, state: Tensor | bool) -> tuple[Tensor, Tensor]:
        """Evaluate one step and return ``(output, next_state)``.

        ``False`` selects the low-state (normally increasing-scan) branch and ``True`` selects the
        high-state (normally decreasing-scan) branch. Values at or above the upper threshold switch
        high; values at or below the lower threshold switch low; the interval between them retains
        the supplied state.
        """
        if not bool(torch.isfinite(values).all()):
            raise ValueError("Activation input must be finite")
        current_state = self._broadcast_state(state, values)
        lower = self._lower_threshold.to(device=values.device, dtype=values.dtype)
        upper = self._upper_threshold.to(device=values.device, dtype=values.dtype)
        next_state = torch.where(values >= upper, torch.ones_like(current_state), current_state)
        next_state = torch.where(values <= lower, torch.zeros_like(next_state), next_state)
        low_output = self.low_curve(values)
        high_output = self.high_curve(values)
        return torch.where(next_state, high_output, low_output), next_state

    def forward_sequence(
        self, values: Tensor, initial_state: Tensor | bool = False
    ) -> tuple[Tensor, Tensor]:
        """Scan the first tensor dimension and return outputs plus the full state history."""
        if values.ndim == 0 or values.shape[0] == 0:
            raise ValueError("A hysteresis sequence needs a non-empty time dimension")
        state: Tensor | bool = initial_state
        outputs: list[Tensor] = []
        states: list[Tensor] = []
        for step in values.unbind(0):
            output, next_state = self(step, state)
            state = next_state
            outputs.append(output)
            states.append(next_state)
        return torch.stack(outputs), torch.stack(states)
