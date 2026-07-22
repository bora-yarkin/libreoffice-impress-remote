# SPDX-FileCopyrightText: 2026 Bora Yarkın
# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
import hashlib
import time

from impress_remote.notes import extract_notes_for_slide
from impress_remote.preview import export_slide_png_bytes, extract_slide_title, render_slide_preview
from impress_remote.localization import translate


@dataclass
class PresentationState:
    running: bool
    active: bool
    paused: bool
    document_kind: str
    status_message: str
    current_slide: int
    slide_count: int
    notes: str
    current_title: str
    current_preview: str
    next_slide: int | None
    next_title: str
    next_preview: str
    can_go_previous: bool
    can_go_next: bool
    remaining_slides: int
    at_end_of_deck: bool
    elapsed_seconds: int
    current_render_token: str
    next_render_token: str


@dataclass
class _ResolvedPresentation:
    document: object
    presentation: object | None
    controller: object | None
    slide_count: int
    running: bool
    active: bool
    paused: bool
    endless: bool
    current_index: int
    next_index: int | None


class ImpressController:
    _SLIDE_PNG_CACHE_LIMIT = 256

    def __init__(self, ctx, monotonic=None):
        self.ctx = ctx
        self._monotonic = monotonic or time.monotonic
        self._running_presentation_key: tuple[int, int] | None = None
        self._presentation_started_at: float | None = None
        self._slide_png_cache: OrderedDict[str, bytes] = OrderedDict()

    def state(self) -> PresentationState:
        document = self._document()
        if document is None:
            self._reset_runtime_tracking()
            return self._empty_state(
                document_kind="none",
                status_message=translate("state.noDocument"),
            )
        if not self._is_impress_document(document):
            self._reset_runtime_tracking()
            return self._empty_state(
                document_kind="other",
                status_message=translate("state.notImpress"),
            )

        resolved = self._resolve_presentation(document)
        key = (
            self._presentation_key(resolved.document, resolved.controller)
            if resolved.running
            else None
        )
        self._sync_runtime_tracking(key, resolved.running)
        current_slide = self._slide_for_index(document, resolved.current_index)
        next_slide = (
            self._slide_for_index(document, resolved.next_index)
            if resolved.next_index is not None
            else None
        )
        current_title = extract_slide_title(current_slide)
        current_preview = (
            render_slide_preview(current_slide, resolved.current_index)
            if current_slide is not None
            else ""
        )
        notes = extract_notes_for_slide(current_slide)
        next_title = extract_slide_title(next_slide)
        next_preview = (
            render_slide_preview(next_slide, resolved.next_index)
            if resolved.next_index is not None
            else ""
        )
        remaining_slides = max(resolved.slide_count - resolved.current_index - 1, 0)
        at_end_of_deck = resolved.slide_count > 0 and resolved.next_index is None
        status_message = self._status_message(
            resolved,
            at_end_of_deck=at_end_of_deck,
        )
        can_go_previous = resolved.current_index > 0 or (
            resolved.running and resolved.endless and resolved.slide_count > 1
        )
        can_go_next = resolved.next_index is not None

        return PresentationState(
            running=resolved.running,
            active=resolved.active,
            paused=resolved.paused,
            document_kind="impress",
            status_message=status_message,
            current_slide=resolved.current_index,
            slide_count=resolved.slide_count,
            notes=notes,
            current_title=current_title,
            current_preview=current_preview,
            next_slide=resolved.next_index,
            next_title=next_title,
            next_preview=next_preview,
            can_go_previous=can_go_previous,
            can_go_next=can_go_next,
            remaining_slides=remaining_slides,
            at_end_of_deck=at_end_of_deck,
            elapsed_seconds=self._elapsed_seconds(resolved.running),
            current_render_token=self._render_token(
                current_slide,
                resolved.current_index,
                current_title,
                notes,
                current_preview,
                resolved.running,
                resolved.paused,
            ),
            next_render_token=self._render_token(
                next_slide,
                resolved.next_index,
                next_title,
                "",
                next_preview,
                False,
                False,
            ),
        )

    def command(self, name: str, index: int | None = None) -> None:
        document = self._document()
        if not self._is_impress_document(document):
            return
        presentation = self._presentation(document)
        controller = self._slideshow_controller(document)
        if (
            name == "start_presentation"
            and presentation is not None
            and hasattr(presentation, "start")
        ):
            self._reset_runtime_tracking()
            if self._dispatch_presentation_command(
                document,
                ".uno:PresentationCurrentSlide",
            ):
                return
            self._start_presentation(document, presentation)
            return
        if (
            name == "start_presentation_from_first_slide"
            and presentation is not None
            and hasattr(presentation, "start")
        ):
            self._reset_runtime_tracking()
            if self._dispatch_presentation_command(document, ".uno:Presentation"):
                return
            self._start_presentation(document, presentation, first_slide_index=0)
            return
        if controller is not None:
            if name == "next_slide":
                if self._call_controller_method(controller, "gotoNextEffect"):
                    return
                controller.gotoNextSlide()
                return
            if name == "previous_slide":
                if self._call_controller_method(controller, "gotoPreviousEffect"):
                    return
                controller.gotoPreviousSlide()
                return
            if name == "goto_slide" and index is not None:
                controller.gotoSlideIndex(index)
                return
            if name == "goto_first_slide":
                controller.gotoSlideIndex(0)
                return
            if name == "goto_last_slide" and hasattr(controller, "gotoLastSlide"):
                controller.gotoLastSlide()
                return

        if name == "next_slide":
            self._set_editing_slide(document, self._editing_slide_index(document) + 1)
        elif name == "previous_slide":
            self._set_editing_slide(document, self._editing_slide_index(document) - 1)
        elif name == "goto_first_slide":
            self._set_editing_slide(document, 0)
        elif name == "goto_slide" and index is not None:
            self._set_editing_slide(document, index)

    def current_slide_png_bytes(self) -> bytes:
        document = self._require_impress_document()
        state = self.state()
        slide = self._slide_for_index(document, state.current_slide)
        return self._cached_slide_png_bytes(slide, state.current_render_token)

    def next_slide_png_bytes(self) -> bytes:
        document = self._require_impress_document()
        state = self.state()
        if state.next_slide is None:
            raise RuntimeError(translate("error.noNextSlideExport"))
        slide = self._slide_for_index(document, state.next_slide)
        return self._cached_slide_png_bytes(slide, state.next_render_token)

    def prewarm_slide_previews(self) -> dict[str, object]:
        document = self._require_impress_document()
        resolved = self._resolve_presentation(document)
        if resolved.slide_count <= 0:
            return {"state": "empty", "slides": 0, "cacheSize": len(self._slide_png_cache)}

        warmed = 0
        for index in range(resolved.slide_count):
            slide = self._slide_for_index(document, index)
            if slide is None:
                continue
            title = extract_slide_title(slide)
            notes = extract_notes_for_slide(slide)
            preview = render_slide_preview(slide, index)
            render_tokens = {
                self._render_token(slide, index, title, notes, preview, True, False),
                self._render_token(
                    slide,
                    index,
                    title,
                    notes,
                    preview,
                    resolved.running,
                    resolved.paused,
                ),
                self._render_token(slide, index, title, "", preview, False, False),
            }
            render_tokens.discard("")
            missing_tokens = [
                token for token in render_tokens if token not in self._slide_png_cache
            ]
            if not missing_tokens:
                continue
            data = export_slide_png_bytes(self.ctx, slide)
            warmed += 1
            for token in missing_tokens:
                self._remember_slide_png(token, data)
        return {
            "state": "ready",
            "slides": warmed,
            "cacheSize": len(self._slide_png_cache),
        }

    def _cached_slide_png_bytes(self, slide, render_token: str) -> bytes:
        if render_token:
            cached = self._slide_png_cache.get(render_token)
            if cached is not None:
                self._slide_png_cache.move_to_end(render_token)
                return cached
        data = export_slide_png_bytes(self.ctx, slide)
        if render_token:
            self._remember_slide_png(render_token, data)
        return data

    def _remember_slide_png(self, render_token: str, data: bytes) -> None:
        self._slide_png_cache[render_token] = data
        self._slide_png_cache.move_to_end(render_token)
        while len(self._slide_png_cache) > self._SLIDE_PNG_CACHE_LIMIT:
            self._slide_png_cache.popitem(last=False)

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

    def _is_impress_document(self, document) -> bool:
        return (
            document is not None
            and hasattr(document, "getDrawPages")
            and hasattr(document, "getPresentation")
        )

    def _slide_for_index(self, document, index: int | None):
        if document is None or index is None or index < 0 or not hasattr(document, "getDrawPages"):
            return None
        draw_pages = document.getDrawPages()
        if index >= draw_pages.getCount():
            return None
        return draw_pages.getByIndex(index)

    def _resolve_presentation(self, document) -> _ResolvedPresentation:
        slide_count = self._slide_count(document)
        presentation = self._presentation(document)
        controller = self._slideshow_controller(document)
        running = self._presentation_running(presentation, controller)
        active = self._presentation_active(controller, running)
        paused = running and self._controller_bool(controller, "isPaused")
        endless = running and self._controller_bool(controller, "isEndless")
        current_index = self._current_slide_index(controller, document, slide_count, running)
        next_index = self._next_slide_index(
            controller,
            current_index,
            slide_count,
            running,
            endless,
        )
        return _ResolvedPresentation(
            document=document,
            presentation=presentation,
            controller=controller,
            slide_count=slide_count,
            running=running,
            active=active,
            paused=paused,
            endless=endless,
            current_index=current_index,
            next_index=next_index,
        )

    def _current_slide_index(self, controller, document, slide_count: int, running: bool) -> int:
        if slide_count <= 0:
            return 0
        if running and controller is not None:
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

    def _next_slide_index(
        self,
        controller,
        current_index: int,
        slide_count: int,
        running: bool,
        endless: bool,
    ) -> int | None:
        if slide_count <= 0 or current_index < 0:
            return None
        if running and controller is not None and hasattr(controller, "getNextSlideIndex"):
            try:
                next_index = int(controller.getNextSlideIndex())
            except (TypeError, ValueError):
                next_index = None
            if next_index is not None and 0 <= next_index < slide_count:
                if next_index != current_index or endless:
                    return next_index
        if endless and slide_count > 0:
            return (current_index + 1) % slide_count
        if current_index + 1 < slide_count:
            return current_index + 1
        return None

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

    def _editing_slide_index(self, document) -> int:
        slide_count = self._slide_count(document)
        current_slide = self._editing_current_slide(document)
        resolved = self._slide_index(document, current_slide)
        if resolved is None:
            return 0
        return max(0, min(resolved, max(slide_count - 1, 0)))

    def _set_editing_slide(self, document, index: int) -> None:
        if document is None or not hasattr(document, "getCurrentController"):
            return
        controller = document.getCurrentController()
        if controller is None or not hasattr(controller, "setCurrentPage"):
            return
        target_slide = self._slide_for_index(document, index)
        if target_slide is None:
            return
        controller.setCurrentPage(target_slide)

    def _dispatch_presentation_command(self, document, command: str) -> bool:
        frame = self._dispatch_frame(document)
        if frame is None:
            return False
        helper = self._dispatch_helper()
        if helper is None or not hasattr(helper, "executeDispatch"):
            return False
        try:
            helper.executeDispatch(frame, command, "", 0, tuple())
        except Exception:
            return False
        return True

    def _call_controller_method(self, controller, method_name: str) -> bool:
        method = getattr(controller, method_name, None)
        if not callable(method):
            return False
        method()
        return True

    def _dispatch_frame(self, document):
        if document is None or not hasattr(document, "getCurrentController"):
            return None
        controller = document.getCurrentController()
        if controller is None or not hasattr(controller, "getFrame"):
            return None
        try:
            return controller.getFrame()
        except Exception:
            return None

    def _dispatch_helper(self):
        service_manager = self.ctx.getServiceManager()
        try:
            return service_manager.createInstanceWithContext(
                "com.sun.star.frame.DispatchHelper",
                self.ctx,
            )
        except Exception:
            return None

    def _start_presentation(
        self,
        document,
        presentation,
        first_slide_index: int | None = None,
    ) -> None:
        options = self._presentation_start_options(document, first_slide_index)
        self._apply_presentation_options(presentation, options)
        presentation.start()

    def _presentation_start_options(
        self,
        document,
        first_slide_index: int | None = None,
    ) -> list[tuple[str, object]]:
        options: list[tuple[str, object]] = [
            ("IsFullScreen", True),
            ("IsAlwaysOnTop", True),
            ("StartWithNavigator", False),
            ("Pause", 0),
            ("FirstPage", ""),
        ]
        if first_slide_index is None:
            return options

        first_slide = self._slide_for_index(document, first_slide_index)
        self._set_editing_slide(document, first_slide_index)
        first_page_name = self._slide_name(first_slide)
        if first_page_name:
            options[-1] = ("FirstPage", first_page_name)
        return options

    def _slide_name(self, slide) -> str:
        if slide is None or not hasattr(slide, "getName"):
            return ""
        try:
            name = slide.getName()
        except Exception:
            return ""
        return name if isinstance(name, str) else ""

    def _apply_presentation_options(
        self,
        presentation,
        options: list[tuple[str, object]],
    ) -> None:
        setter = getattr(presentation, "setPropertyValue", None)
        for name, value in options:
            try:
                if setter is not None:
                    setter(name, value)
                else:
                    setattr(presentation, name, value)
            except Exception:
                continue

    def _slide_index(self, document, target_slide) -> int | None:
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

    def _empty_state(self, document_kind: str, status_message: str) -> PresentationState:
        return PresentationState(
            running=False,
            active=False,
            paused=False,
            document_kind=document_kind,
            status_message=status_message,
            current_slide=0,
            slide_count=0,
            notes="",
            current_title="",
            current_preview="",
            next_slide=None,
            next_title="",
            next_preview="",
            can_go_previous=False,
            can_go_next=False,
            remaining_slides=0,
            at_end_of_deck=False,
            elapsed_seconds=0,
            current_render_token="",
            next_render_token="",
        )

    def _presentation_running(self, presentation, controller) -> bool:
        for target in (presentation, controller):
            result = self._call_optional(target, "isRunning")
            if result is not None:
                return bool(result)
        return controller is not None

    def _presentation_active(self, controller, running: bool) -> bool:
        result = self._call_optional(controller, "isActive")
        if result is not None:
            return bool(result)
        return running

    def _controller_bool(self, controller, method_name: str) -> bool:
        result = self._call_optional(controller, method_name)
        return bool(result) if result is not None else False

    def _call_optional(self, target, method_name: str):
        if target is None or not hasattr(target, method_name):
            return None
        try:
            return getattr(target, method_name)()
        except Exception:
            return None

    def _status_message(
        self,
        resolved: _ResolvedPresentation,
        *,
        at_end_of_deck: bool,
    ) -> str:
        if resolved.slide_count <= 0:
            return translate("state.emptyDeck")
        if resolved.running:
            if resolved.paused and at_end_of_deck:
                return translate("state.pausedLast")
            if resolved.paused:
                return translate("state.paused")
            if at_end_of_deck:
                return translate("state.runningLast")
            if not resolved.active:
                return translate("state.connected")
            return translate("state.running")
        return translate("state.editing")

    def _render_token(
        self,
        slide,
        index: int | None,
        title: str,
        notes: str,
        preview: str,
        running: bool,
        paused: bool,
    ) -> str:
        if slide is None or index is None or index < 0:
            return ""
        digest = hashlib.blake2s(digest_size=8)
        for value in (
            str(index),
            title,
            notes,
            preview,
            str(int(running)),
            str(int(paused)),
        ):
            digest.update(value.encode("utf-8", errors="ignore"))
            digest.update(b"\0")
        return digest.hexdigest()

    def _presentation_key(self, document, controller) -> tuple[int, int]:
        return (id(document), id(controller) if controller is not None else 0)

    def _sync_runtime_tracking(
        self,
        presentation_key: tuple[int, int] | None,
        running: bool,
    ) -> None:
        if not running or presentation_key is None:
            self._reset_runtime_tracking()
            return
        if self._running_presentation_key != presentation_key:
            self._running_presentation_key = presentation_key
            self._presentation_started_at = self._monotonic()

    def _reset_runtime_tracking(self) -> None:
        self._running_presentation_key = None
        self._presentation_started_at = None

    def _elapsed_seconds(self, running: bool) -> int:
        if not running or self._presentation_started_at is None:
            return 0
        return max(int(self._monotonic() - self._presentation_started_at), 0)

    def _require_impress_document(self):
        document = self._document()
        if not self._is_impress_document(document):
            raise RuntimeError(translate("error.impressRequired"))
        return document
