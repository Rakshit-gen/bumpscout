"""Date parsing."""

import warnings
from datetime import datetime

_UNSET = object()


def parse(s, fmt=_UNSET):
    if fmt is _UNSET:
        warnings.warn(
            "parse() without fmt is deprecated; pass fmt explicitly",
            DeprecationWarning,
            stacklevel=2,
        )
        fmt = "%Y-%m-%d"
    return datetime.strptime(s, fmt).date()
