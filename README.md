# Simkl CSV Converters

[![CI](https://github.com/jshields-ca/simkl-csv-converters/actions/workflows/ci.yml/badge.svg)](https://github.com/jshields-ca/simkl-csv-converters/actions/workflows/ci.yml)
[![Latest release](https://img.shields.io/github/v/release/jshields-ca/simkl-csv-converters)](https://github.com/jshields-ca/simkl-csv-converters/releases)

A lightweight, zero-dependency suite of Python tools designed to convert watch history from **Trakt.tv exports** and local **Tautulli databases** into strictly formatted CSV files ready for direct import into [Simkl](https://simkl.com).

With Trakt's recent move to restrict API access for free users, directly syncing data via API (using tools like `plextraktsync`) has become complicated or entirely broken for many. These offline utilities provide a completely free workaround to ensure your watch history remains 100% portable and private without recurring SaaS costs.

## Included Tools

| Script | Source Data | Description |
| :--- | :--- | :--- |
| **`convert_trakt_to_simkl.py`** | Trakt `.zip` Export (`watched-history-*.json`) | Extracts and formats movie and television watch history from official Trakt JSON archives. |
| **`convert_tautulli_to_simkl.py`** | Tautulli SQLite Database (`tautulli.db`) | Queries local Plex stream logs directly from Tautulli with support for user and date filtering. |

## Features
* **Zero Runtime Dependencies:** Uses only the Python standard library (`sqlite3`, `json`, `csv`, `argparse`, `tkinter`). No `pip install` required to *run* the scripts — see [Contributing](CONTRIBUTING.md) if you want to run the test suite.
* **Interactive Folder & User Pickers:** Run either script with no arguments at a terminal and a native folder picker (or a text prompt, if Tkinter isn't available) opens. The Tautulli script also lets you list and pick a username interactively.
* **Automation-Safe by Default:** Pickers and prompts only ever appear at an interactive terminal. Cron jobs, CI, and scripted invocations (with or without flags) never block — they fall back to the classic non-interactive defaults (auto-detected DB, current directory, all users).
* **Safe Database Access:** The Tautulli script queries the local `tautulli.db` using read-only URI mode (`?mode=ro`) to prevent database locking or corruption while Tautulli is actively running.
* **Accurate ID Matching:** Extracts `TMDB`, `IMDB`, and `TVDB` IDs from Trakt exports for near-flawless matching on Simkl's end.
* **Fixes the "Watching" Bug:** Automatically hardcodes the `Watchlist` status to `completed` so Simkl doesn't incorrectly tag your entire history as currently watching.
* **Strict Formatting:** Adheres exactly to Simkl's required headers, including the specific `s1e1` format for episodic data.

## ⚠️ Known Deficiencies & Limitations
* **Simkl Title Matching Bug:** Simkl's CSV importer has a known bug where it shifts column data (putting titles in the `year` column) if it cannot parse an ambiguous TV show title. The Tautulli script mitigates this by stripping `(YYYY)` tags via Regex and injecting hardcoded `TVDB_ID`s for known problematic shows (like *Law & Order* or *The Pitt*). However, brand-new or highly ambiguous titles not in the script's `ID_MAP` may still fail to import.
* **Tautulli Historical Limit:** The Tautulli extraction script can only export data that Tautulli itself has logged. If you watched media on Plex prior to installing Tautulli, that history will not be in the database.
* **Trakt Manual Export:** The Trakt script relies on a manual ZIP download, meaning it is not a real-time sync replacement, but rather a one-time migration tool.
* **Folder Pickers Are Not Recursive:** Both folder pickers/auto-detection only look inside the exact folder you select (or the current/default directory) — they do not search subfolders. If a Tautulli install nests `tautulli.db` in a data subdirectory, browse into that subdirectory directly.

## Prerequisites
* **Python 3.8+** installed on your system.

---

## Usage Guide

### Method 1: Exporting from Trakt.tv

1. Log into your Trakt account and navigate to [Data Settings](https://app.trakt.tv/settings/data).
2. Click **"Export now"** and download the resulting `.zip` file.
3. Extract the archive somewhere convenient.
4. Run the conversion:
   ```bash
   # From inside the extracted folder — no arguments needed:
   python3 convert_trakt_to_simkl.py

   # Or point at the folder explicitly from anywhere:
   python3 convert_trakt_to_simkl.py /path/to/extracted/export

   # If run at a terminal with no argument and no watched-history-*.json
   # files in the current directory, a folder picker opens automatically.
   ```
5. The script parses all `watched-history-*.json` files in that folder and outputs **`simkl_import.csv`** (override with `--output`/`-o`).

### Method 2: Exporting from Tautulli (`tautulli.db`)

You can extract your full watch history, or filter by specific usernames and date ranges.

**1. Standard Full Export (explicit path)**
```bash
python3 convert_tautulli_to_simkl.py --db /path/to/tautulli.db --all-users -o simkl_tautulli_import.csv
```

**2. Let the script find the database and ask which user (interactive)**
```bash
python3 convert_tautulli_to_simkl.py
# Auto-detects tautulli.db in common locations, or opens a folder picker
# if it can't find one. Then prompts you to type or pick a username.
```

**3. Filter by Plex Username (non-interactive, e.g. cron)**
```bash
python3 convert_tautulli_to_simkl.py --db /path/to/tautulli.db --user "your_username" -o simkl_user_history.csv
```

**4. Filter Date Gaps (e.g. records on or after a specific date)**
```bash
python3 convert_tautulli_to_simkl.py --db /path/to/tautulli.db --user "your_username" --since 2026-07-28 -o simkl_gap_import.csv
```

**CLI Options Reference — `convert_tautulli_to_simkl.py`**
* `--db`: Path to `tautulli.db`. If omitted, common Docker/local locations are checked automatically; if none are found and the script is running at a terminal, a folder picker opens.
* `--output`, `-o`: Output CSV filename *(default: `simkl_tautulli_import.csv`)*.
* `--user`, `-u`: Filter by Plex username (case-insensitive). Mutually exclusive with `--all-users`.
* `--all-users`: Explicitly export every user, no prompt.
* `--since`, `-s`: Filter events on or after date formatted as `YYYY-MM-DD`.

> If neither `--user` nor `--all-users` is given: at an interactive terminal you'll be prompted to pick a user; in a non-interactive run (cron, CI, piped) the script exports **all users**, matching the original script's default.

**CLI Options Reference — `convert_trakt_to_simkl.py`**
* `folder` (positional, optional): Folder containing `watched-history-*.json`. Defaults to the current directory; if empty and running at a terminal, a folder picker opens.
* `--output`, `-o`: Output CSV filename *(default: `simkl_import.csv`)*.

---

## Importing to Simkl
1. Go to Simkl's [CSV Import Tool](https://simkl.com/apps/import/csv/).
2. Upload your generated `.csv` file.
3. *Important:* If you are importing a gap or merging multiple files, select **"Add missing watches"** to prevent duplicate entries.

## Data Schema Reference
For reference, these scripts automatically format your data to match the strict column headers expected by Simkl:

| simkl_id | TVDB_ID | TMDB | IMDB_ID | MAL_ID | Type | Title | Year | LastEpWatched | Watchlist | WatchedDate | Rating | Memo |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| | | 1340138 | tt1340138 | | movie | Terminator Genisys | 2015 | | completed | 2015-08-20 | | |
| | 276562 | | | | tv | Power | 2014 | s2e2 | completed | 2015-08-21 | | |

## Troubleshooting
**Q: I need to wipe a bad import from Simkl and try again.**
**A:** You can bulk-delete specific statuses (like "Watching") or wipe your entire history without deleting your account via the [Simkl Account Cleanup tool](https://simkl.com/settings/login/clean-or-delete/).

---

## Contributing

Bug reports, feature requests, and pull requests are welcome — see
[CONTRIBUTING.md](CONTRIBUTING.md) for the dev setup, test/lint commands,
and the rules that keep these scripts zero-dependency and safe to run
unattended.

## Versioning & Releases

This project uses [Semantic Versioning](https://semver.org/); every release
is tagged `vMAJOR.MINOR.PATCH` with notes in [CHANGELOG.md](CHANGELOG.md).
See [CONTRIBUTING.md](CONTRIBUTING.md#versioning--changelog) for what bumps
which number.

## Contributors

* [jshields-ca](https://github.com/jshields-ca) — original scripts, ID map, and project maintenance.
* [Crazy-Lunatic](https://github.com/Crazy-Lunatic) — folder pickers, Tautulli username picker, `--all-users`, and CLI folder support for the Trakt script ([#1](https://github.com/jshields-ca/simkl-csv-converters/pull/1)).

Thank you to everyone who reports issues or opens a PR — see the
[full contributor list](https://github.com/jshields-ca/simkl-csv-converters/graphs/contributors)
on GitHub.

## AI Assistance

Parts of this project were written with AI assistance, disclosed here for
transparency:
* The original scripts and README were drafted with assistance from
  **Google Gemini Pro**.
* The v1.1.0 update — merging in community contributions, the fixes,
  automation-safe defaults, the test suite, CI workflow, and this
  documentation/repo setup — was done with assistance from **Claude**
  (Anthropic).

All AI-assisted code is reviewed, tested, and maintained by a human
(the repo owner) before being merged.

---
*Authored by [jshields-ca](https://github.com/jshields-ca).*
