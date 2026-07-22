# SPDX-FileCopyrightText: 2026 Bora Yarkın
# SPDX-License-Identifier: GPL-3.0-only

import json

import pytest

from tools.import_localizations import (
    LocalizationImportError,
    import_translation,
    normalize_locale_tag,
)


def test_normalizes_locale_tags_for_imported_catalogs() -> None:
    assert normalize_locale_tag("pt_br") == "pt-BR"
    assert normalize_locale_tag("tr") == "tr"


def test_import_translation_writes_validated_catalog(tmp_path) -> None:
    source = {
        "hello": "Hello {name}",
        "bye": "Bye",
    }
    translation = tmp_path / "de.json"
    translation.write_text(
        json.dumps({"hello": "Hallo {name}", "bye": "Tschuss"}),
        encoding="utf-8",
    )

    output = import_translation(translation, source_catalog=source, output_dir=tmp_path / "out")

    assert output.name == "de.json"
    assert json.loads(output.read_text(encoding="utf-8"))["hello"] == "Hallo {name}"


def test_import_translation_rejects_placeholder_mismatches(tmp_path) -> None:
    translation = tmp_path / "es.json"
    translation.write_text(json.dumps({"hello": "Hola {nombre}"}), encoding="utf-8")

    with pytest.raises(LocalizationImportError):
        import_translation(
            translation,
            source_catalog={"hello": "Hello {name}"},
            output_dir=tmp_path / "out",
        )
