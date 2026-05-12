from copy import deepcopy
from pathlib import Path
import sqlite3


class BoardRepository:
    def __init__(self, db_path: Path, schema_path: Path, default_board: dict) -> None:
        self.db_path = db_path
        self.schema_path = schema_path
        self.default_board = deepcopy(default_board)

    def initialize(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        schema_sql = self.schema_path.read_text(encoding="utf-8")
        with self._connect() as conn:
            conn.executescript(schema_sql)
            conn.commit()

    def get_board(self, username: str) -> dict:
        with self._connect() as conn:
            board_id = self._ensure_user_and_board(conn, username)
            board = self._load_board(conn, board_id)
            conn.commit()
            return board

    def save_board(self, username: str, board: dict) -> dict:
        with self._connect() as conn:
            board_id = self._ensure_user_and_board(conn, username)
            self._replace_board(conn, board_id, board)
            saved = self._load_board(conn, board_id)
            conn.commit()
            return saved

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _ensure_user_and_board(self, conn: sqlite3.Connection, username: str) -> int:
        conn.execute("INSERT OR IGNORE INTO users (username) VALUES (?)", (username,))
        user_row = conn.execute(
            "SELECT id FROM users WHERE username = ?",
            (username,),
        ).fetchone()
        if user_row is None:
            raise RuntimeError("Failed to resolve user row")

        user_id = int(user_row["id"])
        conn.execute(
            "INSERT OR IGNORE INTO boards (user_id, name) VALUES (?, ?)",
            (user_id, "My Board"),
        )
        board_row = conn.execute(
            "SELECT id FROM boards WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        if board_row is None:
            raise RuntimeError("Failed to resolve board row")

        board_id = int(board_row["id"])
        column_count_row = conn.execute(
            "SELECT COUNT(1) AS count FROM board_columns WHERE board_id = ?",
            (board_id,),
        ).fetchone()
        if column_count_row and int(column_count_row["count"]) == 0:
            self._replace_board(conn, board_id, deepcopy(self.default_board))

        return board_id

    def _replace_board(self, conn: sqlite3.Connection, board_id: int, board: dict) -> None:
        conn.execute("DELETE FROM cards WHERE board_id = ?", (board_id,))
        conn.execute("DELETE FROM board_columns WHERE board_id = ?", (board_id,))

        column_db_id_by_external: dict[str, int] = {}
        for column_position, column in enumerate(board["columns"]):
            cursor = conn.execute(
                """
                INSERT INTO board_columns (board_id, external_id, title, position)
                VALUES (?, ?, ?, ?)
                """,
                (board_id, column["id"], column["title"], column_position),
            )
            column_db_id_by_external[column["id"]] = int(cursor.lastrowid)

        for column in board["columns"]:
            column_db_id = column_db_id_by_external[column["id"]]
            for card_position, card_external_id in enumerate(column["cardIds"]):
                card = board["cards"][card_external_id]
                conn.execute(
                    """
                    INSERT INTO cards (board_id, column_id, external_id, title, details, position)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        board_id,
                        column_db_id,
                        card["id"],
                        card["title"],
                        card["details"],
                        card_position,
                    ),
                )

        conn.execute(
            "UPDATE boards SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (board_id,),
        )

    def _load_board(self, conn: sqlite3.Connection, board_id: int) -> dict:
        column_rows = conn.execute(
            """
            SELECT external_id, title
            FROM board_columns
            WHERE board_id = ?
            ORDER BY position ASC
            """,
            (board_id,),
        ).fetchall()

        board = {"columns": [], "cards": {}}
        columns_by_external_id: dict[str, dict] = {}

        for row in column_rows:
            column_payload = {
                "id": row["external_id"],
                "title": row["title"],
                "cardIds": [],
            }
            board["columns"].append(column_payload)
            columns_by_external_id[row["external_id"]] = column_payload

        card_rows = conn.execute(
            """
            SELECT
              bc.external_id AS column_external_id,
              c.external_id,
              c.title,
              c.details
            FROM cards c
            JOIN board_columns bc ON bc.id = c.column_id
            WHERE c.board_id = ?
            ORDER BY bc.position ASC, c.position ASC
            """,
            (board_id,),
        ).fetchall()

        for row in card_rows:
            card_id = row["external_id"]
            columns_by_external_id[row["column_external_id"]]["cardIds"].append(card_id)
            board["cards"][card_id] = {
                "id": card_id,
                "title": row["title"],
                "details": row["details"],
            }

        return board
