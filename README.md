# PhotonAct

**PhotonAct turns measured or simulated optical-device response curves into differentiable,
hysteresis-aware PyTorch activation functions.**

[![CI](https://github.com/SoftBread1217/PhotonAct/actions/workflows/ci.yml/badge.svg)](https://github.com/SoftBread1217/PhotonAct/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/Python-3.10--3.12-blue)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

![PhotonAct workflow](assets/workflow.svg)

```bash
python -m pip install -e .
photonact inspect examples/curves/sample_phh.csv
python examples/minimal.py
python examples/hysteresis.py
```

```python
import torch
from photonact import CurveActivation

layer = CurveActivation.from_file("examples/curves/sample_phh.csv", branch="up")
x = torch.tensor([0.25, 0.75, 1.25], requires_grad=True)
layer(x).sum().backward()
print(x.grad)
```

> **Status:** v0.1.0. The stateless curve layer and the explicit-state hysteresis layer are tested
> on Python 3.10-3.12. The bundled `sample_phh` curve is
> synthetic demonstration data, not experimental data and not digitized from a paper.

[中文说明](README_zh.md)

## Why PhotonAct

Researchers often have discrete input/output power points but no simple way to use them inside a
PyTorch model. PhotonAct provides the smallest useful bridge:

```text
documented CSV or JSON -> validated branches -> torch.nn.Module -> autograd
```

It does not include an electromagnetic simulator and does not invent unavailable device data.

## Scope and Non-Goals

PhotonAct focuses on the boundary between an optical response curve and a machine-learning model:

- validate documented measured, simulated, digitized, or synthetic curve data;
- expose the curve as a small, differentiable `torch.nn.Module`;
- make branch selection, hysteresis state, extrapolation, normalization, and future hardware effects
  explicit; and
- provide reproducible benchmarks whose configurations and raw results can be audited.

PhotonAct is not an electromagnetic solver, a substitute for device characterization, or evidence
that a model matches physical hardware without documented provenance. It does not claim to reproduce
the motivating paper while that paper's underlying curve data remain unavailable.

## Installation

PhotonAct targets Python 3.10-3.12.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

Development tools are optional:

```bash
python -m pip install -e ".[dev]"
pytest
ruff check .
mypy photonact
```

## Curve Data Format

CSV files use `input_power`, `output_power`, and an optional `branch` column:

```csv
input_power,output_power,branch
0.0,0.00,up
0.4,0.04,up
0.0,0.00,down
0.4,0.08,down
```

Within each branch, input values must be strictly increasing. For `device.csv`, optional metadata is
stored in `device.meta.json`:

```json
{
  "name": "my_device",
  "input_unit": "mW",
  "output_unit": "mW",
  "source": "Measured in Example Lab on 2026-01-01",
  "valid_min": 0.0,
  "valid_max": 2.0,
  "normalized": false,
  "license": "CC-BY-4.0",
  "citation": "DOI or lab record"
}
```

JSON may contain `{"metadata": {...}, "points": [...]}` or just a list of points. See
[docs/curve_data.md](docs/curve_data.md).

## Stateful Hysteresis

`HysteresisActivation` switches between the increasing-scan (`up`) and decreasing-scan (`down`)
curves with explicit state. The module never hides trajectory state inside a global or persistent
attribute: each step receives the previous state and returns the next one.

```python
import torch
from photonact import HysteresisActivation

layer = HysteresisActivation.from_file("examples/curves/sample_phh.csv")
x = torch.tensor([0.2, 1.0, 1.8, 1.0, 0.2], requires_grad=True)
y, state_history = layer.forward_sequence(x, initial_state=False)
y.sum().backward()
```

At or above `upper_threshold`, the state switches high and selects the `down` branch. At or below
`lower_threshold`, it switches low and selects the `up` branch. Between those thresholds it retains
the supplied state. See [docs/hysteresis.md](docs/hysteresis.md) for batched inputs, reset behavior,
and gradient semantics.

## Interpolation Semantics

`CurveActivation` uses differentiable piecewise-linear interpolation. This is easier to inspect and
test than a high-order spline and is the deliberate v0.0.1 choice. Multi-branch curves require an
explicit branch. Out-of-range behavior can be `clamp`, `linear`, or `error`. Input and output can be
normalized independently.

PyTorch automatically moves registered curve points when you call `.to("cuda")`; CPU works by
default. See [examples/minimal.py](examples/minimal.py) and the
[introductory notebook](examples/notebooks/curve_activation.ipynb).

## Data and Paper Boundary

The research motivation includes *Optical Bistability in Photonic Topological Hypercrystals and Its
Applications in Photonic Neural Network* ([Nanomaterials 2026, 16, 561](https://doi.org/10.3390/nano16090561)).
The repository does not ship that paper's underlying data and does not claim to reproduce its
accuracy results.

`sample_phh` is a hand-authored synthetic example with separated up/down branches. Replace it with
appropriately licensed measured, simulated, or digitized data and record its provenance.

Authors who have legitimate access to the Figure 4(b) source workbook can prepare a private local
curve without modifying the workbook:

```bash
python -m pip install -e ".[data]"
python scripts/prepare_phh_1535nm.py path/to/shuangwentiai.xlsx
python examples/hysteresis.py --curve local_data/phh_1535nm/phh_1535nm.csv
```

The converter records the source SHA-256, provenance, wavelength, polarization, transition
intervals, and output-power calculation. Its default destination, `local_data/`, is Git-ignored.
Do not publish the generated files until every relevant author or rights holder has approved the
data license.

## Roadmap

See the milestone definitions and evidence requirements in [docs/roadmap.md](docs/roadmap.md).

## Contributing, Citation, and License

See [CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md), and
[CHANGELOG.md](CHANGELOG.md). Cite PhotonAct with [CITATION.cff](CITATION.cff) and cite device data
separately. Code is released under the [MIT License](LICENSE); data may declare a different license
in metadata.
