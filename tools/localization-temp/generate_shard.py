import argparse
import json
import sys
from pathlib import Path

import ctranslate2
from huggingface_hub import snapshot_download
from transformers import AutoTokenizer

sys.path.insert(0, str(Path(__file__).resolve().parent))
import generate_locales as g

ROOT = Path.cwd()
SOURCE_PATH = ROOT / "shared/localizations/en.json"
TURKISH_PATH = ROOT / "tools/localization-temp/tr_corrected.json"
OUTPUT = ROOT / "shard-output"
LOCALES_DIR = OUTPUT / "locales"
METADATA_DIR = OUTPUT / "metadata"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--index", type=int, required=True)
    parser.add_argument("--count", type=int, required=True)
    args = parser.parse_args()

    source = json.loads(SOURCE_PATH.read_text(encoding="utf-8"))
    turkish = json.loads(TURKISH_PATH.read_text(encoding="utf-8"))
    keys = list(source)
    values = list(source.values())
    if list(turkish) != keys:
        raise RuntimeError("Turkish keys do not match English keys")

    items = [(code, name) for position, (code, name) in enumerate(g.LOCALES.items()) if position % args.count == args.index]
    LOCALES_DIR.mkdir(parents=True, exist_ok=True)
    METADATA_DIR.mkdir(parents=True, exist_ok=True)

    needs_model = any(not code.startswith("en-") and code != "tr" for code, _ in items)
    tokenizer = None
    translator = None
    available = set()
    if needs_model:
        tokenizer = AutoTokenizer.from_pretrained("facebook/nllb-200-distilled-600M", src_lang="eng_Latn")
        model_path = snapshot_download("osa911/nllb-200-distilled-600M-ct2-int8")
        translator = ctranslate2.Translator(model_path, device="cpu", compute_type="int8", inter_threads=2, intra_threads=2)
        codes = set(g.NLLB.values()) | set(g.RELATED_FALLBACK.values())
        available = {code for code in codes if tokenizer.convert_tokens_to_ids(code) != tokenizer.unk_token_id}

    cache = {}
    for locale, language in items:
        if locale.startswith("en-"):
            translated = values
            method = "source-copy"
            model_language = "eng_Latn"
            fallback_count = 0
        elif locale == "tr":
            translated = list(turkish.values())
            method = "human-corrected-existing-translation"
            model_language = "tur_Latn"
            fallback_count = 0
        elif locale == "sr-Latn":
            code = "srp_Cyrl"
            if code not in cache:
                cache[code] = g.nllb_translate(values, code, tokenizer, translator)
            cyrillic, fallback_count = cache[code]
            translated = [g.transliterate_serbian(value) for value in cyrillic]
            method = "nllb-plus-script-transliteration"
            model_language = code
        else:
            desired = g.NLLB.get(locale)
            if desired and desired in available:
                if desired not in cache:
                    cache[desired] = g.nllb_translate(values, desired, tokenizer, translator)
                translated, fallback_count = cache[desired]
                method = "nllb-200-int8"
                model_language = desired
            else:
                google_code = g.GOOGLE.get(locale)
                google_values = None
                google_failures = list(range(len(values)))
                if google_code:
                    try:
                        google_values, google_failures = g.google_translate(values, google_code)
                    except Exception:
                        google_values = None
                if google_values is not None and len(google_failures) < len(values) // 4:
                    translated = google_values
                    fallback_count = len(google_failures)
                    method = "google-web-translation-fallback"
                    model_language = google_code
                else:
                    related = g.RELATED_FALLBACK.get(locale, "eng_Latn")
                    if related in available:
                        if related not in cache:
                            cache[related] = g.nllb_translate(values, related, tokenizer, translator)
                        translated, fallback_count = cache[related]
                        method = "related-language-machine-draft"
                        model_language = related
                    else:
                        translated = values
                        fallback_count = len(values)
                        method = "english-fallback"
                        model_language = "eng_Latn"

        data = dict(zip(keys, translated))
        g.write_json(LOCALES_DIR / f"{locale}.json", data)
        placeholder_errors = [key for key in keys if g.placeholder_signature(data[key]) != g.placeholder_signature(source[key])]
        metadata = {
            "locale": locale,
            "language": language,
            "file": f"locales/{locale}.json",
            "method": method,
            "model_language": model_language,
            "key_count": len(data),
            "keys_match": list(data) == keys,
            "placeholders_ok": not placeholder_errors,
            "placeholder_errors": placeholder_errors,
            "empty_count": sum(not str(data[key]).strip() for key in keys),
            "exact_english_count": sum(data[key] == source[key] for key in keys),
            "source_fallback_count": fallback_count,
            "native_review_required": locale not in {"en-GB", "en-US", "en-ZA", "tr"},
        }
        g.write_json(METADATA_DIR / f"{locale}.json", metadata)
        if not metadata["keys_match"] or not metadata["placeholders_ok"] or metadata["empty_count"]:
            raise RuntimeError(f"Validation failed for {locale}: {metadata}")
        print(f"{locale}: {method}, model={model_language}, fallback={fallback_count}", flush=True)


if __name__ == "__main__":
    main()
