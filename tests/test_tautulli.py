import csv
import sqlite3
import sys
from unittest.mock import MagicMock

import convert_tautulli_to_simkl as tautulli


def make_db(tmp_path, rows):
    """Create a minimal Tautulli-schema SQLite DB with the given watch rows.

    Each row is a dict with keys: media_type, user, grandparent_title,
    title, year, season, episode, started.
    """
    db_path = tmp_path / "tautulli.db"
    conn = sqlite3.connect(db_path)
    conn.executescript(
        """
        CREATE TABLE session_history (
            id INTEGER PRIMARY KEY,
            media_type TEXT,
            user TEXT,
            started INTEGER
        );
        CREATE TABLE session_history_metadata (
            id INTEGER PRIMARY KEY,
            grandparent_title TEXT,
            title TEXT,
            year INTEGER,
            parent_media_index INTEGER,
            media_index INTEGER
        );
        """
    )
    for i, row in enumerate(rows, start=1):
        conn.execute(
            "INSERT INTO session_history (id, media_type, user, started) VALUES (?, ?, ?, ?)",
            (i, row["media_type"], row["user"], row.get("started", 1700000000)),
        )
        conn.execute(
            """
            INSERT INTO session_history_metadata
                (id, grandparent_title, title, year, parent_media_index, media_index)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                i,
                row.get("grandparent_title"),
                row.get("title"),
                row.get("year"),
                row.get("season"),
                row.get("episode"),
            ),
        )
    conn.commit()
    conn.close()
    return db_path


# --- find_db_in_folder ---------------------------------------------------

def test_find_db_in_folder_prefers_tautulli_db(tmp_path):
    (tmp_path / "tautulli.db").touch()
    (tmp_path / "other.db").touch()
    assert tautulli.find_db_in_folder(tmp_path) == tmp_path / "tautulli.db"


def test_find_db_in_folder_single_db_fallback(tmp_path):
    only_db = tmp_path / "backup.db"
    only_db.touch()
    assert tautulli.find_db_in_folder(tmp_path) == only_db


def test_find_db_in_folder_no_db_returns_none(tmp_path):
    assert tautulli.find_db_in_folder(tmp_path) is None


def test_find_db_in_folder_multiple_ambiguous_db_returns_none(tmp_path):
    (tmp_path / "a.db").touch()
    (tmp_path / "b.db").touch()
    assert tautulli.find_db_in_folder(tmp_path) is None


# --- get_users / match_username (case-insensitive, duplicates) -----------

def test_get_users_counts_and_folds_case_insensitive_duplicates(tmp_path):
    db_path = make_db(
        tmp_path,
        [
            {"media_type": "movie", "user": "Bob", "title": "Movie A", "year": 2020},
            {"media_type": "movie", "user": "bob", "title": "Movie B", "year": 2021},
            {"media_type": "episode", "user": "Alice", "grandparent_title": "Show A"},
        ],
    )
    users = tautulli.get_users(db_path)
    usernames = {u for u, _count in users}

    # "Bob" and "bob" fold into a single canonical entry with a combined count.
    assert len(users) == 2
    assert "Alice" in usernames
    bob_entry = next(u for u in users if u[0].casefold() == "bob")
    assert bob_entry[1] == 2


def test_match_username_is_case_insensitive():
    users = [("Alice", 3), ("Bob", 1)]
    assert tautulli.match_username("alice", users) == "Alice"
    assert tautulli.match_username("BOB", users) == "Bob"
    assert tautulli.match_username("carol", users) is None


# --- export_tautulli_history: success, filtering, empty, errors ----------

def test_export_history_all_users(tmp_path):
    db_path = make_db(
        tmp_path,
        [
            {"media_type": "movie", "user": "Alice", "title": "Movie A", "year": 2020},
            {"media_type": "movie", "user": "Bob", "title": "Movie B", "year": 2021},
        ],
    )
    output = tmp_path / "out.csv"
    count = tautulli.export_tautulli_history(db_path, output, user=None)

    assert count == 2
    with output.open(newline='', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    assert {r["Title"] for r in rows} == {"Movie A", "Movie B"}


def test_export_history_filtered_by_user(tmp_path):
    db_path = make_db(
        tmp_path,
        [
            {"media_type": "movie", "user": "Alice", "title": "Movie A", "year": 2020},
            {"media_type": "movie", "user": "Bob", "title": "Movie B", "year": 2021},
        ],
    )
    output = tmp_path / "out.csv"
    count = tautulli.export_tautulli_history(db_path, output, user="alice")

    assert count == 1
    with output.open(newline='', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    assert rows[0]["Title"] == "Movie A"


def test_export_history_empty_result_is_success_not_error(tmp_path):
    db_path = make_db(tmp_path, [])
    output = tmp_path / "out.csv"
    count = tautulli.export_tautulli_history(db_path, output, user=None)

    # A valid query with zero matches must be a successful 0, not None (error).
    assert count == 0


def test_export_history_missing_db_returns_none(tmp_path):
    missing = tmp_path / "does_not_exist.db"
    output = tmp_path / "out.csv"
    count = tautulli.export_tautulli_history(missing, output, user=None)

    assert count is None


# --- main(): exit codes ---------------------------------------------------

def test_main_missing_db_returns_1(tmp_path, monkeypatch, capsys):
    missing = tmp_path / "nope.db"
    monkeypatch.setattr(sys, "argv", ["prog", "--db", str(missing), "--all-users"])
    assert tautulli.main() == 1


def test_main_empty_export_returns_0(tmp_path, monkeypatch):
    db_path = make_db(tmp_path, [])
    output = tmp_path / "out.csv"
    monkeypatch.setattr(
        sys, "argv",
        ["prog", "--db", str(db_path), "--all-users", "-o", str(output)],
    )
    assert tautulli.main() == 0


def test_main_unknown_user_returns_1(tmp_path, monkeypatch):
    db_path = make_db(
        tmp_path, [{"media_type": "movie", "user": "Alice", "title": "X", "year": 2020}]
    )
    monkeypatch.setattr(sys, "argv", ["prog", "--db", str(db_path), "--user", "nobody"])
    assert tautulli.main() == 1


def test_main_noninteractive_without_user_flag_defaults_to_all_users(tmp_path, monkeypatch):
    """Non-interactive runs (isatty() == False) must not block on a prompt."""
    db_path = make_db(
        tmp_path,
        [
            {"media_type": "movie", "user": "Alice", "title": "X", "year": 2020},
            {"media_type": "movie", "user": "Bob", "title": "Y", "year": 2021},
        ],
    )
    output = tmp_path / "out.csv"
    monkeypatch.setattr(sys, "argv", ["prog", "--db", str(db_path), "-o", str(output)])
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)

    assert tautulli.main() == 0
    with output.open(newline='', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 2


# --- interactive pickers: cancellation -------------------------------------

def test_choose_db_path_returns_none_when_dialog_cancelled(monkeypatch, tmp_path):
    fake_tk_module = MagicMock()
    fake_root = MagicMock()
    fake_tk_module.Tk.return_value = fake_root
    fake_tk_module.TclError = Exception

    fake_filedialog = MagicMock()
    fake_filedialog.askdirectory.return_value = ''  # user hit Cancel

    monkeypatch.setitem(sys.modules, "tkinter", fake_tk_module)
    monkeypatch.setitem(sys.modules, "tkinter.filedialog", fake_filedialog)
    fake_tk_module.filedialog = fake_filedialog

    result = tautulli.choose_db_path()

    assert result is None
    fake_root.destroy.assert_called_once()


def test_resolve_db_path_noninteractive_with_no_default_errors(monkeypatch, tmp_path):
    monkeypatch.setattr(tautulli, "find_default_db", lambda: None)
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)

    assert tautulli.resolve_db_path(None) is None
