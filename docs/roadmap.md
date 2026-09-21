# PhotonAct Roadmap

PhotonAct grows through small releases with testable scientific and software claims. A milestone is
complete only when its behavior is documented, covered by automated tests, and demonstrated by a
reproducible example. Dates are intentionally omitted; evidence matters more than a rushed label.

## Project Principles

1. **Provenance before performance.** Every device curve states whether it is measured, simulated,
   digitized, or synthetic, together with units, source, valid range, and license.
2. **Explicit semantics.** Branch choice, state, extrapolation, normalization, and hardware effects
   must never be hidden defaults when they can change a scientific conclusion.
3. **Reproducible claims.** Benchmarks include configuration, random seeds, dependency versions, raw
   results, and a command that regenerates the reported summary.
4. **Small trustworthy core.** New abstractions must solve a demonstrated use case without turning
   PhotonAct into an electromagnetic simulator.

## v0.0.x - Reliable Curve Adapter

Current foundation:

- CSV and JSON parsing with metadata validation;
- branch-aware, piecewise-linear differentiable activation;
- explicit clamp, linear, and error extrapolation policies;
- command-line curve inspection;
- Python 3.10-3.12 tests and installed-wheel smoke testing.

Before v0.1, add user-facing error examples, stabilize the curve-data specification, and publish a
small release with complete author and citation metadata.

## v0.1 - Hysteresis Semantics (complete)

- separate `CurveActivation` and explicit-state `HysteresisActivation` APIs;
- deterministic lower/upper threshold transitions and documented reset behavior;
- increasing, decreasing, reversing, batched, serialized, and gradient tests;
- metadata for data kind, response quantity, wavelength, polarization, and thresholds; and
- a deterministic, Git-ignored workflow for preparing legitimately held Figure 4(b) workbook data.

The implementation, documentation, tests, and package build are complete. Publishing any derived
research data separately still requires an approved data license.

## v0.2 - Hardware Effects

Add opt-in, seeded models for quantization, noise, finite dynamic range, insertion loss, and drift.
Every effect must have units or a normalized interpretation, deterministic tests, and a no-effect
configuration that exactly recovers the v0.1 behavior.

## v0.3 - Reproducible Benchmarks

Provide compact MNIST and Fashion-MNIST comparisons between standard digital activations and clearly
labeled PhotonAct curves. Store configurations and raw metric tables, not downloaded datasets or
large model weights. Report multiple seeds and avoid claiming reproduction of unavailable paper data.

## Toward v1.0

Stabilize the curve schema and public Python API, publish migration notes, add broader real-world
curve examples with compatible licenses, and provide a versioned benchmark report. CIFAR-10 and an
interactive curve explorer remain optional until the core evidence chain is reliable.
