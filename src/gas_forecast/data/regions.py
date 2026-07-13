from __future__ import annotations

# State lists per EIA Weekly Natural Gas Storage Report definitions:
# https://ir.eia.gov/ngs/notes.html

_EAST_STATES = frozenset(
    {
        "Connecticut",
        "Delaware",
        "District of Columbia",
        "Florida",
        "Georgia",
        "Maine",
        "Maryland",
        "Massachusetts",
        "New Hampshire",
        "New Jersey",
        "New York",
        "North Carolina",
        "Ohio",
        "Pennsylvania",
        "Rhode Island",
        "South Carolina",
        "Vermont",
        "Virginia",
        "West Virginia",
    }
)

_MIDWEST_STATES = frozenset(
    {
        "Illinois",
        "Indiana",
        "Iowa",
        "Kentucky",
        "Michigan",
        "Minnesota",
        "Missouri",
        "Tennessee",
        "Wisconsin",
    }
)

_MOUNTAIN_STATES = frozenset(
    {
        "Arizona",
        "Colorado",
        "Idaho",
        "Montana",
        "Nebraska",
        "Nevada",
        "New Mexico",
        "North Dakota",
        "South Dakota",
        "Utah",
        "Wyoming",
    }
)

_PACIFIC_STATES = frozenset(
    {
        "California",
        "Oregon",
        "Washington",
    }
)

_SOUTH_CENTRAL_STATES = frozenset(
    {
        "Alabama",
        "Arkansas",
        "Kansas",
        "Louisiana",
        "Mississippi",
        "Oklahoma",
        "Texas",
    }
)

_LOWER48_EXCLUDED = frozenset(
    {
        "Alaska",
        "Hawaii",
        "Puerto Rico",
    }
)

_LOWER48_STATES = (
    _EAST_STATES
    | _MIDWEST_STATES
    | _MOUNTAIN_STATES
    | _PACIFIC_STATES
    | _SOUTH_CENTRAL_STATES
)

# duoarea codes from EIA weekly storage API (duoarea column).
_REGION_STATES: dict[str, frozenset[str]] = {
    "R48": _LOWER48_STATES,
    "R31": _EAST_STATES,
    "R32": _MIDWEST_STATES,
    "R33": _SOUTH_CENTRAL_STATES,
    "R34": _MOUNTAIN_STATES,
    "R35": _PACIFIC_STATES,
    # Legacy aliases
    "R01": _EAST_STATES,
    "R02": _MIDWEST_STATES,
    "R03": _MOUNTAIN_STATES,
    "R04": _PACIFIC_STATES,
    "R05": _SOUTH_CENTRAL_STATES,
}

_REGION_SLUGS: dict[str, str] = {
    "R48": "lower48",
    "R31": "east",
    "R32": "midwest",
    "R33": "south_central",
    "R34": "mountain",
    "R35": "pacific",
    # Legacy aliases
    "R01": "east",
    "R02": "midwest",
    "R03": "mountain",
    "R04": "pacific",
    "R05": "south_central",
}

_CANONICAL_REGION_CODES = ("R48", "R31", "R32", "R33", "R34", "R35")

_REGION_LABELS: dict[str, str] = {
    "R48": "Lower 48 States",
    "R31": "East",
    "R32": "Midwest",
    "R33": "South Central",
    "R34": "Mountain",
    "R35": "Pacific",
    "R01": "East",
    "R02": "Midwest",
    "R03": "Mountain",
    "R04": "Pacific",
    "R05": "South Central",
}


def supported_storage_regions(*, include_legacy: bool = False) -> list[str]:
    """Return canonical EIA storage regions, optionally including legacy aliases."""
    if include_legacy:
        return list(_REGION_STATES.keys())
    return list(_CANONICAL_REGION_CODES)


def region_states(duoarea: str) -> frozenset[str]:
    """Return state names for an EIA storage region."""
    try:
        return _REGION_STATES[duoarea]
    except KeyError as exc:
        supported = ", ".join(sorted(_REGION_STATES))
        raise ValueError(
            f"Unknown duoarea {duoarea!r}. Supported: {supported}"
        ) from exc


def region_slug(duoarea: str) -> str:
    """Return a filesystem-safe slug for an EIA storage region."""
    try:
        return _REGION_SLUGS[duoarea]
    except KeyError as exc:
        supported = ", ".join(sorted(_REGION_SLUGS))
        raise ValueError(
            f"Unknown duoarea {duoarea!r}. Supported: {supported}"
        ) from exc


def region_label(duoarea: str) -> str:
    """Return the human-readable label for an EIA storage region."""
    try:
        return _REGION_LABELS[duoarea]
    except KeyError as exc:
        supported = ", ".join(sorted(_REGION_LABELS))
        raise ValueError(
            f"Unknown duoarea {duoarea!r}. Supported: {supported}"
        ) from exc


def lower48_excluded_states() -> frozenset[str]:
    """Return census areas excluded from Lower 48 storage geography."""
    return _LOWER48_EXCLUDED
