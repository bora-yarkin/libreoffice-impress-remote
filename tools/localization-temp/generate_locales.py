import concurrent.futures
import json
import re
import shutil
import time
import urllib.parse
import urllib.request
import zipfile
from collections import Counter
from pathlib import Path

import ctranslate2
from huggingface_hub import snapshot_download
from transformers import AutoTokenizer

ROOT = Path.cwd()
SOURCE_PATH = ROOT / "shared/localizations/en.json"
TURKISH_PATH = ROOT / "tools/localization-temp/tr_corrected.json"
BUILD = ROOT / "localization-build"
PACKAGE = BUILD / "libreoffice-impress-remote-locales"
LOCALES_DIR = PACKAGE / "locales"

LOCALES = {
    "af": "Afrikaans", "sq": "Albanian", "am": "Amharic", "ar": "Arabic",
    "hy": "Armenian", "as": "Assamese", "ast": "Asturian", "eu": "Basque",
    "be": "Belarusian", "bn": "Bengali", "bn-IN": "Bengali (India)", "brx": "Bodo (India)",
    "bs": "Bosnian", "br": "Breton", "bg": "Bulgarian", "my": "Burmese",
    "ca": "Catalan", "ca-valencia": "Catalan (Valencian)", "ckb": "Central Kurdish",
    "zh-CN": "Chinese (Simplified)", "zh-TW": "Chinese (Traditional)", "hr": "Croatian",
    "cs": "Czech", "da": "Danish", "doi": "Dogri", "nl": "Dutch", "dz": "Dzongkha",
    "en-GB": "English (GB)", "en-US": "English (US)", "en-ZA": "English (ZA)",
    "eo": "Esperanto", "et": "Estonian", "fi": "Finnish", "fr": "French",
    "fy": "Frisian", "fur": "Friulian", "gl": "Galician", "ka": "Georgian",
    "de": "German", "el": "Greek", "gug": "Guarani", "gu": "Gujarati",
    "he": "Hebrew", "hi": "Hindi", "hu": "Hungarian", "is": "Icelandic",
    "id": "Indonesian", "ga": "Irish", "it": "Italian", "ja": "Japanese",
    "kab": "Kabyle", "kn": "Kannada", "ks": "Kashmiri", "kk": "Kazakh",
    "km": "Khmer", "rw": "Kinyarwanda", "kok": "Konkani", "ko": "Korean",
    "ku": "Kurdish (Latin)", "lo": "Lao", "lv": "Latvian", "lt": "Lithuanian",
    "dsb": "Lower Sorbian", "lb": "Luxembourgish", "mk": "Macedonian",
    "mai": "Maithili", "ml": "Malayalam", "mni": "Manipuri", "mr": "Marathi",
    "mn": "Mongolian", "nr": "Ndebele (South)", "ne": "Nepali",
    "nso": "Northern Sotho", "nb": "Norwegian Bokmål", "nn": "Norwegian Nynorsk",
    "oc": "Occitan", "or": "Odia", "om": "Oromo", "pa": "Punjabi", "fa": "Persian",
    "pl": "Polish", "pt-PT": "Portuguese", "pt-BR": "Portuguese (Brazil)",
    "ro": "Romanian", "ru": "Russian", "sa": "Sanskrit", "sat": "Santali",
    "gd": "Scottish Gaelic", "sr": "Serbian", "sr-Latn": "Serbian (Latin)",
    "sid": "Sidama", "szl": "Silesian", "sd": "Sindhi", "si": "Sinhala",
    "sk": "Slovak", "sl": "Slovenian", "st": "Southern Sotho", "es": "Spanish",
    "sw": "Swahili", "ss": "Swati", "sv": "Swedish", "tl": "Tagalog",
    "tg": "Tajik", "ta": "Tamil", "tt": "Tatar", "te": "Telugu", "th": "Thai",
    "bo": "Tibetan", "ts": "Tsonga", "tn": "Tswana", "tr": "Turkish",
    "ug": "Uighur", "uk": "Ukrainian", "hsb": "Upper Sorbian", "uz": "Uzbek",
    "ve": "Venda", "vec": "Venetian", "vi": "Vietnamese", "cy": "Welsh",
    "xh": "Xhosa", "zu": "Zulu"
}

NLLB = {
    "af": "afr_Latn", "sq": "als_Latn", "am": "amh_Ethi", "ar": "arb_Arab",
    "hy": "hye_Armn", "as": "asm_Beng", "ast": "ast_Latn", "eu": "eus_Latn",
    "be": "bel_Cyrl", "bn": "ben_Beng", "bn-IN": "ben_Beng", "bs": "bos_Latn",
    "br": "bre_Latn", "bg": "bul_Cyrl", "my": "mya_Mymr", "ca": "cat_Latn",
    "ca-valencia": "cat_Latn", "ckb": "ckb_Arab", "zh-CN": "zho_Hans",
    "zh-TW": "zho_Hant", "hr": "hrv_Latn", "cs": "ces_Latn", "da": "dan_Latn",
    "nl": "nld_Latn", "dz": "dzo_Tibt", "eo": "epo_Latn", "et": "est_Latn",
    "fi": "fin_Latn", "fr": "fra_Latn", "fur": "fur_Latn", "gl": "glg_Latn",
    "ka": "kat_Geor", "de": "deu_Latn", "el": "ell_Grek", "gug": "grn_Latn",
    "gu": "guj_Gujr", "he": "heb_Hebr", "hi": "hin_Deva", "hu": "hun_Latn",
    "is": "isl_Latn", "id": "ind_Latn", "ga": "gle_Latn", "it": "ita_Latn",
    "ja": "jpn_Jpan", "kab": "kab_Latn", "kn": "kan_Knda", "ks": "kas_Arab",
    "kk": "kaz_Cyrl", "km": "khm_Khmr", "rw": "kin_Latn", "ko": "kor_Hang",
    "ku": "kmr_Latn", "lo": "lao_Laoo", "lv": "lvs_Latn", "lt": "lit_Latn",
    "lb": "ltz_Latn", "mk": "mkd_Cyrl", "mai": "mai_Deva", "ml": "mal_Mlym",
    "mni": "mni_Beng", "mr": "mar_Deva", "mn": "khk_Cyrl", "ne": "npi_Deva",
    "nso": "nso_Latn", "nb": "nob_Latn", "nn": "nno_Latn", "oc": "oci_Latn",
    "or": "ory_Orya", "om": "gaz_Latn", "pa": "pan_Guru", "fa": "pes_Arab",
    "pl": "pol_Latn", "pt-PT": "por_Latn", "pt-BR": "por_Latn", "ro": "ron_Latn",
    "ru": "rus_Cyrl", "sa": "san_Deva", "sat": "sat_Olck", "gd": "gla_Latn",
    "sr": "srp_Cyrl", "szl": "szl_Latn", "sd": "snd_Arab", "si": "sin_Sinh",
    "sk": "slk_Latn", "sl": "slv_Latn", "st": "sot_Latn", "es": "spa_Latn",
    "sw": "swh_Latn", "ss": "ssw_Latn", "sv": "swe_Latn", "tl": "tgl_Latn",
    "tg": "tgk_Cyrl", "ta": "tam_Taml", "tt": "tat_Cyrl", "te": "tel_Telu",
    "th": "tha_Thai", "bo": "bod_Tibt", "ts": "tso_Latn", "tn": "tsn_Latn",
    "tr": "tur_Latn", "ug": "uig_Arab", "uk": "ukr_Cyrl", "uz": "uzn_Latn",
    "vec": "vec_Latn", "vi": "vie_Latn", "cy": "cym_Latn", "xh": "xho_Latn",
    "zu": "zul_Latn"
}

GOOGLE = {
    "brx": "brx", "doi": "doi", "fy": "fy", "kok": "gom", "dsb": "dsb",
    "nr": "nr", "sid": "sid", "sr-Latn": "sr", "hsb": "hsb", "ve": "ve"
}

RELATED_FALLBACK = {
    "brx": "asm_Beng", "doi": "hin_Deva", "fy": "nld_Latn", "kok": "mar_Deva",
    "dsb": "ces_Latn", "nr": "zul_Latn", "sid": "gaz_Latn", "sr-Latn": "srp_Cyrl",
    "hsb": "ces_Latn", "ve": "tso_Latn"
}

PROTECTED = [
    "LibreOffice", "Impress", "LocalTunnel", "GraphicExportFilter", "ERROR_CORRECT_H",
    "Web Crypto", "WebSocket", "websocket", "AES-GCM", "AES", "P-256", "IPv6", "UTF-8",
    "JSON", "QR", "UNO", "PyPNG", "BaseImage.drawimage", "BaseImage.drawrect_context",
    "glog", "range(8)", "TTY", "nonce", "host_v4", "host_v6", "session_ttl",
    "/api/session", "/health", "/ws", "HTTP"
]

PLACEHOLDER_RE = re.compile(r"\{[^{}]+\}")
SENTINEL_RE = re.compile(r"ZXQ([PT])(\d+)QXZ", re.IGNORECASE)


def protect(text):
    items = []
    def ph(match):
        index = len(items)
        items.append(("P", match.group(0)))
        return f" ZXQP{index}QXZ "
    text = PLACEHOLDER_RE.sub(ph, text)
    for term in sorted(PROTECTED, key=len, reverse=True):
        pattern = re.compile(re.escape(term), re.IGNORECASE)
        def tr(match):
            index = len(items)
            items.append(("T", match.group(0)))
            return f" ZXQT{index}QXZ "
        text = pattern.sub(tr, text)
    return re.sub(r"\s+", " ", text).strip(), items


def restore(text, items):
    normalized = re.sub(r"Z\s*X\s*Q\s*([PT])\s*(\d+)\s*Q\s*X\s*Z", r"ZXQ\1\2QXZ", text, flags=re.IGNORECASE)
    seen = Counter()
    def repl(match):
        kind = match.group(1).upper()
        index = int(match.group(2))
        if 0 <= index < len(items) and items[index][0] == kind:
            seen[(kind, index)] += 1
            return items[index][1]
        return match.group(0)
    restored = SENTINEL_RE.sub(repl, normalized)
    expected = Counter((kind, index) for index, (kind, _) in enumerate(items))
    if any(seen[item] != expected[item] for item in expected):
        return None
    return re.sub(r"\s+([.,;:!?])", r"\1", restored).strip()


def placeholder_signature(text):
    return sorted(PLACEHOLDER_RE.findall(text))


def nllb_translate(values, target_code, tokenizer, translator):
    protected = [protect(value) for value in values]
    tokenizer.src_lang = "eng_Latn"
    sources = [tokenizer.convert_ids_to_tokens(tokenizer.encode(text)) for text, _ in protected]
    results = translator.translate_batch(
        sources,
        target_prefix=[[target_code] for _ in sources],
        beam_size=1,
        batch_type="tokens",
        max_batch_size=4096,
        max_decoding_length=192,
        repetition_penalty=1.05,
        replace_unknowns=True,
    )
    output = []
    fallback_count = 0
    for source, (_, items), result in zip(values, protected, results):
        tokens = list(result.hypotheses[0])
        if tokens and tokens[0] == target_code:
            tokens = tokens[1:]
        decoded = tokenizer.decode(tokenizer.convert_tokens_to_ids(tokens), skip_special_tokens=True).strip()
        restored = restore(decoded, items)
        if restored is None or placeholder_signature(restored) != placeholder_signature(source):
            restored = source
            fallback_count += 1
        output.append(restored)
    return output, fallback_count


def google_translate_one(text, target):
    protected, items = protect(text)
    params = urllib.parse.urlencode({"client": "gtx", "sl": "en", "tl": target, "dt": "t", "q": protected})
    url = "https://translate.googleapis.com/translate_a/single?" + params
    last = None
    for delay in (0, 1, 2, 4):
        if delay:
            time.sleep(delay)
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(request, timeout=30) as response:
                data = json.loads(response.read().decode("utf-8"))
            translated = "".join(part[0] for part in data[0] if part and part[0])
            restored = restore(translated, items)
            if restored is None or placeholder_signature(restored) != placeholder_signature(text):
                raise ValueError("placeholder preservation failed")
            return restored
        except Exception as exception:
            last = exception
    raise RuntimeError(str(last))


def google_translate(values, target):
    output = [None] * len(values)
    failures = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        futures = {pool.submit(google_translate_one, text, target): index for index, text in enumerate(values)}
        for future in concurrent.futures.as_completed(futures):
            index = futures[future]
            try:
                output[index] = future.result()
            except Exception:
                failures.append(index)
                output[index] = values[index]
    return output, failures


def transliterate_serbian(text):
    pairs = [
        ("Љ", "Lj"), ("Њ", "Nj"), ("Џ", "Dž"), ("љ", "lj"), ("њ", "nj"), ("џ", "dž"),
        ("А", "A"), ("Б", "B"), ("В", "V"), ("Г", "G"), ("Д", "D"), ("Ђ", "Đ"),
        ("Е", "E"), ("Ж", "Ž"), ("З", "Z"), ("И", "I"), ("Ј", "J"), ("К", "K"),
        ("Л", "L"), ("М", "M"), ("Н", "N"), ("О", "O"), ("П", "P"), ("Р", "R"),
        ("С", "S"), ("Т", "T"), ("Ћ", "Ć"), ("У", "U"), ("Ф", "F"), ("Х", "H"),
        ("Ц", "C"), ("Ч", "Č"), ("Ш", "Š"), ("а", "a"), ("б", "b"), ("в", "v"),
        ("г", "g"), ("д", "d"), ("ђ", "đ"), ("е", "e"), ("ж", "ž"), ("з", "z"),
        ("и", "i"), ("ј", "j"), ("к", "k"), ("л", "l"), ("м", "m"), ("н", "n"),
        ("о", "o"), ("п", "p"), ("р", "r"), ("с", "s"), ("т", "t"), ("ћ", "ć"),
        ("у", "u"), ("ф", "f"), ("х", "h"), ("ц", "c"), ("ч", "č"), ("ш", "š")
    ]
    for source, target in pairs:
        text = text.replace(source, target)
    return text


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    source = json.loads(SOURCE_PATH.read_text(encoding="utf-8"))
    turkish = json.loads(TURKISH_PATH.read_text(encoding="utf-8"))
    if list(source) != list(turkish):
        raise RuntimeError("Turkish keys do not match English keys")
    shutil.rmtree(BUILD, ignore_errors=True)
    LOCALES_DIR.mkdir(parents=True)
    keys = list(source)
    values = list(source.values())

    tokenizer = AutoTokenizer.from_pretrained("facebook/nllb-200-distilled-600M", src_lang="eng_Latn")
    model_path = snapshot_download("osa911/nllb-200-distilled-600M-ct2-int8")
    translator = ctranslate2.Translator(model_path, device="cpu", compute_type="int8", inter_threads=2, intra_threads=2)

    token_ids = {code: tokenizer.convert_tokens_to_ids(code) for code in set(NLLB.values()) | set(RELATED_FALLBACK.values())}
    available = {code for code, token_id in token_ids.items() if token_id != tokenizer.unk_token_id}
    cache = {}
    metadata = {}

    for locale, language in LOCALES.items():
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
        elif locale == "sr-Latn" and "sr" in metadata:
            sr_data = json.loads((LOCALES_DIR / "sr.json").read_text(encoding="utf-8"))
            translated = [transliterate_serbian(sr_data[key]) for key in keys]
            method = "nllb-plus-script-transliteration"
            model_language = "srp_Cyrl"
            fallback_count = metadata["sr"]["source_fallback_count"]
        else:
            desired = NLLB.get(locale)
            if desired and desired in available:
                if desired not in cache:
                    cache[desired] = nllb_translate(values, desired, tokenizer, translator)
                translated, fallback_count = cache[desired]
                method = "nllb-200-int8"
                model_language = desired
            else:
                google_code = GOOGLE.get(locale)
                google_values = None
                google_failures = list(range(len(values)))
                if google_code:
                    try:
                        google_values, google_failures = google_translate(values, google_code)
                    except Exception:
                        google_values = None
                if google_values is not None and len(google_failures) < len(values) // 4:
                    translated = google_values
                    fallback_count = len(google_failures)
                    method = "google-web-translation-fallback"
                    model_language = google_code
                else:
                    related = RELATED_FALLBACK.get(locale, "eng_Latn")
                    if related in available:
                        if related not in cache:
                            cache[related] = nllb_translate(values, related, tokenizer, translator)
                        translated, fallback_count = cache[related]
                        method = "related-language-machine-draft"
                        model_language = related
                    else:
                        translated = values
                        fallback_count = len(values)
                        method = "english-fallback"
                        model_language = "eng_Latn"

        data = dict(zip(keys, translated))
        write_json(LOCALES_DIR / f"{locale}.json", data)
        exact_english = sum(data[key] == source[key] for key in keys)
        placeholder_errors = [key for key in keys if placeholder_signature(data[key]) != placeholder_signature(source[key])]
        metadata[locale] = {
            "language": language,
            "file": f"locales/{locale}.json",
            "method": method,
            "model_language": model_language,
            "key_count": len(data),
            "keys_match": list(data) == keys,
            "placeholders_ok": not placeholder_errors,
            "placeholder_errors": placeholder_errors,
            "empty_count": sum(not str(data[key]).strip() for key in keys),
            "exact_english_count": exact_english,
            "source_fallback_count": fallback_count,
            "native_review_required": locale not in {"en-GB", "en-US", "en-ZA", "tr"},
        }
        print(f"{locale}: {method}, model={model_language}, english={exact_english}, fallback={fallback_count}", flush=True)

    for locale in LOCALES:
        data = json.loads((LOCALES_DIR / f"{locale}.json").read_text(encoding="utf-8"))
        if list(data) != keys:
            raise RuntimeError(f"Key mismatch: {locale}")
        for key in keys:
            if placeholder_signature(data[key]) != placeholder_signature(source[key]):
                raise RuntimeError(f"Placeholder mismatch: {locale}:{key}")

    manifest = {
        "source_locale": "en-US",
        "locale_count": len(LOCALES),
        "string_count_per_locale": len(keys),
        "locales": [{"locale": code, "language": name, "file": f"locales/{code}.json"} for code, name in LOCALES.items()]
    }
    qa = {
        "summary": {
            "locale_count": len(LOCALES),
            "string_count_per_locale": len(keys),
            "all_json_valid": True,
            "all_keys_match": all(item["keys_match"] for item in metadata.values()),
            "all_placeholders_valid": all(item["placeholders_ok"] for item in metadata.values()),
            "machine_generated_locale_count": sum(item["method"] not in {"source-copy", "human-corrected-existing-translation"} for item in metadata.values()),
            "related_language_or_english_fallback_locales": [code for code, item in metadata.items() if item["method"] in {"related-language-machine-draft", "english-fallback"}],
        },
        "locales": metadata,
    }
    write_json(PACKAGE / "manifest.json", manifest)
    write_json(PACKAGE / "QA_REPORT.json", qa)
    readme = f"""# LibreOffice Impress Remote localizations

This package contains {len(LOCALES)} LibreOffice UI locale variants with {len(keys)} JSON strings per locale.

## Contents

- `locales/*.json`: one UTF-8 JSON file per locale code
- `manifest.json`: locale names and file paths
- `QA_REPORT.json`: generation method and automated validation results per locale

## Validation

Every locale file was parsed as JSON and checked for exact key order, key count, empty values, and exact preservation of every `{{placeholder}}` token from the English source.

## Translation status

- `en-GB`, `en-US`, and `en-ZA` are exact copies of the English base.
- `tr.json` is the existing Turkish translation with Turkish characters and orthography corrected.
- Other locales are machine-generated drafts. Native-speaker review is required before release.
- `QA_REPORT.json` identifies the machine-translation method, source-language fallback count, and any locale generated through a related-language fallback.
- Product names, protocol identifiers, code paths, placeholders, and cryptographic terms were protected during translation.

The English source remains authoritative for keys and runtime placeholders.
"""
    (PACKAGE / "README.md").write_text(readme, encoding="utf-8")

    zip_path = BUILD / "libreoffice-impress-remote-locales.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(PACKAGE.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(BUILD))
    print(f"ZIP={zip_path}", flush=True)


if __name__ == "__main__":
    main()
