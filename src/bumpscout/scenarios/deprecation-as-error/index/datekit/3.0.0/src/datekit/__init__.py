"""Date parsing."""

from datetime import datetime


def parse(s, fmt="%Y-%m-%d"):
    return datetime.strptime(s, fmt).date()
