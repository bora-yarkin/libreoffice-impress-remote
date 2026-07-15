# SPDX-FileCopyrightText: 2026 Bora Yarkın
# SPDX-License-Identifier: GPL-3.0-only

import json
import unittest

from impress_remote.protocol import (
    decode_command_message,
    encode_command_message,
    encode_state_message,
)


class ProtocolTests(unittest.TestCase):
    def test_encode_state_message_wraps_state_payload(self) -> None:
        payload = json.loads(encode_state_message({"running": True, "slideCount": 3}))
        self.assertEqual(payload["type"], "state")
        self.assertTrue(payload["state"]["running"])

    def test_command_message_round_trip_preserves_index(self) -> None:
        command = decode_command_message(encode_command_message("goto_slide", 4))
        self.assertIsNotNone(command)
        assert command is not None
        self.assertEqual(command.command, "goto_slide")
        self.assertEqual(command.index, 4)

    def test_decode_command_message_rejects_other_message_types(self) -> None:
        self.assertIsNone(decode_command_message('{"type":"state"}'))
