"""Tests for explicit-state hysteresis semantics."""

import pytest
import torch

from photonact import CurveData, CurveMetadata, HysteresisActivation


@pytest.fixture
def activation() -> HysteresisActivation:
    """Return a two-branch curve with distinct slopes."""
    curve = CurveData(
        input_power=(0.0, 1.0, 2.0, 0.0, 1.0, 2.0),
        output_power=(0.0, 1.0, 2.0, 10.0, 12.0, 14.0),
        branch=("up", "up", "up", "down", "down", "down"),
        metadata=CurveMetadata(
            valid_min=0.0,
            valid_max=2.0,
            lower_threshold=0.5,
            upper_threshold=1.5,
        ),
    )
    return HysteresisActivation(curve)


def test_sequence_switches_and_retains_state(activation):
    values = torch.tensor([0.0, 1.0, 2.0, 1.0, 0.25])
    outputs, states = activation.forward_sequence(values)
    torch.testing.assert_close(outputs, torch.tensor([0.0, 1.0, 14.0, 12.0, 0.25]))
    assert states.tolist() == [False, False, True, True, False]


def test_threshold_equality_switches_deterministically(activation):
    outputs, states = activation.forward_sequence(torch.tensor([1.5, 0.5]))
    torch.testing.assert_close(outputs, torch.tensor([13.0, 0.5]))
    assert states.tolist() == [True, False]


def test_batched_step_uses_independent_states(activation):
    outputs, states = activation(torch.tensor([2.0, 0.25]), torch.tensor([False, True]))
    torch.testing.assert_close(outputs, torch.tensor([14.0, 0.25]))
    assert states.tolist() == [True, False]


def test_gradients_follow_selected_branches(activation):
    values = torch.tensor([1.0, 1.0], requires_grad=True)
    outputs, _ = activation(values, torch.tensor([False, True]))
    outputs.sum().backward()
    torch.testing.assert_close(values.grad, torch.tensor([1.0, 2.0]))


def test_state_must_broadcast_to_input(activation):
    with pytest.raises(ValueError, match="broadcastable"):
        activation(torch.tensor([0.2, 0.3]), torch.tensor([False, True, False]))


def test_sequence_requires_time_dimension(activation):
    with pytest.raises(ValueError, match="time dimension"):
        activation.forward_sequence(torch.tensor(0.2))
    with pytest.raises(ValueError, match="time dimension"):
        activation.forward_sequence(torch.empty(0))


def test_thresholds_are_serialized(activation):
    state_dict = activation.state_dict()
    assert state_dict["_lower_threshold"].item() == pytest.approx(0.5)
    assert state_dict["_upper_threshold"].item() == pytest.approx(1.5)
