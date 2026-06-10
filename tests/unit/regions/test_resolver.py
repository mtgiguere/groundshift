import pytest

from groundshift.models.bounding_box import BoundingBox
from groundshift.regions.resolver import UnknownRegionError, resolve_region


def test_resolve_ethiopia_returns_bounding_box():
    result = resolve_region("ethiopia")
    assert isinstance(result, BoundingBox)


def test_resolve_unknown_region_raises_unknown_region_error():
    with pytest.raises(UnknownRegionError, match="unknown_place"):
        resolve_region("unknown_place")


def test_resolve_colombia_returns_bounding_box():
    result = resolve_region("colombia")
    assert isinstance(result, BoundingBox)


def test_resolve_central_america_returns_bounding_box():
    result = resolve_region("central_america")
    assert isinstance(result, BoundingBox)
