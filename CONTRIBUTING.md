# Contributing to Simkl CSV Converters

Thanks for considering a contribution — community fixes like the folder and
username pickers from [Crazy-Lunatic](https://github.com/Crazy-Lunatic) are
exactly the kind of thing that make these tools more useful for everyone.

## Ground rules

* **Zero runtime dependencies.** The converters must keep working with a
  stock Python 3.8+ install and only the standard library
  (`sqlite3`, `csv`, `json`, `argparse`, `tkinter`, etc.). Dev-only tools
  (tests, linting) may use packages from `requirements-dev.txt`.
* **Don't break non-interactive use.** Both scripts must keep working
  unattended (cron, CI, `python3 script.py --flag value`) with no prompts.
  Interactive pickers/prompts should only trigger when `sys.stdin.isatty()`
  is `True` and no explicit argument was given — see `resolve_db_path()` and
  `resolve_input_folder()` for the existing pattern.
* **Errors vs. empty results are not the same thing.** A successful run that
  matches zero records should exit `0`. A real failure (bad DB, bad path,
  bad data) should exit non-zero and print to `stderr`.

## Getting set up

```bash
git clone https://github.com/jshields-ca/simkl-csv-converters.git
cd simkl-csv-converters
pip install -r requirements-dev.txt
```

## Running tests and lint locally

```bash
pytest -v
flake8 convert_tautulli_to_simkl.py convert_trakt_to_simkl.py tests/
```

Both run automatically in CI (`.github/workflows/ci.yml`) on every pull
request, across Python 3.9–3.12.

## Making a change

1. Fork the repo and create a branch off `main`.
2. Add or update tests in `tests/` for any behavior change — new CLI flags,
   new branches in the picker/fallback logic, new error paths, etc.
3. Update `README.md` if you change CLI flags, defaults, or output.
4. Add an entry under `[Unreleased]` in `CHANGELOG.md` describing the change
   and crediting yourself (see [Versioning](#versioning--changelog) below).
5. Open a pull request against `main`. Fill in the PR template — it's short.

## Versioning & Changelog

This project follows [Semantic Versioning](https://semver.org/)
(`MAJOR.MINOR.PATCH`) and keeps a [Keep a Changelog](https://keepachangelog.com/)
formatted `CHANGELOG.md`:

* **MAJOR** — a change that breaks existing non-interactive usage or CLI
  flags (e.g. removing a flag, changing what a bare invocation does).
* **MINOR** — a backward-compatible feature (e.g. a new flag, a new picker,
  a new script).
* **PATCH** — a backward-compatible bug fix.

Releases are tagged on GitHub as `vMAJOR.MINOR.PATCH` with the matching
`CHANGELOG.md` section as the release notes. Every changelog entry names the
contributor, so please add yours (GitHub handle + link) when you open a PR —
credit doesn't get dropped just because a maintainer merges or rebases your
change.

## Code style

Plain PEP 8, enforced by `flake8` (see `setup.cfg` for the couple of
project-specific tweaks). No formatter is enforced; just keep it readable
and consistent with the surrounding code.
