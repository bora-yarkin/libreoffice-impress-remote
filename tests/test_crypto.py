# SPDX-FileCopyrightText: 2026 Bora Yarkın
# SPDX-License-Identifier: GPL-3.0-only

from impress_remote.crypto import hkdf_sha256, random_token


def test_random_token_is_urlsafe() -> None:
    token = random_token()
    assert token
    assert "=" not in token


def test_hkdf_is_deterministic() -> None:
    first = hkdf_sha256(b"secret", b"salt", b"info")
    second = hkdf_sha256(b"secret", b"salt", b"info")
    assert first == second
    assert len(first) == 32
