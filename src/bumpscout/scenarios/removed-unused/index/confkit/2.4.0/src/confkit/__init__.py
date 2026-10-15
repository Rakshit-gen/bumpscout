"""Config loading."""

import configparser
import json


def load_json(text):
    return json.loads(text)


def load_ini(text):
    p = configparser.ConfigParser()
    p.read_string(text)
    return {s: dict(p[s]) for s in p.sections()}
