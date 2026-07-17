# SPDX-FileCopyrightText: 2026 Bora Yarkın
# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets

_SBOX = (
    0x63, 0x7C, 0x77, 0x7B, 0xF2, 0x6B, 0x6F, 0xC5, 0x30, 0x01, 0x67, 0x2B, 0xFE, 0xD7, 0xAB,
    0x76, 0xCA, 0x82, 0xC9, 0x7D, 0xFA, 0x59, 0x47, 0xF0, 0xAD, 0xD4, 0xA2, 0xAF, 0x9C, 0xA4,
    0x72, 0xC0, 0xB7, 0xFD, 0x93, 0x26, 0x36, 0x3F, 0xF7, 0xCC, 0x34, 0xA5, 0xE5, 0xF1, 0x71,
    0xD8, 0x31, 0x15, 0x04, 0xC7, 0x23, 0xC3, 0x18, 0x96, 0x05, 0x9A, 0x07, 0x12, 0x80, 0xE2,
    0xEB, 0x27, 0xB2, 0x75, 0x09, 0x83, 0x2C, 0x1A, 0x1B, 0x6E, 0x5A, 0xA0, 0x52, 0x3B, 0xD6,
    0xB3, 0x29, 0xE3, 0x2F, 0x84, 0x53, 0xD1, 0x00, 0xED, 0x20, 0xFC, 0xB1, 0x5B, 0x6A, 0xCB,
    0xBE, 0x39, 0x4A, 0x4C, 0x58, 0xCF, 0xD0, 0xEF, 0xAA, 0xFB, 0x43, 0x4D, 0x33, 0x85, 0x45,
    0xF9, 0x02, 0x7F, 0x50, 0x3C, 0x9F, 0xA8, 0x51, 0xA3, 0x40, 0x8F, 0x92, 0x9D, 0x38, 0xF5,
    0xBC, 0xB6, 0xDA, 0x21, 0x10, 0xFF, 0xF3, 0xD2, 0xCD, 0x0C, 0x13, 0xEC, 0x5F, 0x97, 0x44,
    0x17, 0xC4, 0xA7, 0x7E, 0x3D, 0x64, 0x5D, 0x19, 0x73, 0x60, 0x81, 0x4F, 0xDC, 0x22, 0x2A,
    0x90, 0x88, 0x46, 0xEE, 0xB8, 0x14, 0xDE, 0x5E, 0x0B, 0xDB, 0xE0, 0x32, 0x3A, 0x0A, 0x49,
    0x06, 0x24, 0x5C, 0xC2, 0xD3, 0xAC, 0x62, 0x91, 0x95, 0xE4, 0x79, 0xE7, 0xC8, 0x37, 0x6D,
    0x8D, 0xD5, 0x4E, 0xA9, 0x6C, 0x56, 0xF4, 0xEA, 0x65, 0x7A, 0xAE, 0x08, 0xBA, 0x78, 0x25,
    0x2E, 0x1C, 0xA6, 0xB4, 0xC6, 0xE8, 0xDD, 0x74, 0x1F, 0x4B, 0xBD, 0x8B, 0x8A, 0x70, 0x3E,
    0xB5, 0x66, 0x48, 0x03, 0xF6, 0x0E, 0x61, 0x35, 0x57, 0xB9, 0x86, 0xC1, 0x1D, 0x9E, 0xE1,
    0xF8, 0x98, 0x11, 0x69, 0xD9, 0x8E, 0x94, 0x9B, 0x1E, 0x87, 0xE9, 0xCE, 0x55, 0x28, 0xDF,
    0x8C, 0xA1, 0x89, 0x0D, 0xBF, 0xE6, 0x42, 0x68, 0x41, 0x99, 0x2D, 0x0F, 0xB0, 0x54, 0xBB,
    0x16,
)
_RCON = (0x00, 0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80, 0x1B, 0x36)
_GCM_POLY = 0xE1000000000000000000000000000000


def random_token(bytes_len: int = 32) -> str:
    return base64url_encode(secrets.token_bytes(bytes_len))


def random_bytes(length: int) -> bytes:
    return secrets.token_bytes(length)


def base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def base64url_decode(text: str) -> bytes:
    padding = "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode(f"{text}{padding}".encode("ascii"))


def hkdf_sha256(secret: bytes, salt: bytes, info: bytes, length: int = 32) -> bytes:
    prk = hmac.new(salt, secret, hashlib.sha256).digest()
    output = b""
    block = b""
    counter = 1
    while len(output) < length:
        block = hmac.new(prk, block + info + bytes([counter]), hashlib.sha256).digest()
        output += block
        counter += 1
    return output[:length]


def aes_gcm_encrypt(
    key: bytes,
    nonce: bytes,
    plaintext: bytes,
    aad: bytes = b"",
) -> tuple[bytes, bytes]:
    _validate_aes_gcm_inputs(key, nonce)
    cipher = _AesCipher(key)
    h = int.from_bytes(cipher.encrypt_block(b"\0" * 16), "big")
    j0 = nonce + b"\0\0\0\1"
    ciphertext = _gctr(cipher, _inc32(j0), plaintext)
    tag = _gcm_tag(cipher, h, j0, aad, ciphertext)
    return ciphertext, tag


def aes_gcm_decrypt(
    key: bytes,
    nonce: bytes,
    ciphertext: bytes,
    tag: bytes,
    aad: bytes = b"",
) -> bytes:
    _validate_aes_gcm_inputs(key, nonce)
    if len(tag) != 16:
        raise ValueError("AES-GCM tags must be 16 bytes long.")
    cipher = _AesCipher(key)
    h = int.from_bytes(cipher.encrypt_block(b"\0" * 16), "big")
    j0 = nonce + b"\0\0\0\1"
    expected_tag = _gcm_tag(cipher, h, j0, aad, ciphertext)
    if not hmac.compare_digest(expected_tag, tag):
        raise ValueError("AES-GCM authentication failed.")
    return _gctr(cipher, _inc32(j0), ciphertext)


def _validate_aes_gcm_inputs(key: bytes, nonce: bytes) -> None:
    if len(key) not in {16, 24, 32}:
        raise ValueError("AES-GCM keys must be 16, 24, or 32 bytes long.")
    if len(nonce) != 12:
        raise ValueError("AES-GCM nonces must be 12 bytes long.")


class _AesCipher:
    def __init__(self, key: bytes):
        self._round_keys, self._rounds = _expand_key(key)

    def encrypt_block(self, block: bytes) -> bytes:
        if len(block) != 16:
            raise ValueError("AES blocks must be 16 bytes long.")
        state = list(block)
        _add_round_key(state, self._round_keys[0:16])
        for round_index in range(1, self._rounds):
            _sub_bytes(state)
            _shift_rows(state)
            _mix_columns(state)
            offset = round_index * 16
            _add_round_key(state, self._round_keys[offset : offset + 16])
        _sub_bytes(state)
        _shift_rows(state)
        final_offset = self._rounds * 16
        _add_round_key(state, self._round_keys[final_offset : final_offset + 16])
        return bytes(state)


def _expand_key(key: bytes) -> tuple[bytes, int]:
    nk = len(key) // 4
    nr = nk + 6
    words = [int.from_bytes(key[index : index + 4], "big") for index in range(0, len(key), 4)]
    total_words = 4 * (nr + 1)
    for index in range(nk, total_words):
        temp = words[index - 1]
        if index % nk == 0:
            temp = _sub_word(_rot_word(temp)) ^ (_RCON[index // nk] << 24)
        elif nk > 6 and index % nk == 4:
            temp = _sub_word(temp)
        words.append(words[index - nk] ^ temp)
    return b"".join(word.to_bytes(4, "big") for word in words), nr


def _rot_word(word: int) -> int:
    return ((word << 8) & 0xFFFFFFFF) | (word >> 24)


def _sub_word(word: int) -> int:
    return (
        (_SBOX[(word >> 24) & 0xFF] << 24)
        | (_SBOX[(word >> 16) & 0xFF] << 16)
        | (_SBOX[(word >> 8) & 0xFF] << 8)
        | _SBOX[word & 0xFF]
    )


def _add_round_key(state: list[int], round_key: bytes) -> None:
    for index, key_byte in enumerate(round_key):
        state[index] ^= key_byte


def _sub_bytes(state: list[int]) -> None:
    for index, value in enumerate(state):
        state[index] = _SBOX[value]


def _shift_rows(state: list[int]) -> None:
    state[1], state[5], state[9], state[13] = state[5], state[9], state[13], state[1]
    state[2], state[6], state[10], state[14] = state[10], state[14], state[2], state[6]
    state[3], state[7], state[11], state[15] = state[15], state[3], state[7], state[11]


def _xtime(value: int) -> int:
    doubled = (value << 1) & 0xFF
    if value & 0x80:
        doubled ^= 0x1B
    return doubled


def _mix_columns(state: list[int]) -> None:
    for offset in range(0, 16, 4):
        a0, a1, a2, a3 = state[offset : offset + 4]
        mix = a0 ^ a1 ^ a2 ^ a3
        state[offset + 0] = a0 ^ mix ^ _xtime(a0 ^ a1)
        state[offset + 1] = a1 ^ mix ^ _xtime(a1 ^ a2)
        state[offset + 2] = a2 ^ mix ^ _xtime(a2 ^ a3)
        state[offset + 3] = a3 ^ mix ^ _xtime(a3 ^ a0)


def _gctr(cipher: _AesCipher, counter_block: bytes, data: bytes) -> bytes:
    if not data:
        return b""
    counter = counter_block
    output = bytearray()
    for offset in range(0, len(data), 16):
        block = data[offset : offset + 16]
        keystream = cipher.encrypt_block(counter)
        output.extend(left ^ right for left, right in zip(block, keystream))
        counter = _inc32(counter)
    return bytes(output)


def _inc32(counter_block: bytes) -> bytes:
    counter = bytearray(counter_block)
    value = (int.from_bytes(counter[-4:], "big") + 1) & 0xFFFFFFFF
    counter[-4:] = value.to_bytes(4, "big")
    return bytes(counter)


def _gcm_tag(
    cipher: _AesCipher,
    hash_subkey: int,
    j0: bytes,
    aad: bytes,
    ciphertext: bytes,
) -> bytes:
    ghash_input = b"".join(
        (
            _pad16(aad),
            _pad16(ciphertext),
            (len(aad) * 8).to_bytes(8, "big"),
            (len(ciphertext) * 8).to_bytes(8, "big"),
        )
    )
    auth = _ghash(hash_subkey, ghash_input)
    tag_mask = cipher.encrypt_block(j0)
    tag = int.from_bytes(tag_mask, "big") ^ auth
    return tag.to_bytes(16, "big")


def _pad16(data: bytes) -> bytes:
    if not data:
        return b""
    remainder = len(data) % 16
    if remainder == 0:
        return data
    return data + (b"\0" * (16 - remainder))


def _ghash(hash_subkey: int, data: bytes) -> int:
    value = 0
    for offset in range(0, len(data), 16):
        block = int.from_bytes(data[offset : offset + 16], "big")
        value = _gf128_multiply(value ^ block, hash_subkey)
    return value


def _gf128_multiply(left: int, right: int) -> int:
    result = 0
    value = right
    for bit_index in range(128):
        if (left >> (127 - bit_index)) & 1:
            result ^= value
        if value & 1:
            value = (value >> 1) ^ _GCM_POLY
        else:
            value >>= 1
    return result
