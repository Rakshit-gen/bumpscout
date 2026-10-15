"""bumpscout: try a dependency upgrade in a scratch copy and say what breaks."""

import argparse
import json
import sys

from . import __version__, evals, scenarios
from .baseline import check as rules
from .report import markdown


def checker(model: str):
    if model == "rules":
        return rules
    raise SystemExit(f"unknown model {model!r}")


def cmd_scenarios(args) -> int:
    for name in scenarios.names():
        sc = scenarios.load(name)
        print(f"{name:<22} {sc.answer['verdict']:<14} {sc.title}")
    return 0


def cmd_check(args) -> int:
    sc = scenarios.load(args.target)
    s = sc.session()
    try:
        v = checker(args.model)(s, args.package or sc.package)
    finally:
        s.close()
    print(json.dumps(v.to_dict(), indent=2) if args.json else markdown(v, args.verbose), end="")
    return 0


def cmd_eval(args) -> int:
    scores = evals.run(checker(args.model), args.names or None)
    if args.json:
        rows = [{"name": s.name, "solved": s.solved, "harmful": s.harmful} for s in scores]
        print(json.dumps(rows, indent=2))
    else:
        print(evals.table(scores))
    return 0 if all(s.solved for s in scores) else 1


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="bumpscout", description=__doc__)
    p.add_argument("--version", action="version", version=f"bumpscout {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("scenarios", help="list the built-in upgrades").set_defaults(fn=cmd_scenarios)

    c = sub.add_parser("check", help="check one upgrade")
    c.add_argument("target", help="a scenario name")
    c.add_argument("package", nargs="?", help="the dependency to upgrade")
    c.set_defaults(fn=cmd_check)

    e = sub.add_parser("eval", help="score every scenario (exit 1 unless all are solved)")
    e.add_argument("names", nargs="*")
    e.set_defaults(fn=cmd_eval)

    for x in (c, e):
        x.add_argument("--model", default="rules", help="rules (default)")
        x.add_argument("--json", action="store_true")
    c.add_argument("-v", "--verbose", action="store_true", help="show each step")

    args = p.parse_args(argv)
    try:
        return args.fn(args)
    except ValueError as err:
        print(f"bumpscout: {err}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
