"""URL routing."""

from shapes import Point


def route(path):
    parts = [p for p in path.split("/") if p]
    return Point(len(parts), len(path))
