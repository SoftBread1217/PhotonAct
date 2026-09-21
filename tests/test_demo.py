"""Tests for the self-contained local curve explorer."""

import json

import pytest

from photonact.cli import main
from photonact.demo import build_demo_payload, render_demo


def test_demo_payload_includes_both_branches():
    payload = build_demo_payload("examples/curves/sample_phh.csv")
    assert payload["metadata"]["lower_threshold"] == 0.6
    assert len(payload["quantities"]["output_power"]["branches"]["up"]) == 6
    assert len(payload["quantities"]["output_power"]["branches"]["down"]) == 6
    assert "transmittance" not in payload["quantities"]


def test_demo_includes_optional_transmittance(tmp_path):
    curve = tmp_path / "device.csv"
    curve.write_text(
        "input_power,transmittance,output_power,branch\n"
        "0,0.1,0,up\n1,0.2,0.2,up\n"
        "0,0.3,0,down\n1,0.4,0.4,down\n",
        encoding="utf-8",
    )
    curve.with_suffix(".meta.json").write_text(
        json.dumps({"lower_threshold": 0.25, "upper_threshold": 0.75}),
        encoding="utf-8",
    )
    payload = build_demo_payload(curve)
    assert payload["quantities"]["transmittance"]["unit"] == "dimensionless"
    assert payload["quantities"]["transmittance"]["branches"]["down"][1] == [1.0, 0.4]


def test_demo_rejects_curve_without_hysteresis(tmp_path):
    curve = tmp_path / "single.csv"
    curve.write_text("input_power,output_power\n0,0\n1,1\n", encoding="utf-8")
    with pytest.raises(ValueError, match="up.*down"):
        build_demo_payload(curve)


def test_render_demo_escapes_script_data(tmp_path):
    curve = tmp_path / "device.csv"
    curve.write_text(
        "input_power,output_power,branch\n0,0,up\n1,1,up\n0,0,down\n1,1,down\n",
        encoding="utf-8",
    )
    curve.with_suffix(".meta.json").write_text(
        json.dumps(
            {
                "name": "</script><script>alert(1)</script>",
                "lower_threshold": 0.25,
                "upper_threshold": 0.75,
            }
        ),
        encoding="utf-8",
    )
    output = render_demo(curve, tmp_path / "demo.html")
    html = output.read_text(encoding="utf-8")
    assert "PhotonAct 本地曲线体验器" in html
    assert "</script><script>alert(1)</script>" not in html
    assert "\\u003c/script\\u003e" in html


def test_demo_cli_writes_without_opening(tmp_path, capsys):
    output = tmp_path / "demo.html"
    assert main(["demo", "sample_phh", "--output", str(output), "--no-open"]) == 0
    assert output.exists()
    assert "Wrote interactive demo" in capsys.readouterr().out
