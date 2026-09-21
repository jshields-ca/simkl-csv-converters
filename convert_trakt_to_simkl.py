#!/usr/bin/env python3
"""
Trakt to Simkl CSV Converter
Authored by jshields-ca (assisted by Gemini Pro). Folder picker and CLI
folder argument contributed by Crazy-Lunatic
(https://github.com/jshields-ca/simkl-csv-converters/pull/1).

Converts watched-history-*.json files from a Trakt.tv data export into a
CSV schema ready for direct import into Simkl.

The folder picker only appears when the script is run at a terminal
(sys.stdin.isatty()). When run non-interactively, or when watched-history
files are already present in the current directory, the classic default
(current working directory) is used with no prompt.
"""

import argparse
import csv
import json
import sys
from pathlib import Path

# Strict Simkl headers based on their template
CSV_COLUMNS = [
    'simkl_id', 'TVDB_ID', 'TMDB', 'IMDB_ID', 'MAL_ID', 'Type', 'Title',
    'Year', 'LastEpWatched', 'Watchlist', 'WatchedDate', 'Rating', 'Memo'
]

DEFAULT_OUTPUT_FILE = 'simkl_import.csv'


def prompt_for_input_folder():
    """Fallback for Python installs where the graphical folder picker is unavailable."""
    print('The folder picker is unavailable on this Python installation.')
    typed_path = input(
        'Enter the folder containing watched-history-*.json files: '
    ).strip().strip('"')
    return Path(typed_path).expanduser() if typed_path else None


def choose_input_folder():
    """Open a folder picker for the Trakt export directory."""
    script_dir = Path(__file__).resolve().parent

    try:
        import tkinter as tk
        from tkinter import filedialog
    except ImportError:
        return prompt_for_input_folder()

    root = None
    try:
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        selected = filedialog.askdirectory(
            title='Select the folder containing Trakt watched JSON files',
            initialdir=str(script_dir),
            mustexist=True,
        )
    except tk.TclError:
        return prompt_for_input_folder()
    finally:
        if root is not None:
            try:
                root.destroy()
            except tk.TclError:
                pass

    return Path(selected) if selected else None


def resolve_input_folder(cli_folder):
    """
    Resolve the folder to search for watched-history-*.json files.

    Precedence: explicit folder argument > current directory (if it already
    has matching files) > (interactive only) folder picker. Returns None
    when nothing could be resolved.
    """
    if cli_folder:
        return Path(cli_folder).expanduser()

    cwd = Path.cwd()
    if list(cwd.glob('watched-history-*.json')):
        return cwd

    if sys.stdin.isatty():
        return choose_input_folder()

    print(
        "[ERROR] No watched-history-*.json files found in the current directory. "
        "Pass a folder argument explicitly for non-interactive runs.",
        file=sys.stderr,
    )
    return None


def convert_trakt_export(input_folder, output_path):
    """Convert watched-history-*.json files from one Trakt export folder."""
    json_files = sorted(input_folder.glob('watched-history-*.json'))

    if not json_files:
        print(f'[ERROR] No watched-history-*.json files were found in: {input_folder}', file=sys.stderr)
        return 0, 0

    rows_written = 0

    with output_path.open('w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=CSV_COLUMNS)
        writer.writeheader()

        for file in json_files:
            with file.open('r', encoding='utf-8') as f:
                data = json.load(f)

            for item in data:
                # Initialize an empty row matching the exact column keys
                row = {col: '' for col in CSV_COLUMNS}

                row['Type'] = item.get('type', '')

                # Trakt dates are ISO 8601; slicing the first 10 chars gives us standard YYYY-MM-DD
                row['WatchedDate'] = (
                    item.get('watched_at', '')[:10]
                    if item.get('watched_at')
                    else ''
                )

                # Hardcoding to 'completed' as defined by Simkl's Watchlist header expectations
                row['Watchlist'] = 'completed'

                # Handle Shows/Episodes
                if row['Type'] == 'episode':
                    show = item.get('show', {})
                    episode = item.get('episode', {})
                    ids = show.get('ids', {})

                    row['Title'] = show.get('title', '')
                    row['Year'] = show.get('year', '')

                    season = episode.get('season', '')
                    ep_num = episode.get('number', '')
                    row['LastEpWatched'] = f"s{season}e{ep_num}"

                    # Extract robust IDs for matching
                    row['TVDB_ID'] = ids.get('tvdb', '')
                    row['TMDB'] = ids.get('tmdb', '')
                    row['IMDB_ID'] = ids.get('imdb', '')

                # Handle Movies
                elif row['Type'] == 'movie':
                    movie = item.get('movie', {})
                    ids = movie.get('ids', {})

                    row['Title'] = movie.get('title', '')
                    row['Year'] = movie.get('year', '')

                    # Extract robust IDs for matching
                    row['TMDB'] = ids.get('tmdb', '')
                    row['IMDB_ID'] = ids.get('imdb', '')

                writer.writerow(row)
                rows_written += 1

    return len(json_files), rows_written


def main():
    parser = argparse.ArgumentParser(
        description='Convert Trakt watched-history JSON exports into a Simkl import CSV.'
    )
    parser.add_argument(
        'folder',
        nargs='?',
        help=(
            "Folder containing watched-history-*.json files. Defaults to the "
            "current directory; if run at a terminal and no files are found "
            "there, a folder picker opens."
        ),
    )
    parser.add_argument(
        '--output', '-o',
        default=DEFAULT_OUTPUT_FILE,
        help=f"Output CSV file path (default: {DEFAULT_OUTPUT_FILE})",
    )
    args = parser.parse_args()

    input_folder = resolve_input_folder(args.folder)
    if input_folder is None:
        print('[INFO] No folder selected. Nothing was converted.')
        return 1

    input_folder = input_folder.resolve()

    if not input_folder.is_dir():
        print(f'[ERROR] The selected path is not a folder: {input_folder}', file=sys.stderr)
        return 1

    output_path = Path(args.output).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    file_count, row_count = convert_trakt_export(input_folder, output_path)

    if file_count == 0:
        return 1

    print(f'Selected Trakt export folder: {input_folder}')
    print(f'Processed {file_count} watched-history JSON file(s) and wrote {row_count} row(s).')
    print(f"Success! Data compiled into {output_path} matching Simkl's strict schema.")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
