# Changelog

All notable changes to PhotonAct are documented in this file. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned

- Define explicit stateful and stateless hysteresis semantics.
- Add reproducible comparison benchmarks with auditable raw results.

## [0.0.1] - 2026-09-20

### Added

- CSV and JSON curve loading with metadata and provenance fields.
- Validation for finite values, strict input ordering, branches, and valid ranges.
- Differentiable piecewise-linear `CurveActivation` with explicit extrapolation and normalization.
- A command-line curve inspector, a minimal backward-pass example, and an introductory notebook.
- Synthetic two-branch demonstration data clearly separated from experimental or paper data.
- Tests across Python 3.10-3.12 and an installed-wheel smoke test in CI.
- English and Chinese documentation, contribution guidance, citation metadata, a security policy,
  and a milestone-based roadmap.

[Unreleased]: https://github.com/SoftBread1217/PhotonAct/compare/v0.0.1...HEAD
[0.0.1]: https://github.com/SoftBread1217/PhotonAct/releases/tag/v0.0.1
