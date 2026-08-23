# Curve data specification

PhotonAct accepts UTF-8 CSV and JSON. Each point has numeric `input_power` and `output_power`.
`branch` is optional and defaults to `single`. Points inside every branch must be strictly increasing
in input. A multi-branch file must be passed to `CurveActivation` with an explicit branch.

For CSV, metadata is optional JSON beside the curve: `device.csv` uses `device.meta.json`. JSON curves
may use `{"metadata": {...}, "points": [...]}`. Supported metadata keys are `name`, `input_unit`,
`output_unit`, `source`, `valid_min`, `valid_max`, `normalized`, `license`, `citation`, and `notes`.

The valid range must contain every sampled input. PhotonAct supports three out-of-range policies:
`clamp` holds the boundary output, `linear` continues the first/last segment, and `error` rejects an
out-of-range tensor. Normalizing input changes the layer's expected range to `[0, 1]`; normalizing
output maps the sampled output minimum/maximum to `[0, 1]`.

Never label digitized, simulated, or synthetic points as measured data. Record digitization tools and
figure citations when a publication license permits digitization.
