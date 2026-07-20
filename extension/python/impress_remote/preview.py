# SPDX-FileCopyrightText: 2026 Bora Yarkın
# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

from pathlib import Path
import tempfile

from impress_remote.localization import translate


def extract_slide_title(slide) -> str:
    snippets = extract_slide_snippets(slide, limit=1)
    return snippets[0] if snippets else ""


def extract_slide_snippets(slide, limit: int = 3) -> list[str]:
    if slide is None or not hasattr(slide, "getCount"):
        return []

    snippets: list[str] = []
    for index in range(slide.getCount()):
        shape = slide.getByIndex(index)
        if not hasattr(shape, "getString"):
            continue
        lines = [line.strip() for line in shape.getString().splitlines()]
        for line in lines:
            if line:
                snippets.append(line)
            if len(snippets) >= limit:
                return snippets[:limit]
    return snippets[:limit]


def render_slide_preview(slide, index: int) -> str:
    snippets = extract_slide_snippets(slide)
    if not snippets:
        return translate("preview.slideFallback", number=index + 1)
    if len(snippets) == 1:
        return snippets[0]
    return " | ".join(snippets)


def export_slide_png_bytes(ctx, slide) -> bytes:
    if slide is None:
        raise RuntimeError(translate("error.noSlideExport"))

    try:
        import uno  # type: ignore[import-not-found]
    except ImportError as exc:
        raise RuntimeError(translate("error.unoUnavailable")) from exc

    service_manager = ctx.getServiceManager()
    export_filter = service_manager.createInstanceWithContext(
        "com.sun.star.drawing.GraphicExportFilter",
        ctx,
    )
    if export_filter is None:
        raise RuntimeError(translate("error.graphicExportFilter"))

    temp_file = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    temp_file.close()
    output_path = Path(temp_file.name)

    try:
        media_type = uno.createUnoStruct("com.sun.star.beans.PropertyValue")
        media_type.Name = "MediaType"
        media_type.Value = "image/png"

        target_url = uno.createUnoStruct("com.sun.star.beans.PropertyValue")
        target_url.Name = "URL"
        target_url.Value = output_path.resolve().as_uri()

        export_filter.setSourceDocument(slide)
        exported = export_filter.filter((media_type, target_url))
        if exported is False or not output_path.exists():
            raise RuntimeError(translate("error.slidePreviewExport"))
        return output_path.read_bytes()
    finally:
        try:
            output_path.unlink(missing_ok=True)
        except OSError:
            pass
