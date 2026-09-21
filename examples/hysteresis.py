"""Run an explicit-state hysteresis trajectory."""

from __future__ import annotations

import argparse
from pathlib import Path

import torch

from photonact import HysteresisActivation


def main() -> None:
    """Evaluate a rising then falling input trajectory."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--curve", type=Path, default=Path("examples/curves/sample_phh.csv")
    )
    arguments = parser.parse_args()
    activation = HysteresisActivation.from_file(arguments.curve)
    inputs = torch.tensor([0.2, 0.8, 1.3, 1.5, 1.8, 1.0, 0.7, 0.5, 0.2])
    outputs, states = activation.forward_sequence(inputs)
    for input_value, output, high_state in zip(inputs, outputs, states, strict=True):
        print(
            f"input={input_value.item():.3f} output={output.item():.3f} "
            f"state={'high' if high_state.item() else 'low'}"
        )


if __name__ == "__main__":
    main()
