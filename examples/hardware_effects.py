"""Compare an uncalibrated synthetic curve with explicit hardware effects."""

from __future__ import annotations

import json

import torch

from photonact import HardwareAwareActivation, HardwareEffects, HysteresisActivation, load_curve


def main() -> None:
    """Print reproducible synthetic examples without using any paper data."""
    curve = load_curve("examples/curves/sample_phh.csv")
    trajectory = torch.tensor([0.2, 0.9, 1.6, 1.0, 0.3])
    cases = {
        "baseline": HardwareEffects(),
        "drift": HardwareEffects(input_drift=0.05),
        "loss": HardwareEffects(insertion_loss_db=1.0),
        "range": HardwareEffects(output_min=0.0, output_max=0.5),
        "quantization": HardwareEffects(
            quantization_step=0.1, quantization_gradient="straight_through"
        ),
        "noise": HardwareEffects(noise_std=0.02),
        "combined": HardwareEffects(
            input_drift=0.05,
            insertion_loss_db=1.0,
            output_min=0.0,
            output_max=0.5,
            quantization_step=0.1,
            quantization_gradient="straight_through",
            noise_std=0.02,
        ),
    }
    print("Synthetic demonstration; effect parameters are not hardware calibrations.")
    for label, effects in cases.items():
        seed = 2026
        generator = torch.Generator().manual_seed(seed)
        activation = HardwareAwareActivation(HysteresisActivation(curve), effects)
        output, state = activation.forward_sequence(trajectory, generator=generator)
        print(
            json.dumps(
                {
                    "case": label,
                    "seed": seed,
                    "effects": effects.to_dict(),
                    "output": output.tolist(),
                    "high_state": state.tolist(),
                }
            )
        )


if __name__ == "__main__":
    main()
