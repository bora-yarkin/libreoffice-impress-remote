# SPDX-FileCopyrightText: 2026 Bora Yarkın
# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

from typing import List


def extract_slide_title(slide) -> str:
    snippets = extract_slide_snippets(slide, limit=1)
    return snippets[0] if snippets else ""


def extract_slide_snippets(slide, limit: int = 3) -> List[str]:
    if slide is None or not hasattr(slide, "getCount"):
        return []

    snippets: List[str] = []
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
        return f"Slide {index + 1}"
    if len(snippets) == 1:
        return snippets[0]
    return " | ".join(snippets)
