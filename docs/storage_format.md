# Storage format

The durable file is made of 4096-byte pages. Page zero is a database
superblock containing `MRDP`, a format version, payload length, and SHA-256
checksum. Following pages contain the binary payload. The payload contains
table schemas, fixed-size slotted-page images, RID-to-page/slot mappings, and
index definitions.

Integer and floating values use big-endian `struct` encodings. Text uses a
32-bit UTF-8 byte length followed by bytes. NULL, boolean, integer, float, and
text values have explicit one-byte type markers.

The standalone page format uses 4096-byte pages. Page headers contain a magic
identifier, page ID, slot count, free-space boundaries, and a slot directory.
The standalone `RecordCodec` and `SlottedPage` components do not use JSON or
pickle.

The WAL uses records with a magic identifier, transaction ID, record type,
page ID, payload length, payload, and CRC32 checksum. Supported record types
are `BEGIN`, `PAGE_IMAGE`, and `COMMIT`. Recovery returns page images only for
transactions with a durable commit record and ignores an incomplete final
record. Replay is idempotent at the database-image level; this is not full
ARIES recovery.
