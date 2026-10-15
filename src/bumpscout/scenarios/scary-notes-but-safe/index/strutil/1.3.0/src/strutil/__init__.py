"""String helpers."""

import re


def title_case(s):
    return " ".join(w.capitalize() for w in s.split())


def slugify(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
