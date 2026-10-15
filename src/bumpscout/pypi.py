"""The live index: versions from PyPI's JSON API, release notes from the
project's GitHub releases when it links a GitHub repo. Only reads; set
GITHUB_TOKEN to raise GitHub's limit of 60 requests an hour."""

import json
import os
import re
import urllib.error
import urllib.request
from collections.abc import Callable

from packaging.utils import canonicalize_name
from packaging.version import InvalidVersion, Version

from .index import Release, by_version

PYPI = "https://pypi.org/pypi/{name}/json"
GH_RELEASES = "https://api.github.com/repos/{repo}/releases?per_page=100"
GH_REPO = re.compile(r"github\.com/([\w.-]+/[\w.-]+?)(?:\.git)?(?:[/#?]|$)")


def github_repo(info: dict) -> str:
    """owner/name of the GitHub repo a PyPI project links to, or ''."""
    urls = list((info.get("project_urls") or {}).values()) + [info.get("home_page") or ""]
    for url in urls:
        if m := GH_REPO.search(url or ""):
            return m.group(1)
    return ""


def tag_version(tag: str) -> str:
    """'v1.2.0', 'tablet-1.2.0' or 'tablet==1.2.0' -> '1.2.0'."""
    m = re.search(r"(\d+(?:\.\d+)*)$", tag)
    return m.group(1) if m else tag


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
    def __init__(self, fetch: Callable[..., dict] = fetch_json):
        self.fetch = fetch
        self._cache: dict[str, dict] = {}
        self._notes: dict[str, dict[str, str]] = {}

    def project(self, name: str) -> dict:
        key = canonicalize_name(name)
        if key not in self._cache:
            self._cache[key] = self.fetch(PYPI.format(name=key), {})
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
        notes = self.notes(name)
        for r in out:
            r.notes = notes.get(r.version, "")
            if not r.notes and "" in notes:
                r.notes = notes[""]  # why there are none
        return by_version(out)

    def notes(self, name: str) -> dict[str, str]:
        """version -> release notes from GitHub; {"": reason} when there are none."""
        key = canonicalize_name(name)
        if key not in self._notes:
            self._notes[key] = self._github_notes(name)
        return self._notes[key]

    def _github_notes(self, name: str) -> dict[str, str]:
        repo = github_repo(self.project(name).get("info", {}))
        if not repo:
            return {"": "(no release notes: the package doesn't link a GitHub repo)"}
        token = os.environ.get("GITHUB_TOKEN", "")
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        try:
            rels = self.fetch(GH_RELEASES.format(repo=repo), headers)
        except ValueError as e:
            return {"": f"(no release notes: {e})"}
        out = {}
        for r in rels:
            v = tag_version(r.get("tag_name") or "")
            out.setdefault(v, (r.get("body") or "").strip())
        out.setdefault("", f"(no GitHub release for this version in {repo})")
        return out
