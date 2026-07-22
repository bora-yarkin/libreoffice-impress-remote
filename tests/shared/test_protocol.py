# SPDX-FileCopyrightText: 2026 Bora Yarkın
# SPDX-License-Identifier: GPL-3.0-only

import json
import unittest

from impress_remote.protocol import (
    RelayProtocolFailure,
    SecureRelayCodec,
    decode_command_payload,
    decode_error_message,
    decode_hello_message,
    decode_command_message,
    encode_error_message,
    encode_hello_message,
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

    def test_hello_message_round_trip_preserves_key_metadata(self) -> None:
        plugin = SecureRelayCodec(
            role="plugin",
            session_id="demo",
            pairing_secret="6o2T5h1XXg3YbqfQ9F0P9v38dGrBvM8UuB8jv3j1fKQ",
        )
        raw = encode_hello_message(plugin.rotate_send_key())

        decoded = decode_hello_message(raw)

        self.assertIsNotNone(decoded)
        assert decoded is not None
        self.assertEqual(decoded.session_id, "demo")
        self.assertEqual(decoded.sender_role, "plugin")
        self.assertTrue(decoded.key_id)
        self.assertTrue(decoded.plugin_nonce)
        self.assertTrue(decoded.public_key)

    def test_error_message_round_trip_preserves_code_and_text(self) -> None:
        decoded = decode_error_message(encode_error_message("bad-frame", "Nope", "demo"))

        self.assertIsNotNone(decoded)
        assert decoded is not None
        self.assertEqual(decoded.code, "bad-frame")
        self.assertEqual(decoded.message, "Nope")
        self.assertEqual(decoded.session_id, "demo")

    def test_secure_codec_encrypts_state_and_commands_between_phone_and_plugin(self) -> None:
        pairing_secret = "6o2T5h1XXg3YbqfQ9F0P9v38dGrBvM8UuB8jv3j1fKQ"
        plugin = SecureRelayCodec(role="plugin", session_id="demo", pairing_secret=pairing_secret)
        phone = SecureRelayCodec(role="phone", session_id="demo", pairing_secret=pairing_secret)

        hello = plugin.rotate_send_key()
        phone_hello = phone.apply_hello(hello)
        self.assertIsNotNone(phone_hello)
        assert phone_hello is not None
        plugin.apply_hello(phone_hello)

        encoded_state = plugin.encode_state_frame({"running": True, "slideCount": 7})
        decoded_state = phone.decode_frame(encoded_state)

        self.assertIsNotNone(decoded_state)
        assert decoded_state is not None
        self.assertEqual(decoded_state.kind, "state")
        self.assertTrue(decoded_state.payload["running"])
        self.assertEqual(decoded_state.payload["slideCount"], 7)

        encoded_command = phone.encode_command_frame("goto_slide", 4)
        decoded_command = plugin.decode_frame(encoded_command)

        self.assertIsNotNone(decoded_command)
        assert decoded_command is not None
        command = decode_command_payload(decoded_command.payload)
        self.assertIsNotNone(command)
        assert command is not None
        self.assertEqual(command.command, "goto_slide")
        self.assertEqual(command.index, 4)

    def test_secure_codec_encrypts_asset_frames_between_plugin_and_phone(self) -> None:
        pairing_secret = "6o2T5h1XXg3YbqfQ9F0P9v38dGrBvM8UuB8jv3j1fKQ"
        plugin = SecureRelayCodec(role="plugin", session_id="demo", pairing_secret=pairing_secret)
        phone = SecureRelayCodec(role="phone", session_id="demo", pairing_secret=pairing_secret)

        phone_hello = phone.apply_hello(plugin.rotate_send_key())
        assert phone_hello is not None
        plugin.apply_hello(phone_hello)
        encoded_asset = plugin.encode_asset_frame(
            {
                "contentType": "image/png",
                "encoding": "base64url",
                "data": "abcd",
                "slot": "current",
            }
        )

        decoded_asset = phone.decode_frame(encoded_asset)

        self.assertIsNotNone(decoded_asset)
        assert decoded_asset is not None
        self.assertEqual(decoded_asset.kind, "asset")
        self.assertEqual(decoded_asset.payload["contentType"], "image/png")
        self.assertEqual(decoded_asset.payload["slot"], "current")

    def test_secure_codec_rejects_replayed_frames(self) -> None:
        pairing_secret = "6o2T5h1XXg3YbqfQ9F0P9v38dGrBvM8UuB8jv3j1fKQ"
        plugin = SecureRelayCodec(role="plugin", session_id="demo", pairing_secret=pairing_secret)
        phone = SecureRelayCodec(role="phone", session_id="demo", pairing_secret=pairing_secret)

        phone_hello = phone.apply_hello(plugin.rotate_send_key())
        assert phone_hello is not None
        plugin.apply_hello(phone_hello)
        encoded_state = plugin.encode_state_frame({"running": True})
        self.assertIsNotNone(phone.decode_frame(encoded_state))

        with self.assertRaises(RelayProtocolFailure):
            phone.decode_frame(encoded_state)

    def test_plugin_keeps_previous_receive_keys_during_rotation(self) -> None:
        pairing_secret = "6o2T5h1XXg3YbqfQ9F0P9v38dGrBvM8UuB8jv3j1fKQ"
        plugin = SecureRelayCodec(role="plugin", session_id="demo", pairing_secret=pairing_secret)
        phone = SecureRelayCodec(role="phone", session_id="demo", pairing_secret=pairing_secret)

        first = plugin.rotate_send_key()
        first_phone_hello = phone.apply_hello(first)
        assert first_phone_hello is not None
        plugin.apply_hello(first_phone_hello)
        old_command = phone.encode_command_frame("next_slide")

        second = plugin.rotate_send_key()
        second_phone_hello = phone.apply_hello(second)
        assert second_phone_hello is not None
        plugin.apply_hello(second_phone_hello)

        decoded = plugin.decode_frame(old_command)

        self.assertIsNotNone(decoded)
        assert decoded is not None
        command = decode_command_payload(decoded.payload)
        self.assertIsNotNone(command)
        assert command is not None
        self.assertEqual(command.command, "next_slide")

    def test_plugin_cannot_encrypt_before_phone_ecdh_response(self) -> None:
        pairing_secret = "6o2T5h1XXg3YbqfQ9F0P9v38dGrBvM8UuB8jv3j1fKQ"
        plugin = SecureRelayCodec(role="plugin", session_id="demo", pairing_secret=pairing_secret)

        plugin.rotate_send_key()

        with self.assertRaises(RelayProtocolFailure):
            plugin.encode_state_frame({"running": True})
