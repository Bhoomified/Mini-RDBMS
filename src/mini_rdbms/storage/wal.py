"""Small binary write-ahead log with redo recovery records."""

from __future__ import annotations

import os
import struct
import zlib

from mini_rdbms.common.errors import RecoveryError, StorageError

MAGIC = b"MRWL"
BEGIN = 0
PAGE_IMAGE = 1
COMMIT = 2
HEADER = ">4sQBIQI"
HEADER_SIZE = struct.calcsize(HEADER)


class WriteAheadLog:
    """Append structured transaction records and recover committed payloads."""

    def __init__(self, path: str) -> None:
        self.path = path
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)

    def append(
        self,
        transaction_id: int,
        record_type: int,
        payload: bytes,
        page_id: int = 0,
    ) -> None:
        checksum = zlib.crc32(payload)
        record = (
            struct.pack(
                HEADER, MAGIC, transaction_id, record_type, page_id, len(payload), checksum
            )
            + payload
        )
        with open(self.path, "ab") as file:
            file.write(record)
            file.flush()
            os.fsync(file.fileno())

    def recover(self) -> list[tuple[int, bytes]]:
        """Return payloads from transactions with a durable COMMIT record."""
        return [
            (transaction_id, payload)
            for transaction_id, _page_id, payload in self.recover_pages()
        ]

    def recover_pages(self) -> list[tuple[int, int, bytes]]:
        """Return committed page images with transaction and page IDs."""
        if not os.path.exists(self.path):
            return []
        pending: dict[int, list[tuple[int, bytes]]] = {}
        committed: set[int] = set()
        try:
            with open(self.path, "rb") as file:
                while True:
                    header = file.read(HEADER_SIZE)
                    if not header:
                        break
                    if len(header) != HEADER_SIZE:
                        break
                    magic, transaction_id, record_type, page_id, length, checksum = struct.unpack(
                        HEADER, header
                    )
                    if (
                        magic != MAGIC
                        or record_type not in {BEGIN, PAGE_IMAGE, COMMIT}
                        or length > 128 * 1024 * 1024
                    ):
                        raise RecoveryError("invalid WAL record header")
                    payload = file.read(length)
                    if len(payload) != length:
                        break
                    if zlib.crc32(payload) != checksum:
                        raise RecoveryError("invalid WAL record checksum")
                    if record_type == PAGE_IMAGE:
                        pending.setdefault(transaction_id, []).append((page_id, payload))
                    elif record_type == COMMIT:
                        committed.add(transaction_id)
        except OSError as error:
            raise RecoveryError("unable to read WAL") from error
        return [
            (transaction_id, page_id, payload)
            for transaction_id in committed
            for page_id, payload in pending.get(transaction_id, [])
        ]

    def clear(self) -> None:
        with open(self.path, "wb"):
            pass
