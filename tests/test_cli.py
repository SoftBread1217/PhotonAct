"""Command-line smoke tests."""

from photonact.cli import main


def test_inspect_bundled_curve(capsys):
    assert main(["inspect", "sample_phh"]) == 0
    assert '"name": "sample_phh"' in capsys.readouterr().out
