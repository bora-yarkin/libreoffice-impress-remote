# SPDX-FileCopyrightText: 2026 Bora Yarkın
# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PresentationState:
    running: bool
    current_slide: int
    slide_count: int
    notes: str


class ImpressController:
    def __init__(self, ctx):
        self.ctx = ctx

    def state(self) -> PresentationState:
        document = self._document()
        slide_count = 0
        if document is not None and hasattr(document, "getDrawPages"):
            slide_count = document.getDrawPages().getCount()
        return PresentationState(True, 0, slide_count, "")

    def command(self, name: str, index: int | None = None) -> None:
        controller = self._slideshow_controller()
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

    def _slideshow_controller(self):
        document = self._document()
        if document is None or not hasattr(document, "getPresentation"):
            return None
        presentation = document.getPresentation()
        if presentation is None or not hasattr(presentation, "getController"):
            return None
        return presentation.getController()
