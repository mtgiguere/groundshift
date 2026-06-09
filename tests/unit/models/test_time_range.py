import pytest
from datetime import datetime

from groundshift.models.time_range import TimeRange


def test_time_range_stores_start_and_end():
    start = datetime(2020, 1, 1)
    end = datetime(2023, 12, 31)
    tr = TimeRange(start=start, end=end)
    assert tr.start == start
    assert tr.end == end


def test_time_range_defaults_scenario_to_none():
    tr = TimeRange(start=datetime(2020, 1, 1), end=datetime(2023, 12, 31))
    assert tr.scenario is None


def test_time_range_defaults_horizon_year_to_none():
    tr = TimeRange(start=datetime(2020, 1, 1), end=datetime(2023, 12, 31))
    assert tr.horizon_year is None


def test_time_range_raises_if_end_before_start():
    with pytest.raises(ValueError, match="end"):
        TimeRange(start=datetime(2023, 1, 1), end=datetime(2020, 1, 1))
