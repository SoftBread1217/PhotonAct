"""Tests for deterministic source-data preparation."""

from types import SimpleNamespace

import pytest

from scripts.prepare_phh_1535nm import _read_branch, _transition_midpoint


class FakeSheet:
    """Minimal worksheet interface used by the conversion helpers."""

    def __init__(self, rows):
        self.rows = rows
        self.max_row = len(rows)

    def cell(self, row, column):
        return SimpleNamespace(value=self.rows[row - 1][column - 1])


def test_read_branch_sorts_points_and_skips_text_footer():
    sheet = FakeSheet([[2.0, 0.4], [1.0, 0.2], ["footer", None]])
    assert _read_branch(sheet, 1, 2) == [(1.0, 0.2), (2.0, 0.4)]


def test_read_branch_rejects_incomplete_numeric_row():
    sheet = FakeSheet([[1.0, None]])
    with pytest.raises(ValueError, match="row 1"):
        _read_branch(sheet, 1, 2)


def test_transition_threshold_uses_largest_jump_midpoint():
    threshold, interval = _transition_midpoint([(0.0, 0.0), (1.0, 0.1), (2.0, 0.9)])
    assert threshold == pytest.approx(1.5)
    assert interval == (1.0, 2.0)
