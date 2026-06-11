import numpy as np
import xarray as xr

from groundshift.models.trend_result import TrendResult


def _slope() -> xr.DataArray:
    return xr.DataArray(np.array([[-0.002, 0.001], [0.003, -0.001]]))


class TestTrendResult:
    def test_has_slope_field(self):
        s = _slope()
        result = TrendResult(slope=s)
        assert result.slope is s

    def test_slope_is_dataarray(self):
        result = TrendResult(slope=_slope())
        assert isinstance(result.slope, xr.DataArray)

    def test_negative_slope_indicates_decline(self):
        slope = xr.DataArray(np.array([[-0.005]]))
        result = TrendResult(slope=slope)
        assert float(result.slope.values[0, 0]) < 0

    def test_positive_slope_indicates_improvement(self):
        slope = xr.DataArray(np.array([[0.003]]))
        result = TrendResult(slope=slope)
        assert float(result.slope.values[0, 0]) > 0
