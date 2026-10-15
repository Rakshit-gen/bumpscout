"""bumpscout: try a dependency upgrade in a scratch copy and say what breaks."""

import argparse
import json
import os
import sys

from . import __version__, evals, scenarios
from .baseline import check as rules
from .report import markdown


def checker(spec: str | None, budget: int = 15, verbose: bool = False):
    """A function (session, package) -> Verdict: the rules, or the agent on a model."""
    if spec is None:
        spec = "groq" if os.environ.get("GROQ_API_KEY") else "rules"
    if spec == "rules":
        return rules
    if spec != "groq" and not spec.startswith("groq:"):
        raise ValueError(f"unknown model {spec!r}; use rules, groq or groq:<model id>")
    from .agent import investigate
    from .llm import DEFAULT_MODEL, ChatAPI

    model = ChatAPI(spec.partition(":")[2] or DEFAULT_MODEL)

    def show(name, args):
        shown = ", ".join(f"{k}={v!r}" for k, v in args.items())
        print(f"  {name}({shown})", file=sys.stderr, flush=True)

    def run(session, package):
        return investigate(session, package, model, budget, show if verbose else None)

    return run


def cmd_scenarios(args) -> int:
    for name in scenarios.names():
        sc = scenarios.load(name)
        print(f"{name:<22} {sc.answer['verdict']:<14} {sc.title}")
    return 0


def cmd_check(args) -> int:
    sc = scenarios.load(args.target)
    s = sc.session()
    try:
        v = checker(args.model, args.budget, args.verbose)(s, args.package or sc.package)
    finally:
        s.close()
    print(json.dumps(v.to_dict(), indent=2) if args.json else markdown(v, args.verbose), end="")
    if args.write_patch:
        if not v.patch:
            print("bumpscout: no patch to write", file=sys.stderr)
            return 1
        with open(args.write_patch, "w") as f:
            f.write(v.patch)
        print(f"wrote the code changes to {args.write_patch}", file=sys.stderr)
    return 0


def cmd_eval(args) -> int:
    scores = evals.run(checker(args.model, args.budget, args.verbose), args.names or None)
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
    c.add_argument(
        "--write-patch", metavar="FILE", help="save the code changes (apply with git apply)"
    )
    c.set_defaults(fn=cmd_check)

    e = sub.add_parser("eval", help="score every scenario (exit 1 unless all are solved)")
    e.add_argument("names", nargs="*")
    e.set_defaults(fn=cmd_eval)

    for x in (c, e):
        x.add_argument(
            "--model",
            help="rules, groq, or groq:<model id> (default: groq if GROQ_API_KEY is set, "
            "else rules)",
        )
        x.add_argument("--budget", type=int, default=15, help="tool calls the agent may make")
        x.add_argument("--json", action="store_true")
        x.add_argument("-v", "--verbose", action="store_true", help="show each step")

    args = p.parse_args(argv)
    try:
        return args.fn(args)
    except ValueError as err:
        print(f"bumpscout: {err}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
