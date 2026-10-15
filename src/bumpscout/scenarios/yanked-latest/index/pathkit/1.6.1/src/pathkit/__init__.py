"""Path helpers."""


def ext(name):
    return name.rsplit("\\", 1)[-1].lower() if "\\" in name else ""
