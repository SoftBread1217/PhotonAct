# Hardware effects in v0.2.0

`HardwareAwareActivation` wraps a `CurveActivation` or `HysteresisActivation`.
`HardwareEffects()` disables all effects and preserves the wrapped layer's output and gradient.
The parameter values in the bundled example are illustrative, not hardware calibrations.

```python
import torch
from photonact import CurveActivation, HardwareAwareActivation, HardwareEffects

base = CurveActivation.from_file("examples/curves/sample_phh.csv", branch="up")
effects = HardwareEffects(
    input_drift=0.05,
    insertion_loss_db=1.0,
    output_min=0.0,
    output_max=1.0,
    quantization_step=0.1,
    quantization_gradient="straight_through",
    noise_std=0.02,
)
layer = HardwareAwareActivation(base, effects)
generator = torch.Generator().manual_seed(2026)
y = layer(torch.tensor([0.25, 0.75, 1.25]), generator=generator)
```

For hysteresis, pass the previous Boolean state as the second argument or use
`forward_sequence(values, initial_state=False, generator=generator)`. The wrapped layer still owns
no hidden trajectory state.

## Order and units

1. Add `input_drift` to the input in the curve's effective input unit. This driven value also
   determines hysteresis switching. With `normalize_input=True`, the effective unit is normalized.
2. Evaluate the underlying branch or state-dependent curve.
3. Multiply output power by `10 ** (-insertion_loss_db / 10)`. Loss must be non-negative and
   the curve's `response_quantity` must describe power.
4. Clamp to `[output_min, output_max]` when both limits are configured.
5. Round to the nearest multiple of `quantization_step` using PyTorch's round-to-even rule.
6. Add zero-mean Gaussian readout noise with standard deviation `noise_std`.

Output limits, quantization step, and noise standard deviation use the layer's effective output
unit. With `normalize_output=True`, this is normalized output. No effect performs implicit unit
conversion. Noise requires a caller-owned seeded `torch.Generator`; the same generator is consumed
sequentially in a hysteresis trajectory.

## Gradients and reproducibility

Range limiting has zero gradient outside its limits. Exact quantization
(`quantization_gradient="zero"`) has zero gradient almost everywhere. The optional
`"straight_through"` mode uses the exact rounded value in the forward pass and the identity
gradient in the backward pass. This is a training surrogate, not a physical derivative. Added
readout noise treats the sampled noise as constant in backward propagation. Switching
discontinuities in hysteresis are not differentiable.

The effect configuration supports `to_dict()` and `from_dict()`, and is stored as extra state
in the wrapper's PyTorch `state_dict()`. Save the random generator's state separately if you need
to continue a stochastic sequence from an exact checkpoint. Run
`python examples/hardware_effects.py` to see every effect alone and in combination.
