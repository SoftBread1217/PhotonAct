# Contributing to PhotonAct

Thank you for improving PhotonAct. Open an issue before a large architectural change. Keep pull
requests focused, add tests, and run `pytest`, `ruff check .`, and `mypy photonact`.

Device curves require metadata with units, valid range, provenance, and license. Explicitly label data
as measured, simulated, digitized, or synthetic. Do not submit private, restricted, or unverifiable
data. Future benchmark claims must include configuration, seeds, raw results, environment metadata,
and a script that regenerates them.

Use type annotations and short docstrings for public APIs. Do not commit datasets, weights, caches,
or benchmark output. By contributing code, you agree that it is licensed under MIT; data may declare
a separate compatible license in its metadata.
