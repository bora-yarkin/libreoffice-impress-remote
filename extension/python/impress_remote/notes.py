# SPDX-FileCopyrightText: 2026 Bora Yarkın
# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations


def extract_notes_for_slide(slide) -> str:
    if slide is None or not hasattr(slide, "getNotesPage"):
        return ""
    notes_page = slide.getNotesPage()
    parts: list[str] = []
    for index in range(notes_page.getCount()):
        shape = notes_page.getByIndex(index)
        if hasattr(shape, "getString"):
            text = shape.getString().strip()
            if text:
                parts.append(text)
    return "\n\n".join(parts)
