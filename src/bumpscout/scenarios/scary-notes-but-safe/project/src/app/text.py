import re

from strutil import title_case


def slugify(s):
    """Our own: keeps underscores, unlike most."""
    return re.sub(r"[^a-z0-9_]+", "-", s.lower()).strip("-")


def heading(s):
    return title_case(s), slugify(s)
