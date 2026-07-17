# SPDX-FileCopyrightText: 2026 Bora Yarkın
# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations


def _is_placeholder_text(text: str) -> bool:
    normalized = " ".join(text.strip().lower().split())
    if not normalized:
        return True
    if normalized in {
        "<number>",
        "<date>",
        "<time>",
        "<date/time>",
        "<header>",
        "<footer>",
        "<slide number>",
    }:
        return True
    if normalized.startswith("<") and normalized.endswith(">"):
        inner = normalized[1:-1]
        return bool(inner) and all(
            character.isalnum() or character in {" ", "/", "-", "_"}
            for character in inner
        )
    return False


def extract_notes_for_slide(slide) -> str:
    if slide is None or not hasattr(slide, "getNotesPage"):
        return ""
    notes_page = slide.getNotesPage()
    parts: list[str] = []
    for index in range(notes_page.getCount()):
        shape = notes_page.getByIndex(index)
        if hasattr(shape, "getString"):
            text = shape.getString().strip()
            if text and not _is_placeholder_text(text):
                parts.append(text)
    return "\n\n".join(parts)
