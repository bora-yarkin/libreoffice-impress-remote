# SPDX-FileCopyrightText: 2026 Bora Yarkın
# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from string import Formatter
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "shared" / "localizations" / "en.json"
DEFAULT_OUTPUT = ROOT / "shared" / "localizations"
LOCALE_PATTERN = re.compile(r"^[a-z]{2,3}(?:[-_][A-Za-z]{2})?$")


class LocalizationImportError(ValueError):
    pass


def normalize_locale_tag(value: str) -> str:
    candidate = value.strip().replace("_", "-")
    if not LOCALE_PATTERN.fullmatch(candidate):
        raise LocalizationImportError(f"Invalid locale tag: {value}")
    parts = candidate.split("-", 1)
    if len(parts) == 1:
        return parts[0].lower()
    return f"{parts[0].lower()}-{parts[1].upper()}"


def load_json_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise LocalizationImportError(f"{path} must contain a JSON object.")
    return payload


def load_translation_file(path: Path) -> tuple[str, dict[str, str]]:
    payload = load_json_object(path)
    if "locale" in payload and "messages" in payload:
        locale = normalize_locale_tag(str(payload["locale"]))
        messages_payload = payload["messages"]
        if not isinstance(messages_payload, dict):
            raise LocalizationImportError(f"{path}: messages must be a JSON object.")
        messages = messages_payload
    else:
        locale = normalize_locale_tag(path.stem)
        messages = payload
    return locale, {str(key): str(value) for key, value in messages.items()}


def placeholders(value: str) -> set[str]:
    names: set[str] = set()
    for _literal, field_name, _format_spec, _conversion in Formatter().parse(value):
        if field_name:
            names.add(field_name.split(".", 1)[0].split("[", 1)[0])
    return names


def validate_translation(
    *,
    source: dict[str, str],
    messages: dict[str, str],
    allow_incomplete: bool = False,
) -> None:
    source_keys = set(source)
    message_keys = set(messages)
    unknown = sorted(message_keys - source_keys)
    if unknown:
        raise LocalizationImportError(f"Unknown localization keys: {', '.join(unknown)}")
    missing = sorted(source_keys - message_keys)
    if missing and not allow_incomplete:
        raise LocalizationImportError(f"Missing localization keys: {', '.join(missing)}")
    for key, translated in messages.items():
        expected = placeholders(source[key])
        actual = placeholders(translated)
        if expected != actual:
            raise LocalizationImportError(
                f"{key}: placeholder mismatch, expected {sorted(expected)}, got {sorted(actual)}"
            )


def import_translation(
    path: Path,
    *,
    source_catalog: dict[str, str],
    output_dir: Path = DEFAULT_OUTPUT,
    allow_incomplete: bool = False,
) -> Path:
    locale, messages = load_translation_file(path)
    validate_translation(
        source=source_catalog,
        messages=messages,
        allow_incomplete=allow_incomplete,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{locale}.json"
    output_path.write_text(
        json.dumps(dict(sorted(messages.items())), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Import validated LibreOffice Impress Remote localization JSON files.",
    )
    parser.add_argument("files", nargs="+", type=Path, help="Translation JSON files to import.")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE, help="Source catalog.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Catalog output dir.",
    )
    parser.add_argument(
        "--allow-incomplete",
        action="store_true",
        help="Allow catalogs that omit keys and rely on English fallback.",
    )
    args = parser.parse_args()
    source_catalog = {str(key): str(value) for key, value in load_json_object(args.source).items()}
    for path in args.files:
        print(
            import_translation(
                path,
                source_catalog=source_catalog,
                output_dir=args.output_dir,
                allow_incomplete=args.allow_incomplete,
            )
        )


if __name__ == "__main__":
    main()
