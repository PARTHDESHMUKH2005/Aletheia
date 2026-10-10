"""Storage interface implemented by local.py (SQLite + disk) and aws.py (DynamoDB + S3).

Phase 1 scope: streams and the image-hash cache (what characterize.py needs).
Phase 3 scope: ledger and upload URL methods are added to this interface then,
mirroring section 4's table list (organizations/processors/rules/prices/co2 are
static JSON, loaded once -- they are not part of this interface).
"""
from abc import ABC, abstractmethod
from typing import Any


class Storage(ABC):
    @abstractmethod
    def create_stream(self, stream_id: str, data: dict[str, Any]) -> None: ...

    @abstractmethod
    def get_stream(self, stream_id: str) -> dict[str, Any] | None: ...

    @abstractmethod
    def update_stream(self, stream_id: str, **fields: Any) -> None: ...

    @abstractmethod
    def get_cached_characterization(self, image_sha: str) -> dict[str, Any] | None: ...

    @abstractmethod
    def set_cached_characterization(self, image_sha: str, characterization: dict[str, Any]) -> None: ...

    @abstractmethod
    def get_ledger_head(self, chain_id: str) -> dict[str, Any] | None:
        """Latest (highest link_no) entry for a chain, or None if the chain is empty."""
        ...

    @abstractmethod
    def append_ledger_entry(self, entry: dict[str, Any]) -> bool:
        """Inserts a ledger row if (chain_id, link_no) doesn't already exist.
        Returns True on success, False on a collision (caller should retry with a fresh head).
        """
        ...

    @abstractmethod
    def get_ledger_chain(self, chain_id: str) -> list[dict[str, Any]]:
        """All entries for a chain, ordered by link_no ascending."""
        ...

    @abstractmethod
    def save_upload(self, key: str, data: bytes) -> None: ...

    @abstractmethod
    def read_upload(self, key: str) -> bytes: ...
