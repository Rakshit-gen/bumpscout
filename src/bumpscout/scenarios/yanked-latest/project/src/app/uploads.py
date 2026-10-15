from pathkit import ext

ALLOWED = {"png", "jpg", "pdf"}


def allowed(name):
    return ext(name) in ALLOWED
