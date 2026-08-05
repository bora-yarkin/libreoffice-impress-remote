# SPDX-FileCopyrightText: 2011 Lincoln Loop
# SPDX-License-Identifier: BSD-3-Clause

from __future__ import annotations

from localization import translate


_MODE_BYTE = 0b0100
_ERROR_CORRECTION_M = 0
_PAD_BYTES = (0xEC, 0x11)
_FORMAT_GENERATOR = 0x537
_FORMAT_MASK = 0x5412
_VERSION_GENERATOR = 0x1F25
_ERROR_CORRECTION_CODEWORDS = (
    10,
    16,
    26,
    18,
    24,
    16,
    18,
    22,
    22,
    26,
    30,
    22,
    22,
    24,
    24,
    28,
    28,
    26,
    26,
    26,
    26,
    28,
    28,
    28,
    28,
    28,
    28,
    28,
    28,
    28,
    28,
    28,
    28,
    28,
    28,
    28,
    28,
    28,
    28,
    28,
)
_ERROR_CORRECTION_BLOCKS = (
    1,
    1,
    1,
    2,
    2,
    4,
    4,
    4,
    5,
    5,
    5,
    8,
    9,
    9,
    10,
    10,
    11,
    13,
    14,
    16,
    17,
    17,
    18,
    20,
    21,
    23,
    25,
    26,
    28,
    29,
    31,
    33,
    35,
    37,
    38,
    40,
    43,
    45,
    47,
    49,
)


def make_qr_matrix(payload: str, border: int = 4) -> list[list[bool]]:
    if border < 0:
        raise ValueError("QR border must not be negative.")

    data = payload.encode("utf-8")
    for version in range(1, 41):
        try:
            codewords = _make_data_codewords(version, data)
        except ValueError:
            continue
        matrix = _draw_matrix(version, codewords)
        if not border:
            return matrix
        width = len(matrix) + border * 2
        framed = [[False] * width for _ in range(border)]
        framed.extend([False] * border + row + [False] * border for row in matrix)
        framed.extend([[False] * width for _ in range(border)])
        return framed

    raise ValueError(translate("qrcode.error.codeLengthOverflow", size=len(data), available=2331))


def _make_data_codewords(version: int, data: bytes) -> list[int]:
    blocks = _error_correction_blocks(version)
    bit_limit = sum(data_count * 8 for _total_count, data_count in blocks)
    length_bits = 8 if version < 10 else 16
    if len(data) >= 1 << length_bits:
        raise ValueError

    buffer = _BitBuffer()
    buffer.put(_MODE_BYTE, 4)
    buffer.put(len(data), length_bits)
    for byte in data:
        buffer.put(byte, 8)
    if len(buffer) > bit_limit:
        raise ValueError

    for _ in range(min(bit_limit - len(buffer), 4)):
        buffer.put_bit(False)
    while len(buffer) % 8:
        buffer.put_bit(False)
    padding_index = 0
    while len(buffer) < bit_limit:
        buffer.put(_PAD_BYTES[padding_index % 2], 8)
        padding_index += 1

    return _interleave_error_correction(buffer.bytes, blocks)


def _error_correction_blocks(version: int) -> list[tuple[int, int]]:
    raw_codewords = _raw_data_modules(version) // 8
    block_count = _ERROR_CORRECTION_BLOCKS[version - 1]
    error_count = _ERROR_CORRECTION_CODEWORDS[version - 1]
    short_block_count = block_count - raw_codewords % block_count
    short_block_length = raw_codewords // block_count
    short_data_count = short_block_length - error_count
    return [(short_block_length, short_data_count) for _ in range(short_block_count)] + [
        (short_block_length + 1, short_data_count + 1)
        for _ in range(block_count - short_block_count)
    ]


def _interleave_error_correction(data: list[int], blocks: list[tuple[int, int]]) -> list[int]:
    data_blocks: list[list[int]] = []
    error_blocks: list[list[int]] = []
    offset = 0
    for total_count, data_count in blocks:
        current_data = data[offset : offset + data_count]
        offset += data_count
        data_blocks.append(current_data)
        error_blocks.append(_reed_solomon_remainder(current_data, total_count - data_count))

    interleaved: list[int] = []
    for index in range(max(len(block) for block in data_blocks)):
        interleaved.extend(block[index] for block in data_blocks if index < len(block))
    for index in range(max(len(block) for block in error_blocks)):
        interleaved.extend(block[index] for block in error_blocks if index < len(block))
    return interleaved


def _reed_solomon_remainder(data: list[int], degree: int) -> list[int]:
    divisor = [1]
    for exponent in range(degree):
        next_divisor = [0] * (len(divisor) + 1)
        factor = _gf_pow(exponent)
        for index, coefficient in enumerate(divisor):
            next_divisor[index] ^= coefficient
            next_divisor[index + 1] ^= _gf_multiply(coefficient, factor)
        divisor = next_divisor

    remainder = [0] * degree
    for byte in data:
        factor = byte ^ remainder.pop(0)
        remainder.append(0)
        for index in range(degree):
            remainder[index] ^= _gf_multiply(divisor[index + 1], factor)
    return remainder


def _draw_matrix(version: int, codewords: list[int]) -> list[list[bool]]:
    best_mask = 0
    best_penalty: int | None = None
    for mask in range(8):
        modules = _draw_function_patterns(version)
        _draw_format_bits(modules, mask, test=True)
        if version >= 7:
            _draw_version_bits(modules, version, test=True)
        _draw_codewords(modules, codewords, mask)
        penalty = _penalty_score(modules)
        if best_penalty is None or penalty < best_penalty:
            best_mask = mask
            best_penalty = penalty

    modules = _draw_function_patterns(version)
    _draw_format_bits(modules, best_mask, test=False)
    if version >= 7:
        _draw_version_bits(modules, version, test=False)
    _draw_codewords(modules, codewords, best_mask)
    return [[bool(cell) for cell in row] for row in modules]


def _draw_function_patterns(version: int) -> list[list[bool | None]]:
    size = version * 4 + 17
    modules: list[list[bool | None]] = [[None] * size for _ in range(size)]
    _draw_finder_pattern(modules, 0, 0)
    _draw_finder_pattern(modules, size - 7, 0)
    _draw_finder_pattern(modules, 0, size - 7)
    _draw_alignment_patterns(modules, version)
    _draw_timing_patterns(modules)
    return modules


def _draw_finder_pattern(modules: list[list[bool | None]], row: int, col: int) -> None:
    size = len(modules)
    for row_offset in range(-1, 8):
        target_row = row + row_offset
        if not 0 <= target_row < size:
            continue
        for col_offset in range(-1, 8):
            target_col = col + col_offset
            if not 0 <= target_col < size:
                continue
            modules[target_row][target_col] = (
                (0 <= row_offset <= 6 and col_offset in {0, 6})
                or (0 <= col_offset <= 6 and row_offset in {0, 6})
                or (2 <= row_offset <= 4 and 2 <= col_offset <= 4)
            )


def _draw_alignment_patterns(modules: list[list[bool | None]], version: int) -> None:
    positions = _alignment_pattern_positions(version)
    for row in positions:
        for col in positions:
            if modules[row][col] is not None:
                continue
            for row_offset in range(-2, 3):
                for col_offset in range(-2, 3):
                    modules[row + row_offset][col + col_offset] = (
                        row_offset in {-2, 2}
                        or col_offset in {-2, 2}
                        or (row_offset == 0 and col_offset == 0)
                    )


def _alignment_pattern_positions(version: int) -> list[int]:
    if version == 1:
        return []
    count = version // 7 + 2
    size = version * 4 + 17
    step = 26 if version == 32 else ((version * 4 + count * 2 + 1) // (count * 2 - 2)) * 2
    positions = [6]
    position = size - 7
    for _ in range(count - 1):
        positions.insert(1, position)
        position -= step
    return positions


def _draw_timing_patterns(modules: list[list[bool | None]]) -> None:
    size = len(modules)
    for index in range(8, size - 8):
        if modules[index][6] is None:
            modules[index][6] = index % 2 == 0
        if modules[6][index] is None:
            modules[6][index] = index % 2 == 0


def _draw_format_bits(modules: list[list[bool | None]], mask: int, *, test: bool) -> None:
    bits = _format_bits((_ERROR_CORRECTION_M << 3) | mask)
    size = len(modules)
    for index in range(15):
        value = not test and bool((bits >> index) & 1)
        if index < 6:
            modules[index][8] = value
        elif index < 8:
            modules[index + 1][8] = value
        else:
            modules[size - 15 + index][8] = value

        if index < 8:
            modules[8][size - index - 1] = value
        elif index < 9:
            modules[8][7] = value
        else:
            modules[8][14 - index] = value
    modules[size - 8][8] = not test


def _draw_version_bits(modules: list[list[bool | None]], version: int, *, test: bool) -> None:
    bits = _version_bits(version)
    size = len(modules)
    for index in range(18):
        value = not test and bool((bits >> index) & 1)
        modules[index // 3][index % 3 + size - 11] = value
        modules[index % 3 + size - 11][index // 3] = value


def _draw_codewords(modules: list[list[bool | None]], codewords: list[int], mask: int) -> None:
    size = len(modules)
    row = size - 1
    direction = -1
    bit_index = 7
    byte_index = 0
    for col in range(size - 1, 0, -2):
        if col <= 6:
            col -= 1
        while True:
            for current_col in (col, col - 1):
                if modules[row][current_col] is not None:
                    continue
                value = False
                if byte_index < len(codewords):
                    value = bool((codewords[byte_index] >> bit_index) & 1)
                if _mask_applies(mask, row, current_col):
                    value = not value
                modules[row][current_col] = value
                bit_index -= 1
                if bit_index < 0:
                    byte_index += 1
                    bit_index = 7
            row += direction
            if not 0 <= row < size:
                row -= direction
                direction = -direction
                break


def _format_bits(data: int) -> int:
    remainder = data << 10
    while _bit_length(remainder) >= _bit_length(_FORMAT_GENERATOR):
        remainder ^= _FORMAT_GENERATOR << (_bit_length(remainder) - _bit_length(_FORMAT_GENERATOR))
    return ((data << 10) | remainder) ^ _FORMAT_MASK


def _version_bits(version: int) -> int:
    remainder = version << 12
    while _bit_length(remainder) >= _bit_length(_VERSION_GENERATOR):
        remainder ^= _VERSION_GENERATOR << (
            _bit_length(remainder) - _bit_length(_VERSION_GENERATOR)
        )
    return (version << 12) | remainder


def _bit_length(value: int) -> int:
    return value.bit_length()


def _mask_applies(mask: int, row: int, col: int) -> bool:
    if mask == 0:
        return (row + col) % 2 == 0
    if mask == 1:
        return row % 2 == 0
    if mask == 2:
        return col % 3 == 0
    if mask == 3:
        return (row + col) % 3 == 0
    if mask == 4:
        return (row // 2 + col // 3) % 2 == 0
    if mask == 5:
        return row * col % 2 + row * col % 3 == 0
    if mask == 6:
        return (row * col % 2 + row * col % 3) % 2 == 0
    return ((row * col) % 3 + (row + col) % 2) % 2 == 0


def _penalty_score(modules: list[list[bool | None]]) -> int:
    size = len(modules)
    score = 0
    run_counts = [0] * (size + 1)
    for row in modules:
        _count_runs(row, run_counts)
    for col in range(size):
        _count_runs([modules[row][col] for row in range(size)], run_counts)
    score += sum(count * (length - 2) for length, count in enumerate(run_counts) if length >= 5)

    for row in range(size - 1):
        for col in range(size - 1):
            value = modules[row][col]
            if value == modules[row + 1][col] == modules[row][col + 1] == modules[row + 1][col + 1]:
                score += 3

    for row in range(size):
        score += _finder_penalty([modules[row][col] for col in range(size)])
    for col in range(size):
        score += _finder_penalty([modules[row][col] for row in range(size)])

    dark_count = sum(bool(value) for row in modules for value in row)
    score += int(abs(dark_count * 100 / (size * size) - 50) / 5) * 10
    return score


def _count_runs(line: list[bool | None], counts: list[int]) -> None:
    previous = line[0]
    length = 0
    for value in line:
        if value == previous:
            length += 1
            continue
        if length >= 5:
            counts[length] += 1
        previous = value
        length = 1
    if length >= 5:
        counts[length] += 1


def _finder_penalty(line: list[bool | None]) -> int:
    score = 0
    for index in range(len(line) - 10):
        pattern = line[index : index + 11]
        if pattern in (
            [True, False, True, True, True, False, True, False, False, False, False],
            [False, False, False, False, True, False, True, True, True, False, True],
        ):
            score += 40
    return score


def _raw_data_modules(version: int) -> int:
    size = version * 4 + 17
    result = size * size
    result -= 8 * 8 * 3
    result -= 15 * 2 + 1
    result -= (size - 16) * 2
    if version >= 2:
        align_count = version // 7 + 2
        result -= (align_count - 1) * (align_count - 1) * 25
        result -= (align_count - 2) * 2 * 20
    if version >= 7:
        result -= 18 * 2
    return result


def _gf_multiply(left: int, right: int) -> int:
    result = 0
    while right:
        if right & 1:
            result ^= left
        left <<= 1
        if left & 0x100:
            left ^= 0x11D
        right >>= 1
    return result


def _gf_pow(exponent: int) -> int:
    value = 1
    for _ in range(exponent):
        value = _gf_multiply(value, 2)
    return value


class _BitBuffer:
    def __init__(self) -> None:
        self.bytes: list[int] = []
        self.length = 0

    def __len__(self) -> int:
        return self.length

    def put(self, value: int, length: int) -> None:
        for index in range(length):
            self.put_bit(bool((value >> (length - index - 1)) & 1))

    def put_bit(self, value: bool) -> None:
        byte_index = self.length // 8
        if len(self.bytes) <= byte_index:
            self.bytes.append(0)
        if value:
            self.bytes[byte_index] |= 0x80 >> (self.length % 8)
        self.length += 1
