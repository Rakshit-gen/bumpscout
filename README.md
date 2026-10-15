# bumpscout

An agent that checks whether your Python project can take a dependency
upgrade. It works in a scratch copy: it reads the release notes, tries the new
version, runs your tests, searches the code for what changed and edits it until
the tests pass. You get a verdict (safe, needs changes, or blocked), the patch,
and the requirement to write. Your project is never touched.

The model is Groq (`openai/gpt-oss-120b` by default), called through the
standard library. The only dependency is `packaging`. Without a key it runs a
rules-only check, so everything also works offline.

## Quickstart

```
uv tool install git+https://github.com/Rakshit-gen/bumpscout
bumpscout scenarios                            # built-in upgrades with known answers
bumpscout check renamed-function               # rules only without GROQ_API_KEY
GROQ_API_KEY=... bumpscout check untested-call-site -v
bumpscout check path/to/project httpx          # a real project, against PyPI, with uv
bumpscout eval                                 # score every scenario
```

## On a real project

A small project pinned to `packaging==21.3` that imports `LegacyVersion`,
which packaging 22 dropped. The rules-only run:

```
$ bumpscout check vercheck packaging --model rules
running vercheck's tests with uv...
# packaging 21.3 to 26.3: upgrade needs code changes

the tests fail on 26.3; the notes change format_full_version, _format_full_version,
_cmpkey, Specifier.prereleases, _Version, NamedTuple, ruff, Py_NOGIL, [...]
LegacySpecifier, LegacyVersion, namedtuple, packaging.metadata

Requirement: `packaging==26.3`

## Files to change

- src/vercheck/__init__.py

## Evidence

- `tests/test_vercheck.py: ImportError: cannot import name 'LegacyVersion' from 'packaging.version' [...]`
- `src/vercheck/__init__.py:1: from packaging.version import LegacyVersion, Version, parse`
- `src/vercheck/__init__.py:10: return isinstance(parse(v), LegacyVersion)`
```

Versions come from PyPI, release notes from the package's GitHub releases,
and the tests run with pytest in a uv virtualenv next to the copy. That run
took 3.2 s the first time and 1.4 s with uv's cache warm. The name list
shows the limit of the rules: they take every name the notes say was
removed or dropped, and only the search narrows it down.

## What the agent does that the rules can't

`examples/scripted_run.py` runs the real agent loop, tools, tests and checks
with a model whose replies are fixed, so it needs no key. In the
`untested-call-site` scenario the tests pass on the new version, so the
rules call it safe. The scripted agent reads the notes, finds the call, fixes
it and shows the fix passes:

```
# notifykit 1.2.0 to 2.0.0: upgrade needs code changes

send_mail is renamed to send_email in 2.0. The tests pass anyway because
nothing calls page(), which still uses the old name.

Requirement: `notifykit<3,>=2.0.0`

## Files to change

- src/app/alerts.py

## Patch

--- a/src/app/alerts.py
+++ b/src/app/alerts.py
@@ -9,4 +9,4 @@
 
 def page(text):
     """Only runs in production when something is on fire."""
-    notifykit.send_mail(ONCALL, subject("critical", text))
+    notifykit.send_email(ONCALL, subject("critical", text))

[evidence left out]

## Notes

- evidence not found in any tool answer: 'page() is called from the alerting cron job'

[the 7 steps left out]
```

The scripted conclusion claims something no tool showed, and the checks drop
it.

## Guard rails

- **Scratch copy only.** The agent edits a temp copy. `--write-patch FILE`
  saves the code changes for `git apply`; applying them is up to you.
- **No editing tests or pins.** `edit_file` refuses test files and
  dependency files. Versions change only through `try_upgrade`.
- **Tests rerun at the end.** The checks run the tests again at the claimed
  version, with the copy as the agent left it. Safe with code edits becomes
  needs-changes. Safe with failing tests becomes needs-changes with no patch.
  A version that can't be installed is blocked, whatever the model said, and
  a fallback has to pass.
- **Evidence.** Quoted lines have to appear in a tool answer, or they're
  dropped.
- **Budget.** 15 tool calls by default (`--budget`), with answers capped at
  1500 characters.

## How the rules do

`bumpscout eval --model rules`, on the ten built-in scenarios:

```
scenario              verdict  version  files  fix  harmful
behavior-change       yes      yes      -      -    -
deprecation-as-error  yes      yes      yes    -    -
minor-safe            yes      yes      yes    yes  -
python-too-old        yes      yes      yes    yes  -
removed-unused        yes      yes      yes    yes  -
renamed-function      yes      yes      yes    -    -
scary-notes-but-safe  yes      yes      yes    yes  -
transitive-conflict   yes      yes      yes    yes  -
untested-call-site    -        yes      -      -    YES
yanked-latest         yes      yes      yes    yes  -
solved 6/10, harmful 1
```

A needs-changes answer only counts as solved with a patch to the right
files, and the rules never write one. That's three of the four misses. The
fourth is the harmful one: in **untested-call-site** a renamed function sits
on a path no test runs, the tests pass, and the rules call it safe.

The scenarios the rules do get also test the agent, since its first reading
is often wrong:

- **scary-notes-but-safe**: the notes remove `slugify`, and the project has a
  `slugify`, but it's the project's own function.
- **behavior-change**: nothing is renamed. A default changed, and the fix is
  to pass the old value explicitly.
- **deprecation-as-error**: a minor release adds a deprecation warning, and
  the project's tests turn warnings into errors.
- **transitive-conflict**: the new version needs another package at a
  version the project pins below.
- **yanked-latest**: the newest release was yanked.

Model results aren't in this README yet. The numbers here only come from runs
that need no API key. `bumpscout eval --model groq` scores the model, with
one investigation per scenario.

## Options

```
bumpscout check TARGET [PACKAGE] [--model rules|groq|groq:<id>] [--budget N] [-v] [--json] [--write-patch FILE]
bumpscout eval [NAME...]         [--model ...] [--budget N] [-v] [--json]
bumpscout scenarios
```

`TARGET` is a scenario name or a project folder. For a folder, `PACKAGE` is
required and uv has to be installed. `--model` defaults to groq when
`GROQ_API_KEY` is set. `eval` exits 1 unless every scenario is solved. Set
`GITHUB_TOKEN` to raise GitHub's limit of 60 unauthenticated requests an
hour. More detail: [docs/how-it-works.md](docs/how-it-works.md).

## Measured vs Claimed

| Claim | Value | How measured | Date |
|---|---|---|---|
| Rules baseline | 6 of 10 solved, 1 harmful | `bumpscout eval --model rules` | 2026-10-15 |
| Rules speed | 0.57 s for all 10 scenarios, tests included | in-process, best of 3, Apple M4, Python 3.13 | 2026-10-15 |
| Live check | 3.2 s first run, 1.4 s with uv's cache warm | `check vercheck packaging --model rules`, Apple M4 | 2026-10-15 |
| Tests | 93, no API calls | `uv run pytest` | 2026-10-15 |

## Status

Works: everything above. The agent has only run with a scripted model here;
there are no live model results yet.

Not done: lock files (`uv.lock`, `poetry.lock`) aren't updated or read, only
the requirement is. Release notes only come from GitHub releases, not
CHANGELOG files. One package at a time. Real projects run their tests with
pytest only.
