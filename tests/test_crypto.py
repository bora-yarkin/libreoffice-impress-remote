# SPDX-FileCopyrightText: 2026 Bora Yarkın
# SPDX-License-Identifier: GPL-3.0-only

import pytest

from impress_remote.crypto import (
    aes_gcm_decrypt,
    aes_gcm_encrypt,
    base64url_decode,
    base64url_encode,
    hkdf_sha256,
    p256_generate_private_key,
    p256_public_key,
    p256_shared_secret,
    random_token,
)


def test_random_token_is_urlsafe() -> None:
    token = random_token()
    assert token
    assert "=" not in token


def test_hkdf_is_deterministic() -> None:
    first = hkdf_sha256(b"secret", b"salt", b"info")
    second = hkdf_sha256(b"secret", b"salt", b"info")
    assert first == second
    assert len(first) == 32


def test_base64url_round_trip_preserves_binary_data() -> None:
    payload = bytes(range(32))

    encoded = base64url_encode(payload)

    assert base64url_decode(encoded) == payload


def test_p256_ecdh_shared_secret_matches_between_peers() -> None:
    left_private = p256_generate_private_key()
    right_private = p256_generate_private_key()
    left_public = p256_public_key(left_private)
    right_public = p256_public_key(right_private)

    assert left_public[0] == 0x04
    assert right_public[0] == 0x04
    assert len(left_public) == 65
    assert p256_shared_secret(left_private, right_public) == p256_shared_secret(
        right_private,
        left_public,
    )


def test_aes_gcm_matches_known_nist_vector() -> None:
    key = bytes.fromhex("00000000000000000000000000000000")
    nonce = bytes.fromhex("000000000000000000000000")
    plaintext = bytes.fromhex("00000000000000000000000000000000")

    ciphertext, tag = aes_gcm_encrypt(key, nonce, plaintext)

    assert ciphertext.hex() == "0388dace60b6a392f328c2b971b2fe78"
    assert tag.hex() == "ab6e47d42cec13bdf53a67b21257bddf"
    assert aes_gcm_decrypt(key, nonce, ciphertext, tag) == plaintext


def test_aes_gcm_rejects_tampered_tags() -> None:
    key = bytes.fromhex("00000000000000000000000000000000")
    nonce = bytes.fromhex("000000000000000000000000")
    ciphertext, tag = aes_gcm_encrypt(key, nonce, b"hello")

    tampered = bytearray(tag)
    tampered[-1] ^= 0x01

    with pytest.raises(ValueError):
        aes_gcm_decrypt(key, nonce, ciphertext, bytes(tampered))
