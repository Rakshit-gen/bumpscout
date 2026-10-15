from confkit import load_json

DEFAULTS = {"debug": False, "workers": 2}


def settings(text):
    return {**DEFAULTS, **load_json(text)}
