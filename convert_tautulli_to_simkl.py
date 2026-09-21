#!/usr/bin/env python3
"""
Tautulli to Simkl CSV Converter
Authored by jshields-ca (assisted by Gemini Pro). Folder/username pickers
contributed by Crazy-Lunatic (https://github.com/jshields-ca/simkl-csv-converters/pull/1).

Extracts watch history from a local Tautulli SQLite database (tautulli.db)
and converts it into a CSV schema ready for direct import into Simkl.

Interactive pickers (folder/username) only appear when the script is run at
a terminal (sys.stdin.isatty()). When run non-interactively (cron, CI, piped
input), the script always falls back to the classic non-interactive
defaults: auto-detected DB path, and ALL users if --user/--all-users is
not given. This keeps existing automation working unattended.
"""

import argparse
import csv
import datetime
import re
import sqlite3
import sys
from pathlib import Path

SIMKL_COLUMNS = [
    'simkl_id', 'TVDB_ID', 'TMDB', 'IMDB_ID', 'MAL_ID',
    'Type', 'Title', 'Year', 'LastEpWatched',
    'Watchlist', 'WatchedDate', 'Rating', 'Memo'
]

# Hardcoded database IDs for ambiguous or brand-new shows that fail Simkl's text matching
ID_MAP = {
    "law & order": {"TVDB_ID": "70522", "TMDB": "549", "IMDB_ID": "tt0098844"},
    "the pitt": {"TVDB_ID": "448698", "TMDB": "249673", "IMDB_ID": "tt31953406"},
    "paradise": {"TVDB_ID": "445209", "TMDB": "247063", "IMDB_ID": "tt31062634"},
    "the amateur": {"TMDB": "1129598", "IMDB_ID": "tt8332922"},
    "platonic": {"TVDB_ID": "391448", "TMDB": "114461", "IMDB_ID": "tt13317132"},
    "the last frontier": {"TVDB_ID": "430538", "TMDB": "221376", "IMDB_ID": "tt26887532"},
    "fallout": {"TVDB_ID": "339031", "TMDB": "113988", "IMDB_ID": "tt12637874"}
}


def find_default_db():
    """Check common locations for tautulli.db. Returns a Path, or None if not found."""
    candidates = [
        Path('~/docker/appdata/tautulli/tautulli.db').expanduser(),
        Path('./tautulli.db'),
        Path('/opt/tautulli/tautulli.db'),
    ]
    for path in candidates:
        if path.is_file():
            return path
    return None


def prompt_for_db_path():
    """Fallback when a graphical folder picker is unavailable."""
    print("The folder picker is unavailable on this Python installation.")
    entered = input(
        "Enter the folder containing tautulli.db, or the full path to the database: "
    ).strip().strip('"')

    if not entered:
        return None

    path = Path(entered).expanduser()
    if path.is_dir():
        return find_db_in_folder(path)
    return path


def find_db_in_folder(folder):
    """Find the Tautulli database inside a selected folder (non-recursive)."""
    folder = Path(folder)
    preferred = folder / 'tautulli.db'

    if preferred.is_file():
        return preferred

    candidates = sorted(folder.glob('*.db'))
    if len(candidates) == 1:
        return candidates[0]

    if not candidates:
        print(f"[ERROR] No .db database file was found in: {folder}", file=sys.stderr)
    else:
        print(
            f"[ERROR] More than one .db file was found in {folder}. "
            "Use --db with the exact database path.",
            file=sys.stderr,
        )
        for candidate in candidates:
            print(f"  - {candidate.name}", file=sys.stderr)

    return None


def choose_db_path():
    """Open a folder picker so the user can choose where tautulli.db lives."""
    script_dir = Path(__file__).resolve().parent

    try:
        import tkinter as tk
        from tkinter import filedialog
    except ImportError:
        return prompt_for_db_path()

    root = None
    try:
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        selected = filedialog.askdirectory(
            title='Select the folder containing tautulli.db',
            initialdir=str(script_dir),
            mustexist=True,
        )
    except tk.TclError:
        return prompt_for_db_path()
    finally:
        if root is not None:
            try:
                root.destroy()
            except tk.TclError:
                pass

    if not selected:
        return None

    return find_db_in_folder(Path(selected))


def resolve_db_path(cli_db):
    """
    Resolve the tautulli.db path to use.

    Precedence: explicit --db > auto-detected common location > (interactive
    only) folder picker. Returns None when nothing could be resolved.
    """
    if cli_db:
        return Path(cli_db).expanduser()

    auto = find_default_db()
    if auto is not None:
        return auto

    if sys.stdin.isatty():
        return choose_db_path()

    print(
        "[ERROR] No tautulli.db found in the default locations. "
        "Pass --db /path/to/tautulli.db explicitly for non-interactive runs.",
        file=sys.stderr,
    )
    return None


def connect_read_only(db_path):
    """Open a SQLite database in read-only mode."""
    db_path = Path(db_path).expanduser().resolve()

    if not db_path.is_file():
        raise FileNotFoundError(f"Database not found at: {db_path}")

    db_uri = f"{db_path.as_uri()}?mode=ro"
    conn = sqlite3.connect(db_uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def get_users(db_path):
    """Return usernames with the number of movie/episode watch records for each."""
    try:
        conn = connect_read_only(db_path)
    except (FileNotFoundError, sqlite3.Error) as exc:
        print(f"[ERROR] Failed to open database: {exc}", file=sys.stderr)
        return []

    try:
        rows = conn.execute(
            """
            SELECT
                MIN(sh.user) AS username,
                COUNT(*) AS watch_count
            FROM session_history sh
            WHERE sh.media_type IN ('episode', 'movie')
              AND TRIM(COALESCE(sh.user, '')) <> ''
            GROUP BY LOWER(sh.user)
            ORDER BY LOWER(MIN(sh.user))
            """
        ).fetchall()
        return [(row['username'], row['watch_count']) for row in rows]
    except sqlite3.Error as exc:
        print(f"[ERROR] Failed to read users from database: {exc}", file=sys.stderr)
        return []
    finally:
        conn.close()


def match_username(entered, users):
    """Return the database's canonical username for a case-insensitive match."""
    wanted = entered.strip().casefold()
    for username, _count in users:
        if username.casefold() == wanted:
            return username
    return None


def choose_user(db_path):
    """Interactively let the user type a username or choose one from the DB."""
    users = get_users(db_path)

    if not users:
        print("[ERROR] No users with movie or episode watch history were found.", file=sys.stderr)
        return None

    while True:
        print()
        print("Do you know the username you want history from?")
        print("  1. Yes - type the username")
        print("  2. No  - show me the users in this database")
        choice = input("Choose 1 or 2: ").strip().lower()

        if choice in {'1', 'yes', 'y'}:
            entered = input("Username: ").strip()
            matched = match_username(entered, users)
            if matched:
                print(f"Selected user: {matched}")
                return matched

            print(f"[ERROR] Username '{entered}' was not found in this database.")
            retry = input("Try again? [Y/n]: ").strip().lower()
            if retry in {'n', 'no'}:
                return None

        elif choice in {'2', 'no', 'n', 'list', 'l'}:
            print()
            print("Users found in this Tautulli database:")
            for index, (username, watch_count) in enumerate(users, start=1):
                print(f"  {index:>2}. {username} ({watch_count} watch records)")

            while True:
                selected = input(
                    "Enter the number of the user you want, or type the username: "
                ).strip()

                if selected.isdigit():
                    index = int(selected)
                    if 1 <= index <= len(users):
                        username = users[index - 1][0]
                        print(f"Selected user: {username}")
                        return username
                    print(f"[ERROR] Enter a number from 1 to {len(users)}.")
                    continue

                matched = match_username(selected, users)
                if matched:
                    print(f"Selected user: {matched}")
                    return matched

                print(f"[ERROR] Username '{selected}' was not found in this database.")

        else:
            print("[ERROR] Please choose 1 or 2.")


def export_tautulli_history(db_path, output_path, user=None, since=None):
    """
    Export watch history to a Simkl-compatible CSV.

    Returns the number of records written (0 is a valid, successful export
    with no matches) on success, or None if an error occurred.
    """
    try:
        conn = connect_read_only(db_path)
        cursor = conn.cursor()
    except (FileNotFoundError, sqlite3.Error) as exc:
        print(f"[ERROR] Failed to connect to database: {exc}", file=sys.stderr)
        return None

    query = """
        SELECT
            sh.media_type,
            sh.user,
            shm.grandparent_title,
            shm.title,
            shm.year,
            shm.parent_media_index AS season,
            shm.media_index AS episode,
            sh.started
        FROM session_history sh
        JOIN session_history_metadata shm ON sh.id = shm.id
        WHERE sh.media_type IN ('episode', 'movie')
    """
    params = []

    if user:
        query += " AND LOWER(sh.user) = LOWER(?)"
        params.append(user)

    if since:
        try:
            dt = datetime.datetime.strptime(since, '%Y-%m-%d')
            epoch_since = int(dt.timestamp())
            query += " AND sh.started >= ?"
            params.append(epoch_since)
        except ValueError:
            print(
                f"[WARNING] Invalid date format for --since '{since}'. "
                "Expected YYYY-MM-DD. Ignoring date filter."
            )

    query += " ORDER BY sh.started ASC"

    try:
        cursor.execute(query, params)
        rows = cursor.fetchall()
    except sqlite3.Error as exc:
        print(f"[ERROR] Failed to read watch history: {exc}", file=sys.stderr)
        conn.close()
        return None

    if not rows:
        print("[INFO] No watch records found matching the specified criteria.")
        conn.close()
        return 0

    output_path = Path(output_path).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open('w', newline='', encoding='utf-8') as outfile:
        writer = csv.DictWriter(outfile, fieldnames=SIMKL_COLUMNS)
        writer.writeheader()

        count = 0
        for row in rows:
            simkl_row = {col: '' for col in SIMKL_COLUMNS}

            if row['started']:
                simkl_row['WatchedDate'] = datetime.datetime.fromtimestamp(
                    row['started']
                ).strftime('%Y-%m-%d')

            simkl_row['Watchlist'] = 'completed'
            media_type = (row['media_type'] or '').lower()

            if media_type == 'episode':
                simkl_row['Type'] = 'tv'
                simkl_row['Title'] = row['grandparent_title'] or row['title']
                simkl_row['Year'] = ''
                season = row['season']
                episode = row['episode']
                if season is not None and episode is not None:
                    simkl_row['LastEpWatched'] = f"s{season}e{episode}"
            elif media_type == 'movie':
                simkl_row['Type'] = 'movie'
                simkl_row['Title'] = row['title'] or ''
                simkl_row['Year'] = row['year'] or ''

            # Inject explicit IDs for known ambiguous titles.
            # Strip a trailing " (YYYY)" from Tautulli titles before ID-map matching.
            title_clean = re.sub(
                r'\s*\(\d{4}\)$', '', simkl_row['Title']
            ).lower().strip()

            if title_clean in ID_MAP:
                if 'TVDB_ID' in ID_MAP[title_clean]:
                    simkl_row['TVDB_ID'] = ID_MAP[title_clean]['TVDB_ID']
                if 'TMDB' in ID_MAP[title_clean]:
                    simkl_row['TMDB'] = ID_MAP[title_clean]['TMDB']
                if 'IMDB_ID' in ID_MAP[title_clean]:
                    simkl_row['IMDB_ID'] = ID_MAP[title_clean]['IMDB_ID']

            writer.writerow(simkl_row)
            count += 1

    conn.close()
    print(f"[SUCCESS] Exported {count} records for '{user or 'ALL USERS'}' to '{output_path}'.")
    return count


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Export Tautulli watch history to a Simkl-compatible CSV. "
            "Run at an interactive terminal with --db/--user omitted to use "
            "folder and username pickers; non-interactive runs (cron, CI) "
            "fall back to auto-detecting the DB and exporting all users."
        )
    )
    parser.add_argument(
        '--db',
        default=None,
        help="Path to tautulli.db. If omitted, common locations are checked automatically."
    )
    parser.add_argument(
        '--output', '-o',
        default='simkl_tautulli_import.csv',
        help="Output CSV file path (default: simkl_tautulli_import.csv)"
    )

    user_group = parser.add_mutually_exclusive_group()
    user_group.add_argument(
        '--user', '-u',
        default=None,
        help="Filter watch history by a specific username"
    )
    user_group.add_argument(
        '--all-users',
        action='store_true',
        help="Explicitly export watch history for every user"
    )

    parser.add_argument(
        '--since', '-s',
        default=None,
        help="Filter records watched on or after this date (YYYY-MM-DD)"
    )

    args = parser.parse_args()

    db_path = resolve_db_path(args.db)
    if db_path is None:
        print("[INFO] No Tautulli database selected. Nothing was exported.")
        return 1

    db_path = db_path.expanduser().resolve()
    if not db_path.is_file():
        print(f"[ERROR] Database not found at: {db_path}", file=sys.stderr)
        return 1

    if args.all_users:
        selected_user = None
    elif args.user:
        users = get_users(db_path)
        selected_user = match_username(args.user, users)
        if selected_user is None:
            print(
                f"[ERROR] Username '{args.user}' was not found in this database.",
                file=sys.stderr,
            )
            return 1
    elif sys.stdin.isatty():
        selected_user = choose_user(db_path)
        if selected_user is None:
            print("[INFO] No user selected. Nothing was exported.")
            return 1
    else:
        # Non-interactive run with no --user/--all-users: preserve the
        # classic default of exporting every user.
        selected_user = None

    print(f"Database: {db_path}")
    if selected_user:
        print(f"Filtering watch history for user: {selected_user}")
    else:
        print("Exporting watch history for ALL USERS.")

    count = export_tautulli_history(
        db_path,
        args.output,
        selected_user,
        args.since,
    )
    if count is None:
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
