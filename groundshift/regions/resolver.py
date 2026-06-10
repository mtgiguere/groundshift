from groundshift.models.bounding_box import BoundingBox


class UnknownRegionError(KeyError):
    pass


# Named regions covering established crop geographies.
# Bounding boxes are intentionally generous — they capture the full country
# or agricultural zone rather than a tight administrative boundary, so the
# pipeline can detect emerging suitability at the periphery.
_REGISTRY: dict[str, BoundingBox] = {
    "ethiopia": BoundingBox(min_lon=33.0, min_lat=3.0, max_lon=48.0, max_lat=15.0),
    "colombia": BoundingBox(min_lon=-79.0, min_lat=-4.0, max_lon=-67.0, max_lat=13.0),
    "central_america": BoundingBox(min_lon=-92.0, min_lat=7.0, max_lon=-77.0, max_lat=18.0),
}


def resolve_region(region_id: str) -> BoundingBox:
    """Return the BoundingBox for a named region.

    Raises UnknownRegionError if the id is not in the registry.
    """
    if region_id not in _REGISTRY:
        raise UnknownRegionError(region_id)
    return _REGISTRY[region_id]
