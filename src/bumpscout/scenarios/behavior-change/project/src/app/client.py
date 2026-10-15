from retryer import retry


def fetch(call):
    """Fetch through a flaky connection."""
    return retry(call)
