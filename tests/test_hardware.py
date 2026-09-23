"""Tests for explicit hardware-effect semantics."""

from dataclasses import replace

import pytest
import torch

from photonact import (
    CurveActivation,
    HardwareAwareActivation,
    HardwareEffects,
    HysteresisActivation,
    load_curve,
)


def test_no_effect_preserves_baseline_and_gradient():
    curve = load_curve("examples/curves/sample_phh.csv")
    baseline = CurveActivation(curve, branch="up")
    wrapped = HardwareAwareActivation(baseline)
    x1 = torch.tensor([0.3, 1.1], requires_grad=True)
    x2 = x1.detach().clone().requires_grad_()
    y1, y2 = baseline(x1), wrapped(x2)
    torch.testing.assert_close(y1, y2, rtol=0, atol=0)
    assert isinstance(y2, torch.Tensor)
    y1.sum().backward()
    y2.sum().backward()
    torch.testing.assert_close(x1.grad, x2.grad, rtol=0, atol=0)


def test_no_effect_preserves_hysteresis_trajectory():
    curve = load_curve("examples/curves/sample_phh.csv")
    baseline = HysteresisActivation(curve)
    wrapped = HardwareAwareActivation(baseline)
    values = torch.tensor([0.2, 1.5, 1.0, 0.2])
    expected_output, expected_state = baseline.forward_sequence(values)
    output, state = wrapped.forward_sequence(values)
    torch.testing.assert_close(output, expected_output, rtol=0, atol=0)
    torch.testing.assert_close(state, expected_state, rtol=0, atol=0)


def test_effect_order_and_state_change_after_input_drift():
    curve = load_curve("examples/curves/sample_phh.csv")
    baseline = HysteresisActivation(curve)
    effects = HardwareEffects(
        input_drift=0.2,
        insertion_loss_db=10,
        output_min=0,
        output_max=0.2,
        quantization_step=0.1,
    )
    wrapped = HardwareAwareActivation(baseline, effects)
    x = torch.tensor([1.3])
    actual, state = wrapped(x, False)
    assert state.tolist() == [True]
    expected, _ = baseline(torch.tensor([1.5]), False)
    expected = torch.round(expected.mul(0.1).clamp(0, 0.2) / 0.1) * 0.1
    torch.testing.assert_close(actual, expected)


def test_quantization_gradient_is_explicit():
    curve = load_curve("examples/curves/sample_phh.csv")
    for convention, expected_gradient in (("zero", 0.0), ("straight_through", 1.0)):
        baseline = CurveActivation(curve, branch="up")
        wrapped = HardwareAwareActivation(
            baseline,
            HardwareEffects(quantization_step=0.1, quantization_gradient=convention),
        )
        value = torch.tensor([0.25], requires_grad=True)
        output = wrapped(value)
        assert isinstance(output, torch.Tensor)
        output.sum().backward()
        baseline_value = value.detach().clone().requires_grad_()
        baseline(baseline_value).sum().backward()
        assert value.grad is not None and baseline_value.grad is not None
        torch.testing.assert_close(value.grad, baseline_value.grad * expected_gradient)


def test_seeded_noise_reproduces_batched_trajectory():
    curve = load_curve("examples/curves/sample_phh.csv")
    wrapped = HardwareAwareActivation(
        HysteresisActivation(curve), HardwareEffects(noise_std=0.02)
    )
    values = torch.tensor([[0.2, 1.5], [1.6, 0.4], [1.0, 1.0]])
    generator_a = torch.Generator().manual_seed(123)
    generator_b = torch.Generator().manual_seed(123)
    outputs_a, states_a = wrapped.forward_sequence(values, generator=generator_a)
    outputs_b, states_b = wrapped.forward_sequence(values, generator=generator_b)
    torch.testing.assert_close(outputs_a, outputs_b, rtol=0, atol=0)
    torch.testing.assert_close(states_a, states_b, rtol=0, atol=0)
    assert states_a.tolist() == [[False, True], [True, False], [True, False]]
    with pytest.raises(ValueError, match="seeded"):
        wrapped.forward_sequence(values)


def test_effect_config_is_saved_with_pytorch_state():
    curve = load_curve("examples/curves/sample_phh.csv")
    options = HardwareEffects(input_drift=0.02, noise_std=0.01)
    first = HardwareAwareActivation(CurveActivation(curve, branch="up"), options)
    second = HardwareAwareActivation(CurveActivation(curve, branch="up"))
    second.load_state_dict(first.state_dict())
    assert second.effects == options
    assert HardwareEffects.from_dict(options.to_dict()) == options


def test_insertion_loss_requires_power_response():
    curve = load_curve("examples/curves/sample_phh.csv")
    non_power = replace(curve, metadata=replace(curve.metadata, response_quantity="transmittance"))
    with pytest.raises(ValueError, match="power response"):
        HardwareAwareActivation(
            CurveActivation(non_power, branch="up"), HardwareEffects(insertion_loss_db=1)
        )


@pytest.mark.parametrize(
    "settings",
    [
        {"noise_std": -1.0},
        {"insertion_loss_db": -0.1},
        {"output_min": 0.0},
        {"output_min": 1.0, "output_max": 1.0},
        {"quantization_step": 0.0},
        {"input_drift": float("nan")},
    ],
)
def test_invalid_effect_settings_fail(settings):
    with pytest.raises(ValueError):
        HardwareEffects(**settings)
