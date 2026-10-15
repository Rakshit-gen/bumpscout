"""The live index: versions from PyPI's JSON API. Only reads; no account needed."""

import json
import urllib.error
import urllib.request
from collections.abc import Callable

from packaging.utils import canonicalize_name
from packaging.version import InvalidVersion, Version

from .index import Release, by_version

PYPI = "https://pypi.org/pypi/{name}/json"


def fetch_json(url: str, headers: dict | None = None, timeout: float = 20) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "bumpscout", **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise ValueError(f"{url} returned {e.code}") from None
    except urllib.error.URLError as e:
        raise ValueError(f"can't reach {url}: {e.reason}") from None


class PyPIIndex:
    def __init__(self, fetch: Callable[[str], dict] = fetch_json):
        self.fetch = fetch
        self._cache: dict[str, dict] = {}

    def project(self, name: str) -> dict:
        key = canonicalize_name(name)
        if key not in self._cache:
            self._cache[key] = self.fetch(PYPI.format(name=key))
        return self._cache[key]

    def releases(self, name: str) -> list[Release]:
        out = []
        for version, files in self.project(name).get("releases", {}).items():
            try:
                if not files or Version(version).is_prerelease:
                    continue
            except InvalidVersion:
                continue
            out.append(
                Release(
                    version,
                    files[0].get("requires_python") or "",
                    yanked=all(f.get("yanked") for f in files),
                )
            )
        return by_version(out)
