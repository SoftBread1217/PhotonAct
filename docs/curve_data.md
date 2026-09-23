# Curve data specification

PhotonAct accepts UTF-8 CSV and JSON. Each point has numeric `input_power` and `output_power`.
`branch` is optional and defaults to `single`. Points inside every branch must be strictly increasing
in input. A multi-branch file must be passed to `CurveActivation` with an explicit branch.

For CSV, metadata is optional JSON beside the curve: `device.csv` uses `device.meta.json`. JSON curves
may use `{"metadata": {...}, "points": [...]}`. Extra CSV columns such as `transmittance` are kept in
the source file for auditability but ignored by the activation loader.

Supported metadata keys are:

- identity and provenance: `name`, `source`, `data_kind`, `license`, `citation`, `notes`;
- physical meaning: `input_unit`, `output_unit`, `response_quantity`, `wavelength_nm`,
  `polarization`;
- numerical domain: `valid_min`, `valid_max`, `normalized`; and
- hysteresis semantics: `lower_threshold`, `upper_threshold`.

The valid range must contain every sampled input. PhotonAct supports three out-of-range policies:
`clamp` holds the boundary output, `linear` continues the first/last segment, and `error` rejects an
out-of-range tensor. Normalizing input changes the layer's expected range to `[0, 1]`; normalizing
output maps the sampled output minimum/maximum to `[0, 1]`.

Never label digitized, simulated, or synthetic points as measured data. Record digitization tools and
figure citations when a publication license permits digitization.

For hysteresis curves, provide both thresholds or neither. They must be finite, ordered as
`valid_min <= lower_threshold < upper_threshold <= valid_max`, and have the same physical unit as
`input_power`. See [hysteresis.md](hysteresis.md) for the state-transition rule.

## Preparing an external table

`photonact prepare` accepts a CSV with named header columns or an XLSX sheet with explicitly
selected Excel column letters/numbers. It supports a long table with a branch column and a wide
table with separate up/down input-output column pairs. XLSX input needs
`python -m pip install -e ".[data]"`. The source is never edited.

```bash
photonact prepare examples/curves/sample_phh.csv --output-dir local_data/roundtrip \
  --name roundtrip --input-column input_power --output-column output_power \
  --branch-column branch --input-unit normalized_power --output-unit normalized_power \
  --source-description "Bundled synthetic demonstration" --data-kind synthetic \
  --license CC0-1.0 --lower-threshold 0.6 --upper-threshold 1.4
```

The command writes `roundtrip.csv`, `roundtrip.meta.json`, and
`roundtrip.preparation.json`. The report records the source SHA-256 and every conversion option.
Existing output files are not overwritten. `--sort` explicitly sorts points within each branch;
otherwise descending or duplicate input values are rejected. For transmittance data, use
`--transform input-times-transmittance` only when the source column is power transmittance and
the desired output is input power multiplied by transmittance. The original transmittance is kept
in the canonical CSV. No smoothing or threshold inference occurs.

For a wide XLSX sweep, select `--sheet`, `--up-input-column`, `--up-output-column`,
`--down-input-column`, and `--down-output-column`. Add `--start-row` and `--end-row` if the
worksheet includes headers or footer material. Source, data kind, license, units, and both
thresholds (when present) must be stated by the caller. Keep private output in `local_data/`.
