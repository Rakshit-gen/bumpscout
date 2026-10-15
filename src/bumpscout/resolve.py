"""Pick a version of every package a set of requirements needs.

Newest release that fits every constraint seen so far and the Python version,
repeated until nothing changes. No deep backtracking: when nothing fits, the
error names the constraints that clash, which is what a person needs to know.
"""

from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet
from packaging.utils import canonicalize_name
from packaging.version import Version

from .index import Index, Release


class ResolutionError(ValueError):
    pass


def resolve(requirements: list[str], index: Index, python: str) -> dict[str, str]:
    py = Version(python)
    wanted: dict[str, list[tuple[str, SpecifierSet]]] = {}  # name -> [(who, spec)]
    for text in requirements:
        req = Requirement(text)
        if req.marker and not req.marker.evaluate({"python_version": python}):
            continue
        wanted.setdefault(canonicalize_name(req.name), []).append(("the project", req.specifier))
    chosen: dict[str, Release] = {}
    for _ in range(50):
        changed = False
        for name, specs in list(wanted.items()):
            if name in chosen and all(
                s.contains(chosen[name].version, prereleases=True) for _, s in specs
            ):
                continue
            fits = [
                r
                for r in index.releases(name)
                if not r.yanked
                and all(s.contains(r.version) for _, s in specs)
                and (not r.requires_python or SpecifierSet(r.requires_python).contains(py))
            ]
            if not fits:
                needs = "; ".join(f"{who} needs {name}{s or ' (any)'}" for who, s in specs)
                raise ResolutionError(f"no {name} release fits Python {python}: {needs}")
            chosen[name] = fits[-1]
            changed = True
            # Requirements of the chosen release, replacing any from an older pick.
            for deps in wanted.values():
                deps[:] = [(who, s) for who, s in deps if not who.startswith(f"{name} ")]
            for text in chosen[name].requires:
                req = Requirement(text)
                wanted.setdefault(canonicalize_name(req.name), []).append(
                    (f"{name} {chosen[name].version}", req.specifier)
                )
        if not changed:
            return {n: r.version for n, r in chosen.items() if n in wanted}
    raise ResolutionError("gave up resolving after 50 rounds")
