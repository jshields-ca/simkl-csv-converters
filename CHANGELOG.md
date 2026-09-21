# Changelog

All notable changes to this project are documented here. The format is based
on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
follows [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [1.1.0] - 2026-09-21

### Added
- **Folder pickers** for both scripts (Tkinter GUI, with a text-prompt
  fallback when Tkinter isn't available), so the DB / export folder no
  longer has to live next to the script.
- **Tautulli username picker** (`convert_tautulli_to_simkl.py`): lists every
  user with watch history in the database and lets you pick by number or
  type a username, case-insensitively.
- `--all-users` flag to explicitly export every Tautulli user.
- `--output` / `-o` on `convert_trakt_to_simkl.py`, for consistency with the
  Tautulli script.
- CLI folder argument on `convert_trakt_to_simkl.py` (`python3
  convert_trakt_to_simkl.py /path/to/export/folder`).
- Read-only SQLite connection handling shared by all Tautulli DB access
  paths, with clearer error messages.
- Output-directory auto-creation for both scripts.
- pytest suite (`tests/`) covering the picker/fallback logic, case-insensitive
  username matching, empty vs. erroring exports, and multi-file Trakt
  conversion.
- GitHub Actions CI (`.github/workflows/ci.yml`) running `flake8` and
  `pytest` on Python 3.9–3.12 for every push/PR.
- `CONTRIBUTING.md`, this `CHANGELOG.md`, issue/PR templates, and a
  `.gitignore`.

  All of the above interactive features were originally contributed by
  **[Crazy-Lunatic](https://github.com/Crazy-Lunatic)** in
  [#1](https://github.com/jshields-ca/simkl-csv-converters/pull/1). This
  release incorporates that work with the fixes below applied, plus the
  surrounding tests/CI/docs.

### Changed
- **Non-interactive runs never prompt.** Pickers and the username prompt
  only appear when a script is run at an interactive terminal
  (`sys.stdin.isatty()`) *and* the relevant argument was omitted. Cron jobs,
  CI, and any command that already worked (`--db ... --user ...`, or no
  flags at all) keep behaving exactly as before: `convert_tautulli_to_simkl.py`
  still auto-detects the DB and exports **all users** by default, and
  `convert_trakt_to_simkl.py` still reads `watched-history-*.json` from the
  current directory by default.

### Fixed
- A Tautulli export that matches **zero records** now exits `0` (success)
  instead of `1`. Previously a valid, empty result and an actual database
  error were indistinguishable to callers — both returned exit code `1`.
- `convert_trakt_to_simkl.py`'s Tkinter root window is now always destroyed
  via `finally`, matching the Tautulli script, so a `TclError` during the
  folder dialog can no longer leak the window.
- Error messages in `convert_trakt_to_simkl.py` are now written to `stderr`
  consistently with the Tautulli script, instead of a mix of `stdout`/`stderr`.

## [1.0.0] - 2026-09-21

Initial tagged release, covering the project as it stood before
[#1](https://github.com/jshields-ca/simkl-csv-converters/pull/1):

### Added
- `convert_trakt_to_simkl.py`: converts Trakt.tv `watched-history-*.json`
  exports into a Simkl-compatible import CSV.
- `convert_tautulli_to_simkl.py`: exports Tautulli watch history
  (optionally filtered by user and/or date) into a Simkl-compatible CSV,
  reading `tautulli.db` in read-only URI mode.
- Hardcoded `ID_MAP` for ambiguous/new show titles that Simkl's importer
  otherwise mismatches.
- MIT License.

Authored by [jshields-ca](https://github.com/jshields-ca), with drafting
assistance from Google Gemini Pro.

[Unreleased]: https://github.com/jshields-ca/simkl-csv-converters/compare/v1.1.0...HEAD
[1.1.0]: https://github.com/jshields-ca/simkl-csv-converters/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/jshields-ca/simkl-csv-converters/releases/tag/v1.0.0
