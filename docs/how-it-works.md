# How bumpscout works

## The scratch copy

Everything happens in a copy of the project in a temp folder (`sandbox.py`).
`.git`, `.venv`, caches and build output are left out. The project itself is
never written to; `--write-patch` saves the code changes to a file for you to
apply with `git apply`.

## Pins

`pins.py` reads direct dependencies from `[project] dependencies` in
`pyproject.toml` and from `requirements*.txt`. To try a version, `edit.py`
rewrites that one requirement in the copy to `==VERSION`, keeping extras and
markers. The requirement bumpscout suggests keeps the old style: an exact pin
stays exact, a range moves its lower bound and, if needed, its cap to the next
major. A `~=` pin becomes a cap at the next major.

## Two environments

- **Scenarios** use a fixture index: a folder per package and version with
  `meta.json` (Python requirement, dependencies, yanked), `notes.md` and the
  package source. `resolve.py` picks versions (newest that fits every
  constraint, no deep backtracking; when nothing fits, the error names who
  needs what). The sources are copied onto `PYTHONPATH` and the tests run
  with `python -m unittest`. Nothing is downloaded, and a scenario runs in
  tens of milliseconds.
- **Real projects** use PyPI's JSON API for versions (`pypi.py`) and uv for
  installs (`UvEnv` in `env.py`): a virtualenv next to the copy, `uv pip
  install` of the pins, the `dev` dependency group, any `test`, `tests` or
  `dev` extras and pytest, then `python -m pytest`. When uv reports "No
  solution found" the version counts as blocked; any other install failure
  stops the run with uv's error.

Release notes for real packages come from the GitHub releases of the repo the
package links on PyPI. Many packages keep their changelog elsewhere; then the
notes say why there are none.

## The rules

`baseline.py`, with no model:

1. Take the newest release that isn't yanked.
2. Try it. If it can't be installed, it's blocked; try older ones, newest
   first, and name the first that installs and passes as the fallback.
3. If the tests pass, it's safe.
4. If not, it needs changes. Pull names from the notes on lines that say
   removed, renamed, deprecated, dropped and so on (in backticks, or bare
   CamelCase and snake_case), and list the non-test files that use them.

The rules never write a fix, and they trust passing tests.

## The agent

`agent.py` gives a model (Groq, `openai/gpt-oss-120b` by default) these tools
over the copy:

| Tool | What it returns |
|---|---|
| `project_info` | Python version, dependencies, installed version, tests today |
| `versions` | newer releases, with Python needs, dependencies and yanked flags |
| `release_notes` | notes from the installed version up to a given one |
| `search_code` | lines that use a name, tests included |
| `read_file` | numbered lines of a file in the copy |
| `try_upgrade` | pin a version, install, run the tests |
| `edit_file` | replace one exact string in a project file |
| `show_patch` | the code edits so far |

`edit_file` refuses tests (the fix has to make the code pass them, not the
other way round) and dependency files (versions go through `try_upgrade`).
Answers are capped at 1500 characters. Asking again for something that can't
have changed (project info, versions, notes) isn't run again; `try_upgrade`
and `search_code` are, since edits change their answers. After the budget
(15 calls by default) no tools are offered and the model has to conclude.

## The checks

`checks.py` runs the tests once more at the claimed version, with the copy as
the agent left it, and fixes the verdict to match:

- Evidence lines that no tool returned are dropped, with a note.
- A version that can't be installed is blocked whatever the model said. A
  blocked fallback has to install and pass, or it's dropped.
- Safe with code edits in the copy becomes needs-changes. Safe with failing
  tests becomes needs-changes with no patch.
- The patch is the copy's code diff, and the files are the ones it touches.
  Needs-changes with passing tests and no patch gets a note.

## Scoring

Each scenario has an answer: verdict, version, files and, when blocked, the
fallback. A result is solved when all of them match and, for needs-changes,
it comes with a patch to those files. Harmful means calling an upgrade safe
when it isn't.
