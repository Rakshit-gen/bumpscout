from jsonfast import dumps


def cache_key(params):
    return dumps(params)
