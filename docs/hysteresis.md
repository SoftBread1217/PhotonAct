# Hysteresis semantics

`CurveActivation` remains the stateless API for selecting one named response branch.
`HysteresisActivation` is the trajectory API for a two-branch response with explicit state.

## State-transition rule

The default mapping is:

| State | Selected curve | Physical interpretation |
| --- | --- | --- |
| `False` | `up` | low state during an increasing input scan |
| `True` | `down` | high state during a decreasing input scan |

For an input value `x` and previous state `s`, the next state is:

```text
False, if x <= lower_threshold
True,  if x >= upper_threshold
s,     otherwise
```

The output is evaluated on the branch selected by the **next** state. Equality is intentional, so
the switching rule is deterministic at either threshold. The piecewise-linear branch interpolation
is differentiable with respect to input away from knots and switching discontinuities.

## Single steps, sequences, and reset

One step accepts and returns state:

```python
y, next_state = layer(x, state)
```

`state` may be a scalar Boolean or a Boolean tensor broadcastable to `x`, allowing independent
states in a batch. The layer does not mutate an internal state. Reset a trajectory by passing
`False` (or a Boolean tensor of the desired initial states) again.

For time-major input, scan the first dimension:

```python
y, state_history = layer.forward_sequence(x_time_major, initial_state=False)
```

The returned state history has the same shape as the input. Empty sequences and non-finite values
are rejected.

## Serialization

Thresholds and both branch samples are registered PyTorch buffers. They follow `.to(device)` and
are included in `state_dict()`. The current trajectory state is deliberately excluded: callers own
that state and decide when to preserve or reset it.

## Scientific boundary

This rule is a compact, reproducible approximation of a two-branch quasistatic response. It is not
a time-domain electromagnetic model. It does not infer switching latency, scan-rate dependence,
memory relaxation, noise, drift, or physical stability from a static curve. Those effects require
separate evidence and explicit models.
