"""LocalStorage: SQLite + local disk implementation of storage/base.py.

SQLite file and uploaded-photo blobs both live under backend/.local_data/,
gitignored, created on first use. Not shared with the data/ directory, which
holds only the static JSON shipped with the repo (rules, processors, etc.).
"""
import json
import os
import sqlite3
import tempfile
import time
from pathlib import Path
from typing import Any

from app.storage.base import Storage
from app.uploads import MAX_UPLOAD_BYTES, validate_upload_key

_LOCAL_DATA_DIR = Path(__file__).resolve().parent.parent.parent / ".local_data"
_DB_PATH = _LOCAL_DATA_DIR / "loopback.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS waste_streams (
    stream_id TEXT PRIMARY KEY,
    data TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS cache (
    image_sha TEXT PRIMARY KEY,
    characterization TEXT NOT NULL,
    created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS ledger (
    chain_id TEXT NOT NULL,
    link_no INTEGER NOT NULL,
    event TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    prev_hash TEXT NOT NULL,
    entry_hash TEXT NOT NULL,
    ts TEXT NOT NULL,
    hash_version INTEGER NOT NULL DEFAULT 2,
    PRIMARY KEY (chain_id, link_no)
);
"""


class LocalStorage(Storage):
    def __init__(self, db_path: Path = _DB_PATH, uploads_dir: Path | None = None):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)  # agent tools run on worker threads; agent.py serialises them
        self._conn.executescript(_SCHEMA)
        if "hash_version" not in {r[1] for r in self._conn.execute("PRAGMA table_info(ledger)")}:
            self._conn.execute("ALTER TABLE ledger ADD COLUMN hash_version INTEGER NOT NULL DEFAULT 1")
        self._conn.commit()
        self.uploads_dir = uploads_dir or (self.db_path.parent / "uploads")
        self.uploads_dir.mkdir(parents=True, exist_ok=True)

    def save_upload(self, key: str, data: bytes) -> None:
        path = self._upload_path(key)
        if not data or len(data) > MAX_UPLOAD_BYTES:
            raise ValueError("invalid upload size")
        path.parent.mkdir(parents=True, exist_ok=True)
        # Publish a complete file atomically, with no window for replacing an
        # existing key or reading a partially written photo.
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".upload-", delete=False) as photo:
                temporary = Path(photo.name)
                photo.write(data)
            os.link(temporary, path)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)

    def read_upload(self, key: str) -> bytes:
        return self._upload_path(key).read_bytes()

    def _upload_path(self, key: str) -> Path:
        validate_upload_key(key)
        path = (self.uploads_dir / key).resolve()
        if not path.is_relative_to(self.uploads_dir.resolve()):
            raise ValueError("photo key escapes upload directory")
        return path

    def create_stream(self, stream_id: str, data: dict[str, Any]) -> None:
        self._conn.execute(
            "INSERT INTO waste_streams (stream_id, data) VALUES (?, ?)",
            (stream_id, json.dumps(data)),
        )
        self._conn.commit()

    def get_stream(self, stream_id: str) -> dict[str, Any] | None:
        row = self._conn.execute(
            "SELECT data FROM waste_streams WHERE stream_id = ?", (stream_id,)
        ).fetchone()
        return json.loads(row[0]) if row else None

    def update_stream(self, stream_id: str, **fields: Any) -> None:
        current = self.get_stream(stream_id)
        if current is None:
            raise KeyError(f"no such stream: {stream_id}")
        current.update(fields)
        self._conn.execute(
            "UPDATE waste_streams SET data = ? WHERE stream_id = ?",
            (json.dumps(current), stream_id),
        )
        self._conn.commit()

    def list_streams_by_org(self, org_id: str) -> list[dict[str, Any]]:
        rows = self._conn.execute("SELECT stream_id, data FROM waste_streams").fetchall()
        result = []
        for stream_id, data_json in rows:
            data = json.loads(data_json)
            if data.get("org_id") == org_id:
                result.append({"stream_id": stream_id, **data})
        return result

    def tamper_ledger_entry_for_demo(self, chain_id: str, link_no: int) -> bool:
        cursor = self._conn.execute(
            "UPDATE ledger SET payload_json = ? WHERE chain_id = ? AND link_no = ?",
            (json.dumps({"tampered_by": "demo tool", "at": time.time()}), chain_id, link_no),
        )
        self._conn.commit()
        return cursor.rowcount > 0

    def get_cached_characterization(self, image_sha: str) -> dict[str, Any] | None:
        row = self._conn.execute(
            "SELECT characterization FROM cache WHERE image_sha = ?", (image_sha,)
        ).fetchone()
        return json.loads(row[0]) if row else None

    def set_cached_characterization(self, image_sha: str, characterization: dict[str, Any]) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO cache (image_sha, characterization, created_at) VALUES (?, ?, ?)",
            (image_sha, json.dumps(characterization), time.time()),
        )
        self._conn.commit()

    def get_ledger_head(self, chain_id: str) -> dict[str, Any] | None:
        row = self._conn.execute(
            "SELECT chain_id, link_no, event, payload_json, prev_hash, entry_hash, ts, hash_version "
            "FROM ledger WHERE chain_id = ? ORDER BY link_no DESC LIMIT 1",
            (chain_id,),
        ).fetchone()
        return self._row_to_entry(row) if row else None

    def append_ledger_entry(self, entry: dict[str, Any]) -> bool:
        try:
            self._conn.execute(
                "INSERT INTO ledger (chain_id, link_no, event, payload_json, prev_hash, entry_hash, ts, hash_version) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    entry["chain_id"], entry["link_no"], entry["event"],
                    entry["payload_json"], entry["prev_hash"], entry["entry_hash"], entry["ts"], entry["hash_version"],
                ),
            )
            self._conn.commit()
            return True
        except sqlite3.IntegrityError:
            self._conn.rollback()
            return False

    def get_ledger_chain(self, chain_id: str) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT chain_id, link_no, event, payload_json, prev_hash, entry_hash, ts, hash_version "
            "FROM ledger WHERE chain_id = ? ORDER BY link_no ASC",
            (chain_id,),
        ).fetchall()
        return [self._row_to_entry(row) for row in rows]

    @staticmethod
    def _row_to_entry(row) -> dict[str, Any]:
        return {
            "chain_id": row[0], "link_no": row[1], "event": row[2],
            "payload_json": row[3], "prev_hash": row[4], "entry_hash": row[5], "ts": row[6], "hash_version": row[7],
        }
