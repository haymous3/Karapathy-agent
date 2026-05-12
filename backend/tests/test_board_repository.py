from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.db import BoardRepository
from app.seed_data import DEFAULT_BOARD_DATA


def make_repo(tmp_path: Path) -> BoardRepository:
    schema_path = Path(__file__).resolve().parents[1] / "app" / "schema.sql"
    repo = BoardRepository(
        db_path=tmp_path / "repo.sqlite3",
        schema_path=schema_path,
        default_board=DEFAULT_BOARD_DATA,
    )
    repo.initialize()
    return repo


def test_repository_seeds_default_board_for_new_user(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)

    board = repo.get_board("user")

    assert board == DEFAULT_BOARD_DATA


def test_repository_save_preserves_column_and_card_order(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    payload = {
        "columns": [
            {"id": "col-a", "title": "A", "cardIds": ["card-3", "card-1"]},
            {"id": "col-b", "title": "B", "cardIds": ["card-2"]},
        ],
        "cards": {
            "card-1": {"id": "card-1", "title": "One", "details": "first"},
            "card-2": {"id": "card-2", "title": "Two", "details": "second"},
            "card-3": {"id": "card-3", "title": "Three", "details": "third"},
        },
    }

    repo.save_board("user", payload)
    board = repo.get_board("user")

    assert board == payload


def test_repository_isolates_data_per_user(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    payload_user_a = {
        "columns": [
            {"id": "col-a", "title": "A", "cardIds": ["card-a"]},
        ],
        "cards": {
            "card-a": {"id": "card-a", "title": "A", "details": "A details"},
        },
    }

    repo.save_board("alice", payload_user_a)
    board_alice = repo.get_board("alice")
    board_bob = repo.get_board("bob")

    assert board_alice == payload_user_a
    assert board_bob == DEFAULT_BOARD_DATA


def test_repository_persists_across_reinitialization(tmp_path: Path) -> None:
    schema_path = Path(__file__).resolve().parents[1] / "app" / "schema.sql"
    db_path = tmp_path / "repo.sqlite3"
    payload = {
        "columns": [{"id": "col-x", "title": "X", "cardIds": ["card-x"]}],
        "cards": {"card-x": {"id": "card-x", "title": "X", "details": "persisted"}},
    }

    repo_one = BoardRepository(db_path=db_path, schema_path=schema_path, default_board=DEFAULT_BOARD_DATA)
    repo_one.initialize()
    repo_one.save_board("user", payload)

    repo_two = BoardRepository(db_path=db_path, schema_path=schema_path, default_board=DEFAULT_BOARD_DATA)
    repo_two.initialize()
    board = repo_two.get_board("user")

    assert board == payload
