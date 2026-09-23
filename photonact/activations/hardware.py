"""Opt-in, reproducible hardware effects around a curve activation."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from math import isfinite
from typing import Any, Literal

import torch
from torch import Tensor, nn

from photonact.activations.curve import CurveActivation
from photonact.activations.hysteresis import HysteresisActivation

QuantizationGradient = Literal["zero", "straight_through"]


@dataclass(frozen=True)
class HardwareEffects:
    """Parameters applied around a curve; all effects are disabled by default."""

    input_drift: float = 0.0
    insertion_loss_db: float = 0.0
    output_min: float | None = None
    output_max: float | None = None
    quantization_step: float | None = None
    quantization_gradient: QuantizationGradient = "zero"
    noise_std: float = 0.0

    def __post_init__(self) -> None:
        """Validate units-independent numerical constraints."""
        for value in (
            self.input_drift,
            self.insertion_loss_db,
            self.output_min,
            self.output_max,
            self.quantization_step,
            self.noise_std,
        ):
            if value is not None and not isfinite(value):
                raise ValueError("Hardware effect parameters must be finite")
        if self.insertion_loss_db < 0 or self.noise_std < 0:
            raise ValueError("Loss and noise standard deviation cannot be negative")
        if (self.output_min is None) != (self.output_max is None):
            raise ValueError("Provide both output range limits or neither")
        if (
            self.output_min is not None
            and self.output_max is not None
            and self.output_min >= self.output_max
        ):
            raise ValueError("Output minimum must be below output maximum")
        if self.quantization_step is not None and self.quantization_step <= 0:
            raise ValueError("Quantization step must be positive")
        if self.quantization_gradient not in {"zero", "straight_through"}:
            raise ValueError("Unsupported quantization gradient convention")

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-compatible configuration."""
        return asdict(self)

    @classmethod
    def from_dict(cls, values: dict[str, Any]) -> HardwareEffects:
        """Restore a configuration without silently dropping unknown fields."""
        return cls(**values)


class HardwareAwareActivation(nn.Module):
    """Apply explicit effects to a stateless or explicit-state optical activation.

    Order: input drift, curve evaluation and switching, output-side loss, range limit,
    quantization, then readout noise. Random sampling requires a caller-owned generator.
    """

    def __init__(
        self,
        layer: CurveActivation | HysteresisActivation,
        effects: HardwareEffects | None = None,
    ) -> None:
        """Wrap a curve or hysteresis layer without changing its default behavior."""
        super().__init__()
        if not isinstance(layer, CurveActivation | HysteresisActivation):
            raise TypeError("Layer must be CurveActivation or HysteresisActivation")
        self.layer = layer
        self.effects = effects if effects is not None else HardwareEffects()
        if self.effects.insertion_loss_db > 0 and "power" not in layer.metadata.response_quantity:
            raise ValueError("Insertion loss in dB requires a power response quantity")

    def get_extra_state(self) -> dict[str, Any]:
        """Store effect parameters alongside the wrapped PyTorch buffers."""
        return self.effects.to_dict()

    def set_extra_state(self, state: dict[str, Any]) -> None:
        """Restore effect parameters from a PyTorch state dictionary."""
        self.effects = HardwareEffects.from_dict(state)

    def _apply_output(self, output: Tensor, generator: torch.Generator | None) -> Tensor:
        effects = self.effects
        if effects.insertion_loss_db:
            output = output * (10.0 ** (-effects.insertion_loss_db / 10.0))
        if effects.output_min is not None and effects.output_max is not None:
            output = output.clamp(effects.output_min, effects.output_max)
        if effects.quantization_step is not None:
            rounded = torch.round(output / effects.quantization_step) * effects.quantization_step
            if effects.quantization_gradient == "straight_through":
                output = output + (rounded - output).detach()
            else:
                output = rounded
        if effects.noise_std:
            if generator is None:
                raise ValueError("Noise requires a caller-owned seeded torch.Generator")
            noise = torch.randn(
                output.shape, dtype=output.dtype, device=output.device, generator=generator
            )
            output = output + effects.noise_std * noise
        return output

    def forward(
        self,
        values: Tensor,
        state: Tensor | bool | None = None,
        *,
        generator: torch.Generator | None = None,
    ) -> Tensor | tuple[Tensor, Tensor]:
        """Evaluate one step, preserving an explicit hysteresis state when present."""
        driven = values + self.effects.input_drift if self.effects.input_drift else values
        if isinstance(self.layer, HysteresisActivation):
            if state is None:
                raise ValueError("Hysteresis activation requires an explicit state")
            output, next_state = self.layer(driven, state)
            return self._apply_output(output, generator), next_state
        if state is not None:
            raise ValueError("A single-branch curve does not accept a state")
        return self._apply_output(self.layer(driven), generator)

    def forward_sequence(
        self,
        values: Tensor,
        initial_state: Tensor | bool = False,
        *,
        generator: torch.Generator | None = None,
    ) -> tuple[Tensor, Tensor]:
        """Evaluate a time-major hysteresis sequence with caller-owned random state."""
        if not isinstance(self.layer, HysteresisActivation):
            raise TypeError("forward_sequence requires HysteresisActivation")
        if values.ndim == 0 or values.shape[0] == 0:
            raise ValueError("A hysteresis sequence needs a non-empty time dimension")
        state: Tensor | bool = initial_state
        outputs: list[Tensor] = []
        states: list[Tensor] = []
        for step in values.unbind(0):
            result = self(step, state, generator=generator)
            assert isinstance(result, tuple)
            output, next_state = result
            outputs.append(output)
            states.append(next_state)
            state = next_state
        return torch.stack(outputs), torch.stack(states)
