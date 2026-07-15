# SPDX-FileCopyrightText: 2026 Bora Yarkın
# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from impress_remote.notes import extract_notes_for_slide
from impress_remote.preview import extract_slide_title, render_slide_preview


@dataclass
class PresentationState:
    running: bool
    current_slide: int
    slide_count: int
    notes: str
    current_title: str
    next_slide: Optional[int]
    next_title: str
    next_preview: str
    can_go_previous: bool
    can_go_next: bool


class ImpressController:
    def __init__(self, ctx):
        self.ctx = ctx

    def state(self) -> PresentationState:
        document = self._document()
        slide_count = self._slide_count(document)
        slideshow_controller = self._slideshow_controller(document)
        current_index = self._current_slide_index(slideshow_controller, document, slide_count)
        current_slide = self._slide_for_index(document, current_index)
        next_index = current_index + 1 if current_index + 1 < slide_count else None
        next_slide = self._slide_for_index(document, next_index) if next_index is not None else None

        return PresentationState(
            running=slideshow_controller is not None,
            current_slide=current_index,
            slide_count=slide_count,
            notes=extract_notes_for_slide(current_slide),
            current_title=extract_slide_title(current_slide),
            next_slide=next_index,
            next_title=extract_slide_title(next_slide),
            next_preview=render_slide_preview(next_slide, next_index) if next_index is not None else "",
            can_go_previous=current_index > 0,
            can_go_next=next_index is not None,
        )

    def command(self, name: str, index: Optional[int] = None) -> None:
        document = self._document()
        presentation = self._presentation(document)
        controller = self._slideshow_controller(document)
        if name == "start_presentation" and presentation is not None and hasattr(presentation, "start"):
            presentation.start()
            return
        if name == "end_presentation" and presentation is not None and hasattr(presentation, "end"):
            presentation.end()
            return
        if controller is None:
            return
        if name == "next_effect":
            controller.gotoNextEffect()
        elif name == "previous_effect":
            controller.gotoPreviousEffect()
        elif name == "next_slide":
            controller.gotoNextSlide()
        elif name == "previous_slide":
            controller.gotoPreviousSlide()
        elif name == "goto_slide" and index is not None:
            controller.gotoSlideIndex(index)

    def _desktop(self):
        service_manager = self.ctx.getServiceManager()
        return service_manager.createInstanceWithContext("com.sun.star.frame.Desktop", self.ctx)

    def _document(self):
        desktop = self._desktop()
        if desktop is None:
            return None
        return desktop.getCurrentComponent()

    def _presentation(self, document=None):
        document = document or self._document()
        if document is None or not hasattr(document, "getPresentation"):
            return None
        return document.getPresentation()

    def _slideshow_controller(self, document=None):
        presentation = self._presentation(document)
        if presentation is None or not hasattr(presentation, "getController"):
            return None
        return presentation.getController()

    def _slide_count(self, document) -> int:
        if document is None or not hasattr(document, "getDrawPages"):
            return 0
        return document.getDrawPages().getCount()

    def _slide_for_index(self, document, index: Optional[int]):
        if document is None or index is None or index < 0 or not hasattr(document, "getDrawPages"):
            return None
        draw_pages = document.getDrawPages()
        if index >= draw_pages.getCount():
            return None
        return draw_pages.getByIndex(index)

    def _current_slide_index(self, controller, document, slide_count: int) -> int:
        if slide_count <= 0:
            return 0
        if controller is not None:
            if hasattr(controller, "getCurrentSlideIndex"):
                try:
                    index = int(controller.getCurrentSlideIndex())
                except (TypeError, ValueError):
                    index = None
                if index is not None and 0 <= index < slide_count:
                    return index

            current_slide = self._slide_from_controller(controller)
            resolved = self._slide_index(document, current_slide)
            if resolved is not None:
                return resolved

        current_slide = self._editing_current_slide(document)
        resolved = self._slide_index(document, current_slide)
        return resolved if resolved is not None else 0

    def _slide_from_controller(self, controller):
        if controller is None:
            return None
        for method_name in ("getCurrentSlide", "getCurrentPage"):
            if hasattr(controller, method_name):
                try:
                    return getattr(controller, method_name)()
                except Exception:
                    return None
        return None

    def _editing_current_slide(self, document):
        if document is None or not hasattr(document, "getCurrentController"):
            return None
        controller = document.getCurrentController()
        if controller is None or not hasattr(controller, "getCurrentPage"):
            return None
        return controller.getCurrentPage()

    def _slide_index(self, document, target_slide) -> Optional[int]:
        if document is None or target_slide is None or not hasattr(document, "getDrawPages"):
            return None
        draw_pages = document.getDrawPages()
        for index in range(draw_pages.getCount()):
            candidate = draw_pages.getByIndex(index)
            if candidate is target_slide:
                return index
            try:
                if candidate == target_slide:
                    return index
            except Exception:
                pass
            candidate_name = getattr(candidate, "getName", None)
            target_name = getattr(target_slide, "getName", None)
            if callable(candidate_name) and callable(target_name):
                try:
                    if candidate_name() and candidate_name() == target_name():
                        return index
                except Exception:
                    continue
        return None
