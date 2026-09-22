"""Binary FBX record walker.

FBX is a nested record format: each record has a name, a property list, and
optional child records. This module only decodes that container into
``(name, properties)`` pairs; deciding which records matter is the reader's job.

Array properties may be zlib-deflated, which is handled here. Anything the
walker cannot decode raises rather than returning partial geometry.
"""

from __future__ import annotations

import struct
import zlib

from orthoplan.io.mesh_formats.payload import MeshParseError

MAGIC = b"Kaydara FBX Binary  \x00"
_HEADER_BYTES = 27
_SCALARS = {"Y": ("h", 2), "C": ("?", 1), "I": ("i", 4), "F": ("f", 4), "D": ("d", 8), "L": ("q", 8)}
_ARRAYS = {"f": "f", "d": "d", "l": "q", "i": "i", "b": "b"}
_MAX_INFLATED_BYTES = 512 * 1024 * 1024
_MAX_DEPTH = 32

Record = tuple[str, list]


def is_binary_fbx(raw: bytes) -> bool:
    return raw[:len(MAGIC)] == MAGIC


def read_records(raw: bytes) -> list[Record]:
    """Flatten the whole document into ``(record name, properties)`` pairs."""

    if not is_binary_fbx(raw):
        raise MeshParseError("not a binary FBX file")
    (version,) = struct.unpack_from("<I", raw, 23)
    wide = version >= 7500
    records: list[Record] = []
    _read_list(raw, _HEADER_BYTES, len(raw), wide, records, depth=0)
    return records


def _read_list(
    raw: bytes, offset: int, limit: int, wide: bool, records: list[Record], *, depth: int
) -> None:
    if depth > _MAX_DEPTH:
        raise MeshParseError("FBX record nesting is too deep to read")
    while offset < limit:
        end, offset = _read_record(raw, offset, wide, records, depth=depth)
        if end == 0:  # NULL record: end of this sibling list.
            return
        offset = end


def _read_record(
    raw: bytes, offset: int, wide: bool, records: list[Record], *, depth: int
) -> tuple[int, int]:
    width = 8 if wide else 4
    symbol = "<QQQ" if wide else "<III"
    if offset + width * 3 + 1 > len(raw):
        return 0, len(raw)
    end, property_count, property_bytes = struct.unpack_from(symbol, raw, offset)
    offset += width * 3
    (name_length,) = struct.unpack_from("<B", raw, offset)
    offset += 1
    if end == 0:
        return 0, offset
    name = raw[offset: offset + name_length].decode("utf-8", errors="replace")
    offset += name_length

    properties: list = []
    property_end = offset + property_bytes
    for _ in range(property_count):
        value, offset = _read_property(raw, offset)
        properties.append(value)
    records.append((name, properties))

    offset = property_end
    if offset < end:
        _read_list(raw, offset, min(end, len(raw)), wide, records, depth=depth + 1)
    return min(end, len(raw)), offset


def _read_property(raw: bytes, offset: int) -> tuple[object, int]:
    if offset >= len(raw):
        raise MeshParseError("FBX property list ended early")
    code = chr(raw[offset])
    offset += 1
    if code in _SCALARS:
        symbol, size = _SCALARS[code]
        (value,) = struct.unpack_from(f"<{symbol}", raw, offset)
        return value, offset + size
    if code in {"S", "R"}:
        (length,) = struct.unpack_from("<I", raw, offset)
        offset += 4
        payload = raw[offset: offset + length]
        decoded = payload.decode("utf-8", errors="replace") if code == "S" else payload
        return decoded, offset + length
    if code in _ARRAYS:
        return _read_array(raw, offset, _ARRAYS[code])
    raise MeshParseError(f"unsupported FBX property type {code!r}")


def _read_array(raw: bytes, offset: int, symbol: str) -> tuple[list, int]:
    length, encoding, compressed = struct.unpack_from("<III", raw, offset)
    offset += 12
    payload = raw[offset: offset + compressed]
    offset += compressed
    if encoding == 1:
        try:
            payload = zlib.decompressobj().decompress(payload, _MAX_INFLATED_BYTES)
        except zlib.error as exc:
            raise MeshParseError(f"FBX array could not be decompressed: {exc}") from exc
    size = struct.calcsize(f"<{symbol}")
    if len(payload) < length * size:
        raise MeshParseError("FBX array is shorter than its declared length")
    return list(struct.unpack_from(f"<{length}{symbol}", payload, 0)), offset
