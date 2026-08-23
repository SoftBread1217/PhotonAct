"""Convert a CSV response into an activation and backpropagate through it."""

import torch

from photonact import CurveActivation

activation = CurveActivation.from_file("examples/curves/sample_phh.csv", branch="up")
inputs = torch.tensor([0.25, 0.75, 1.25], requires_grad=True)
outputs = activation(inputs)
outputs.sum().backward()
print("outputs:", outputs.detach().tolist())
print("gradients:", inputs.grad.tolist() if inputs.grad is not None else None)
