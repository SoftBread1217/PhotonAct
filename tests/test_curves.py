"""Tests for file loading and curve interpolation."""

import json

import pytest
import torch

from photonact import CurveActivation, load_curve


def test_load_json_and_backward(tmp_path):
    path = tmp_path / "curve.json"
    path.write_text(
        json.dumps(
            {
                "metadata": {"name": "test", "input_unit": "W"},
                "points": [
                    {"input_power": 0, "output_power": 0},
                    {"input_power": 1, "output_power": 2},
                    {"input_power": 2, "output_power": 3},
                ],
            }
        ),
        encoding="utf-8",
    )
    activation = CurveActivation(load_curve(path))
    values = torch.tensor([0.5, 1.5], requires_grad=True)
    activation(values).sum().backward()
    torch.testing.assert_close(values.grad, torch.tensor([2.0, 1.0]))


def test_csv_metadata_and_normalization(tmp_path):
    path = tmp_path / "curve.csv"
    path.write_text("input_power,output_power,branch\n10,2,single\n20,6,single\n", encoding="utf-8")
    path.with_suffix(".meta.json").write_text(
        json.dumps({"name": "csv", "valid_min": 10, "valid_max": 20}), encoding="utf-8"
    )
    activation = CurveActivation.from_file(path, normalize_input=True, normalize_output=True)
    torch.testing.assert_close(activation(torch.tensor([0.5])), torch.tensor([0.5]))


def test_clamp_has_zero_gradient_outside_range():
    curve = load_curve("examples/curves/sample_phh.csv").select_branch("up")
    activation = CurveActivation(curve, extrapolation="clamp")
    values = torch.tensor([-1.0, 1.0, 9.0], requires_grad=True)
    activation(values).sum().backward()
    assert values.grad is not None
    assert values.grad[0] == 0 and values.grad[-1] == 0


def test_multibranch_requires_selection():
    curve = load_curve("examples/curves/sample_phh.csv")
    with pytest.raises(ValueError, match="explicit branch"):
        CurveActivation(curve)


@pytest.mark.parametrize(
    "metadata",
    [
        {"lower_threshold": 0.5},
        {"lower_threshold": 1.5, "upper_threshold": 0.5},
        {"lower_threshold": -0.1, "upper_threshold": 0.5},
    ],
)
def test_hysteresis_threshold_metadata_is_complete_and_ordered(tmp_path, metadata):
    path = tmp_path / "curve.json"
    path.write_text(
        json.dumps(
            {
                "metadata": metadata,
                "points": [
                    {"input_power": 0, "output_power": 0},
                    {"input_power": 1, "output_power": 1},
                ],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="threshold"):
        load_curve(path)


def test_curve_rejects_nonfinite_points(tmp_path):
    path = tmp_path / "curve.json"
    path.write_text(
        '[{"input_power": 0, "output_power": 0}, '
        '{"input_power": 1, "output_power": "NaN"}]',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="finite"):
        load_curve(path)


def test_gradcheck():
    curve = load_curve("examples/curves/sample_phh.csv").select_branch("up")
    activation = CurveActivation(curve).double()
    values = torch.tensor([0.25, 0.75, 1.25], dtype=torch.float64, requires_grad=True)
    assert torch.autograd.gradcheck(activation, (values,), eps=1e-6, atol=1e-4)
