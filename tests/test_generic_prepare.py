"""Tests for auditable conversion of external curve tables."""

import hashlib
import json

import pytest

from photonact import PrepareOptions, load_curve, prepare_curve
from photonact.cli import main


def _options(**overrides):
    values = {
        "name": "device",
        "input_column": "drive",
        "output_column": "response",
        "branch_column": "scan",
        "input_unit": "W/m",
        "output_unit": "W/m",
        "source_description": "Synthetic test instrument export",
        "data_kind": "synthetic",
        "license": "CC0-1.0",
        "lower_threshold": 0.4,
        "upper_threshold": 0.6,
    }
    values.update(overrides)
    return PrepareOptions(**values)


def test_csv_prepare_records_source_and_preserves_original(tmp_path):
    source = tmp_path / "source.csv"
    content = (
        "drive,response,scan\n"
        "0,0,up\n1,1,up\n0,0.2,down\n1,0.8,down\n"
    )
    source.write_text(content, encoding="utf-8")
    paths = prepare_curve(source, tmp_path / "local_data", _options())
    curve = load_curve(paths[0])
    assert curve.metadata.data_kind == "synthetic"
    assert curve.metadata.lower_threshold == 0.4
    assert curve.branch == ("up", "up", "down", "down")
    report = json.loads(paths[2].read_text(encoding="utf-8"))
    assert report["source_sha256"] == hashlib.sha256(source.read_bytes()).hexdigest()
    assert report["options"]["output_column"] == "response"
    assert source.read_text(encoding="utf-8") == content
    with pytest.raises(FileExistsError):
        prepare_curve(source, tmp_path / "local_data", _options())


def test_sort_requires_explicit_choice(tmp_path):
    source = tmp_path / "unsorted.csv"
    source.write_text(
        "drive,response,scan\n1,1,up\n0,0,up\n0,0.2,down\n1,0.8,down\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="row 3"):
        prepare_curve(source, tmp_path / "rejected", _options())
    assert not (tmp_path / "rejected").exists()
    csv_path, _, _ = prepare_curve(source, tmp_path / "accepted", _options(sort=True))
    assert load_curve(csv_path).input_power[:2] == (0.0, 1.0)


def test_missing_numeric_cell_has_source_row(tmp_path):
    source = tmp_path / "broken.csv"
    source.write_text("drive,response,scan\n0,,up\n", encoding="utf-8")
    with pytest.raises(ValueError, match="row 2, column response"):
        prepare_curve(source, tmp_path / "out", _options())


def test_invalid_threshold_leaves_no_partial_curve(tmp_path):
    source = tmp_path / "source.csv"
    source.write_text(
        "drive,response,scan\n0,0,up\n1,1,up\n0,0.2,down\n1,0.8,down\n",
        encoding="utf-8",
    )
    output = tmp_path / "output"
    with pytest.raises(ValueError, match="threshold"):
        prepare_curve(source, output, _options(upper_threshold=2.0))
    assert list(output.iterdir()) == []


def test_wide_xlsx_transmittance_conversion(tmp_path):
    openpyxl = pytest.importorskip("openpyxl")
    source = tmp_path / "wide.xlsx"
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "Sweep"
    sheet.append([1, 0.2, 1, 0.4])
    sheet.append([2, 0.3, 2, 0.5])
    workbook.save(source)
    options = PrepareOptions(
        name="wide",
        up_input_column="A",
        up_output_column="B",
        down_input_column="C",
        down_output_column="D",
        sheet="Sweep",
        transform="input-times-transmittance",
        input_unit="W/m",
        output_unit="W/m",
        source_description="Synthetic wide workbook",
        data_kind="synthetic",
        license="CC0-1.0",
        lower_threshold=1.25,
        upper_threshold=1.75,
    )
    csv_path, _, _ = prepare_curve(source, tmp_path / "out", options)
    curve = load_curve(csv_path)
    assert curve.output_power == pytest.approx((0.2, 0.6, 0.4, 1.0))
    assert "transmittance" in csv_path.read_text(encoding="utf-8")


def test_inspect_reports_branch_ranges_and_warnings(capsys):
    assert main(["inspect", "sample_phh"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["branch_ranges"] == {"down": [0.0, 2.0], "up": [0.0, 2.0]}
    assert report["warnings"] == []


def test_prepare_cli_roundtrip(tmp_path, capsys):
    source = tmp_path / "source.csv"
    source.write_text("drive,response\n0,0\n1,1\n", encoding="utf-8")
    output_dir = tmp_path / "converted"
    assert main(
        [
            "prepare",
            str(source),
            "--output-dir",
            str(output_dir),
            "--name",
            "smoke",
            "--input-column",
            "drive",
            "--output-column",
            "response",
            "--input-unit",
            "normalized_power",
            "--output-unit",
            "normalized_power",
            "--source-description",
            "Synthetic CLI test",
            "--data-kind",
            "synthetic",
            "--license",
            "CC0-1.0",
        ]
    ) == 0
    assert len(capsys.readouterr().out.splitlines()) == 3
    assert load_curve(output_dir / "smoke.csv").output_power == (0.0, 1.0)
