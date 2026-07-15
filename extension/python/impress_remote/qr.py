# SPDX-FileCopyrightText: 2026 Bora Yarkın
# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

from binascii import crc32
from pathlib import Path
from struct import pack
import tempfile
from zlib import compress

from qrcode import QRCode, constants


def _close_document(document) -> None:
    if document is None:
        return
    try:
        document.close(True)
    except Exception:
        try:
            document.dispose()
        except Exception:
            pass


PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
PNG_BLACK = 0
PNG_WHITE = 255


def _png_chunk(chunk_type: bytes, data: bytes) -> bytes:
    return (
        pack(">I", len(data))
        + chunk_type
        + data
        + pack(">I", crc32(chunk_type + data) & 0xFFFFFFFF)
    )


def _matrix_to_png_bytes(matrix: list[list[bool]], box_size: int = 8) -> bytes:
    if not matrix or not matrix[0]:
        raise RuntimeError("QR matrix is empty.")

    size = len(matrix)
    width = size * box_size
    rows = bytearray()
    for matrix_row in matrix:
        pixel_row = bytearray()
        for cell in matrix_row:
            color = PNG_BLACK if cell else PNG_WHITE
            pixel_row.extend([color] * box_size)
        for _ in range(box_size):
            rows.append(0)
            rows.extend(pixel_row)

    ihdr = pack(">IIBBBBB", width, width, 8, 0, 0, 0, 0)
    return b"".join(
        (
            PNG_SIGNATURE,
            _png_chunk(b"IHDR", ihdr),
            _png_chunk(b"IDAT", compress(bytes(rows), level=9)),
            _png_chunk(b"IEND", b""),
        )
    )


def export_qr_png_path(_ctx, payload: str) -> Path:
    if not payload:
        raise RuntimeError("No pairing URL is available for this route.")

    temp_file = tempfile.NamedTemporaryFile(
        prefix="impress-remote-qr-",
        suffix=".png",
        delete=False,
    )
    temp_file.close()
    output_path = Path(temp_file.name)

    try:
        qr_code = QRCode(
            version=None,
            error_correction=constants.ERROR_CORRECT_M,
            box_size=8,
            border=4,
        )
        qr_code.add_data(payload)
        qr_code.make(fit=True)
        output_path.write_bytes(_matrix_to_png_bytes(qr_code.get_matrix()))
        return output_path
    except Exception:
        try:
            output_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise
