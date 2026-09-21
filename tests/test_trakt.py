import csv
import json
import sys
from unittest.mock import MagicMock

import convert_trakt_to_simkl as trakt


def write_history_file(folder, name, items):
    (folder / name).write_text(json.dumps(items), encoding='utf-8')


MOVIE_ITEM = {
    "type": "movie",
    "watched_at": "2024-05-01T12:00:00.000Z",
    "movie": {"title": "Movie A", "year": 2020, "ids": {"tmdb": "111", "imdb": "tt111"}},
}
EPISODE_ITEM = {
    "type": "episode",
    "watched_at": "2024-05-02T12:00:00.000Z",
    "show": {"title": "Show A", "year": 2019, "ids": {"tvdb": "222", "tmdb": "223", "imdb": "tt222"}},
    "episode": {"season": 1, "number": 3},
}


# --- convert_trakt_export: multiple JSON files ----------------------------

def test_convert_trakt_export_merges_multiple_json_files(tmp_path):
    write_history_file(tmp_path, "watched-history-movies.json", [MOVIE_ITEM])
    write_history_file(tmp_path, "watched-history-episodes.json", [EPISODE_ITEM])

    output_path = tmp_path / "simkl_import.csv"
    file_count, row_count = trakt.convert_trakt_export(tmp_path, output_path)

    assert file_count == 2
    assert row_count == 2

    with output_path.open(newline='', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))

    titles = {r["Title"] for r in rows}
    assert titles == {"Movie A", "Show A"}

    episode_row = next(r for r in rows if r["Title"] == "Show A")
    assert episode_row["LastEpWatched"] == "s1e3"
    assert episode_row["TVDB_ID"] == "222"

    movie_row = next(r for r in rows if r["Title"] == "Movie A")
    assert movie_row["TMDB"] == "111"
    assert movie_row["Watchlist"] == "completed"


def test_convert_trakt_export_no_matching_files_returns_zero(tmp_path):
    output_path = tmp_path / "out.csv"
    file_count, row_count = trakt.convert_trakt_export(tmp_path, output_path)
    assert (file_count, row_count) == (0, 0)


# --- resolve_input_folder: explicit / cwd default / non-interactive ------

def test_resolve_input_folder_explicit_argument(tmp_path):
    assert trakt.resolve_input_folder(str(tmp_path)) == tmp_path


def test_resolve_input_folder_defaults_to_cwd_when_files_present(tmp_path, monkeypatch):
    write_history_file(tmp_path, "watched-history-x.json", [MOVIE_ITEM])
    monkeypatch.chdir(tmp_path)

    assert trakt.resolve_input_folder(None) == tmp_path


def test_resolve_input_folder_noninteractive_no_files_returns_none(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)

    assert trakt.resolve_input_folder(None) is None


# --- interactive picker: cancellation --------------------------------------

def test_choose_input_folder_returns_none_when_dialog_cancelled(monkeypatch):
    fake_tk_module = MagicMock()
    fake_root = MagicMock()
    fake_tk_module.Tk.return_value = fake_root
    fake_tk_module.TclError = Exception

    fake_filedialog = MagicMock()
    fake_filedialog.askdirectory.return_value = ''  # user hit Cancel

    monkeypatch.setitem(sys.modules, "tkinter", fake_tk_module)
    monkeypatch.setitem(sys.modules, "tkinter.filedialog", fake_filedialog)
    fake_tk_module.filedialog = fake_filedialog

    result = trakt.choose_input_folder()

    assert result is None
    fake_root.destroy.assert_called_once()


# --- main(): exit codes ---------------------------------------------------

def test_main_no_json_files_returns_1(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["prog", str(tmp_path)])
    assert trakt.main() == 1


def test_main_success_returns_0_and_respects_output_option(tmp_path, monkeypatch):
    write_history_file(tmp_path, "watched-history-x.json", [MOVIE_ITEM])
    output = tmp_path / "custom_output.csv"
    monkeypatch.setattr(sys, "argv", ["prog", str(tmp_path), "-o", str(output)])

    assert trakt.main() == 0
    assert output.is_file()
