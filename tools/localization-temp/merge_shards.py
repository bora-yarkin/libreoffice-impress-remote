import json
import shutil
import zipfile
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import generate_locales as g

ROOT = Path.cwd()
SOURCE_PATH = ROOT / "shared/localizations/en.json"
SHARDS = ROOT / "merged-shards"
BUILD = ROOT / "localization-build"
PACKAGE = BUILD / "libreoffice-impress-remote-locales"
LOCALES_DIR = PACKAGE / "locales"


def main():
    source = json.loads(SOURCE_PATH.read_text(encoding="utf-8"))
    keys = list(source)
    shutil.rmtree(BUILD, ignore_errors=True)
    LOCALES_DIR.mkdir(parents=True)

    metadata = {}
    for locale, language in g.LOCALES.items():
        source_file = SHARDS / "locales" / f"{locale}.json"
        metadata_file = SHARDS / "metadata" / f"{locale}.json"
        if not source_file.exists() or not metadata_file.exists():
            raise RuntimeError(f"Missing shard output for {locale}")
        data = json.loads(source_file.read_text(encoding="utf-8"))
        item = json.loads(metadata_file.read_text(encoding="utf-8"))
        if list(data) != keys:
            raise RuntimeError(f"Key mismatch: {locale}")
        if any(g.placeholder_signature(data[key]) != g.placeholder_signature(source[key]) for key in keys):
            raise RuntimeError(f"Placeholder mismatch: {locale}")
        if any(not str(data[key]).strip() for key in keys):
            raise RuntimeError(f"Empty value: {locale}")
        if item.get("language") != language:
            raise RuntimeError(f"Metadata mismatch: {locale}")
        shutil.copy2(source_file, LOCALES_DIR / source_file.name)
        metadata[locale] = item

    manifest = {
        "source_locale": "en-US",
        "locale_count": len(g.LOCALES),
        "string_count_per_locale": len(keys),
        "locales": [
            {"locale": code, "language": name, "file": f"locales/{code}.json"}
            for code, name in g.LOCALES.items()
        ],
    }
    qa = {
        "summary": {
            "locale_count": len(g.LOCALES),
            "string_count_per_locale": len(keys),
            "all_json_valid": True,
            "all_keys_match": all(item["keys_match"] for item in metadata.values()),
            "all_placeholders_valid": all(item["placeholders_ok"] for item in metadata.values()),
            "all_values_nonempty": all(item["empty_count"] == 0 for item in metadata.values()),
            "machine_generated_locale_count": sum(
                item["method"] not in {"source-copy", "human-corrected-existing-translation"}
                for item in metadata.values()
            ),
            "related_language_or_english_fallback_locales": [
                code for code, item in metadata.items()
                if item["method"] in {"related-language-machine-draft", "english-fallback"}
            ],
            "locales_with_per_string_source_fallbacks": [
                code for code, item in metadata.items() if item["source_fallback_count"]
            ],
        },
        "locales": metadata,
    }
    g.write_json(PACKAGE / "manifest.json", manifest)
    g.write_json(PACKAGE / "QA_REPORT.json", qa)
    readme = f"""# LibreOffice Impress Remote localizations

This package contains {len(g.LOCALES)} LibreOffice UI locale variants with {len(keys)} JSON strings per locale.

## Contents

- `locales/*.json`: one UTF-8 JSON file per locale code
- `manifest.json`: locale names and file paths
- `QA_REPORT.json`: generation method and automated validation results per locale

## Validation

Every locale file was parsed as JSON and checked for exact key order, key count, non-empty values, and exact preservation of every `{{placeholder}}` token from the English source.

## Translation status

- `en-GB`, `en-US`, and `en-ZA` are exact copies of the English base.
- `tr.json` is the existing Turkish translation with Turkish characters and orthography corrected.
- Other locales are machine-generated drafts. Native-speaker review is required before release.
- `QA_REPORT.json` identifies the method, source-language fallback count, and related-language fallbacks.
- Product names, protocol identifiers, code paths, placeholders, and cryptographic terms were protected during translation.

The English source remains authoritative for keys and runtime placeholders.
"""
    (PACKAGE / "README.md").write_text(readme, encoding="utf-8")

    zip_path = BUILD / "libreoffice-impress-remote-locales.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(PACKAGE.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(BUILD))
    print(zip_path)


if __name__ == "__main__":
    main()
