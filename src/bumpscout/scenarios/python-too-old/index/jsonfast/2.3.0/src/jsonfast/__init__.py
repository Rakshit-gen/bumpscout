"""JSON with sorted keys."""

import json


def dumps(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))
