# SPDX-FileCopyrightText: 2026 Bora Yarkın
# SPDX-License-Identifier: GPL-3.0-only

import unittest
from unittest.mock import patch

from impress_remote.controller import ImpressController


class FakeShape:
    def __init__(self, text: str):
        self.text = text

    def getString(self) -> str:
        return self.text


class FakeSlide:
    def __init__(self, name: str, texts: list[str], notes: list[str] | None = None):
        self.name = name
        self.shapes = [FakeShape(text) for text in texts]
        self.notes_page = FakeNotesPage(notes or [])

    def getCount(self) -> int:
        return len(self.shapes)

    def getByIndex(self, index: int):
        return self.shapes[index]

    def getName(self) -> str:
        return self.name

    def getNotesPage(self):
        return self.notes_page


class FakeNotesPage:
    def __init__(self, texts: list[str]):
        self.shapes = [FakeShape(text) for text in texts]

    def getCount(self) -> int:
        return len(self.shapes)

    def getByIndex(self, index: int):
        return self.shapes[index]


class FakeDrawPages:
    def __init__(self, slides: list[FakeSlide]):
        self.slides = slides

    def getCount(self) -> int:
        return len(self.slides)

    def getByIndex(self, index: int):
        return self.slides[index]


class FakeSlideShowController:
    def __init__(
        self,
        current_index: int,
        slides: list[FakeSlide],
        *,
        running: bool = True,
        active: bool | None = None,
        paused: bool = False,
        endless: bool = False,
        next_index: int | None = None,
        current_slide_override=None,
        fail_current_slide_index: bool = False,
    ):
        self.current_index = current_index
        self.slides = slides
        self.running = running
        self.active = running if active is None else active
        self.paused = paused
        self.endless = endless
        self.next_index = next_index
        self.current_slide_override = current_slide_override
        self.fail_current_slide_index = fail_current_slide_index
        self.commands: list[tuple[str, int | None]] = []

    def getCurrentSlideIndex(self) -> int:
        if self.fail_current_slide_index:
            raise TypeError("Current slide index is unavailable")
        return self.current_index

    def getCurrentSlide(self):
        if self.current_slide_override is not None:
            return self.current_slide_override
        return self.slides[self.current_index]

    def getCurrentPage(self):
        return self.getCurrentSlide()

    def getNextSlideIndex(self) -> int:
        if self.next_index is not None:
            return self.next_index
        if self.endless and self.slides:
            return (self.current_index + 1) % len(self.slides)
        if self.current_index + 1 < len(self.slides):
            return self.current_index + 1
        return -1

    def isRunning(self) -> bool:
        return self.running

    def isActive(self) -> bool:
        return self.active

    def isPaused(self) -> bool:
        return self.paused

    def isEndless(self) -> bool:
        return self.endless

    def gotoNextEffect(self) -> None:
        self.commands.append(("next_effect", None))

    def gotoPreviousEffect(self) -> None:
        self.commands.append(("previous_effect", None))

    def gotoNextSlide(self) -> None:
        self.commands.append(("next_slide", None))

    def gotoPreviousSlide(self) -> None:
        self.commands.append(("previous_slide", None))

    def gotoSlideIndex(self, index: int) -> None:
        self.commands.append(("goto_slide", index))

    def pause(self) -> None:
        self.paused = True
        self.commands.append(("pause", None))

    def resume(self) -> None:
        self.paused = False
        self.commands.append(("resume", None))

    def blankScreen(self, color: int) -> None:
        self.commands.append(("blank_screen", color))

    def gotoLastSlide(self) -> None:
        self.commands.append(("goto_last_slide", None))


class FakePresentation:
    def __init__(self, controller):
        self.controller = controller
        self.started = False
        self.ended = False
        self.properties: dict[str, object] = {}

    def getController(self):
        return self.controller

    def setPropertyValue(self, name: str, value: object) -> None:
        self.properties[name] = value

    def start(self) -> None:
        self.started = True
        if self.controller is not None:
            self.controller.running = True

    def end(self) -> None:
        self.ended = True
        if self.controller is not None:
            self.controller.running = False

    def isRunning(self) -> bool:
        return bool(self.controller is not None and self.controller.running)


class FakeFrame:
    pass


class FakeDispatchHelper:
    def __init__(self, should_fail: bool = False):
        self.should_fail = should_fail
        self.calls: list[tuple[object, str, str, int, tuple[object, ...]]] = []

    def executeDispatch(
        self,
        dispatch_provider,
        url: str,
        target_frame_name: str,
        search_flags: int,
        arguments,
    ) -> None:
        if self.should_fail:
            raise RuntimeError("Dispatch failed")
        self.calls.append(
            (
                dispatch_provider,
                url,
                target_frame_name,
                search_flags,
                tuple(arguments),
            )
        )


class FakeLegacyPresentation:
    def __init__(self, controller):
        self.controller = controller
        self.started = False
        self.ended = False
        self.properties: dict[str, object] = {}

    def getController(self):
        return self.controller

    def setPropertyValue(self, name: str, value: object) -> None:
        self.properties[name] = value

    def start(self) -> None:
        self.started = True
        if self.controller is not None:
            self.controller.running = True

    def end(self) -> None:
        self.ended = True
        if self.controller is not None:
            self.controller.running = False

    def isRunning(self) -> bool:
        return bool(self.controller is not None and self.controller.running)


class FakeCurrentController:
    def __init__(self, slide, frame=None):
        self.slide = slide
        self.frame = frame or FakeFrame()
        self.selected_pages = []

    def getCurrentPage(self):
        return self.slide

    def setCurrentPage(self, slide) -> None:
        self.slide = slide
        self.selected_pages.append(slide)

    def getFrame(self):
        return self.frame


class FakeDocument:
    def __init__(self, slides: list[FakeSlide], presentation, current_page, frame=None):
        self.draw_pages = FakeDrawPages(slides)
        self.presentation = presentation
        self.current_controller = FakeCurrentController(current_page, frame=frame)

    def getDrawPages(self):
        return self.draw_pages

    def getPresentation(self):
        return self.presentation

    def getCurrentController(self):
        return self.current_controller


class FakeNonImpressDocument:
    pass


class FakeDesktop:
    def __init__(self, document):
        self.document = document

    def getCurrentComponent(self):
        return self.document


class FakeServiceManager:
    def __init__(self, document, dispatch_helper=None):
        self.document = document
        self.dispatch_helper = dispatch_helper

    def createInstanceWithContext(self, _service_name: str, _ctx):
        if _service_name == "com.sun.star.frame.DispatchHelper":
            return self.dispatch_helper
        return FakeDesktop(self.document)


class FakeContext:
    def __init__(self, document, dispatch_helper=None):
        self.document = document
        self.dispatch_helper = dispatch_helper

    def getServiceManager(self):
        return FakeServiceManager(self.document, dispatch_helper=self.dispatch_helper)


class ControllerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.slides = [
            FakeSlide("Agenda", ["Agenda", "Intro", "Plan"], ["Welcome everyone"]),
            FakeSlide("Metrics", ["Metrics", "Revenue up", "Churn down"], ["Focus on churn"]),
            FakeSlide("Wrap", ["Wrap Up"], ["Questions"]),
        ]

    def test_state_reports_current_and_next_slide_details(self) -> None:
        slideshow = FakeSlideShowController(current_index=1, slides=self.slides)
        document = FakeDocument(self.slides, FakePresentation(slideshow), self.slides[0])
        controller = ImpressController(FakeContext(document), monotonic=lambda: 100.0)

        state = controller.state()

        self.assertTrue(state.running)
        self.assertTrue(state.active)
        self.assertFalse(state.paused)
        self.assertFalse(state.blanked)
        self.assertEqual(state.document_kind, "impress")
        self.assertEqual(state.status_message, "Presentation running")
        self.assertEqual(state.current_slide, 1)
        self.assertEqual(state.slide_count, 3)
        self.assertEqual(state.current_title, "Metrics")
        self.assertEqual(state.current_preview, "Metrics | Revenue up | Churn down")
        self.assertEqual(state.notes, "Focus on churn")
        self.assertEqual(state.next_slide, 2)
        self.assertEqual(state.next_title, "Wrap Up")
        self.assertIn("Wrap Up", state.next_preview)
        self.assertEqual(state.remaining_slides, 1)
        self.assertFalse(state.at_end_of_deck)
        self.assertEqual(state.elapsed_seconds, 0)
        self.assertTrue(state.can_go_previous)
        self.assertTrue(state.can_go_next)
        self.assertTrue(state.current_render_token)
        self.assertTrue(state.next_render_token)

    def test_prewarm_slide_previews_populates_png_cache_for_local_mode(self) -> None:
        slideshow = FakeSlideShowController(current_index=0, slides=self.slides)
        document = FakeDocument(self.slides, FakePresentation(slideshow), self.slides[0])
        controller = ImpressController(FakeContext(document))
        exported: list[str] = []

        def export(_ctx, slide) -> bytes:
            exported.append(slide.getName())
            return f"png:{slide.getName()}".encode()

        with patch("impress_remote.controller.export_slide_png_bytes", side_effect=export):
            result = controller.prewarm_slide_previews()
            current_png = controller.current_slide_png_bytes()
            next_png = controller.next_slide_png_bytes()

        self.assertEqual(result["state"], "ready")
        self.assertEqual(result["slides"], 3)
        self.assertEqual(exported, ["Agenda", "Metrics", "Wrap"])
        self.assertEqual(current_png, b"png:Agenda")
        self.assertEqual(next_png, b"png:Metrics")

    def test_state_falls_back_to_editing_view_when_slideshow_is_not_running(self) -> None:
        slideshow = FakeSlideShowController(current_index=0, slides=self.slides, running=False)
        document = FakeDocument(self.slides, FakePresentation(slideshow), self.slides[2])
        controller = ImpressController(FakeContext(document))

        state = controller.state()

        self.assertFalse(state.running)
        self.assertFalse(state.active)
        self.assertEqual(state.document_kind, "impress")
        self.assertEqual(state.status_message, "Ready in editing view")
        self.assertEqual(state.current_slide, 2)
        self.assertEqual(state.current_title, "Wrap Up")
        self.assertEqual(state.next_slide, None)
        self.assertFalse(state.can_go_next)
        self.assertEqual(state.elapsed_seconds, 0)

    def test_state_reports_non_impress_documents(self) -> None:
        controller = ImpressController(FakeContext(FakeNonImpressDocument()))

        state = controller.state()

        self.assertFalse(state.running)
        self.assertFalse(state.active)
        self.assertEqual(state.document_kind, "other")
        self.assertIn("not an Impress presentation", state.status_message)
        self.assertEqual(state.slide_count, 0)

    def test_commands_dispatch_to_presentation_and_slideshow(self) -> None:
        slideshow = FakeSlideShowController(current_index=0, slides=self.slides)
        presentation = FakePresentation(slideshow)
        document = FakeDocument(self.slides, presentation, self.slides[0])
        dispatch_helper = FakeDispatchHelper()
        controller = ImpressController(FakeContext(document, dispatch_helper=dispatch_helper))

        controller.command("start_presentation")
        controller.command("pause_presentation")
        controller.command("blank_screen")
        controller.command("resume_presentation")
        controller.command("goto_last_slide")
        controller.command("goto_first_slide")
        controller.command("next_slide")
        controller.command("goto_slide", 2)
        controller.command("end_presentation")

        self.assertFalse(presentation.started)
        self.assertTrue(presentation.ended)
        self.assertEqual(presentation.properties, {})
        self.assertEqual(len(dispatch_helper.calls), 1)
        self.assertEqual(dispatch_helper.calls[0][1], ".uno:PresentationCurrentSlide")
        self.assertEqual(
            slideshow.commands,
            [
                ("pause", None),
                ("blank_screen", 0),
                ("resume", None),
                ("goto_last_slide", None),
                ("goto_slide", 0),
                ("next_slide", None),
                ("goto_slide", 2),
            ],
        )

    def test_start_presentation_falls_back_to_direct_properties_without_args(self) -> None:
        slideshow = FakeSlideShowController(current_index=0, slides=self.slides)
        presentation = FakeLegacyPresentation(slideshow)
        document = FakeDocument(self.slides, presentation, self.slides[0])
        controller = ImpressController(FakeContext(document, dispatch_helper=None))

        controller.command("start_presentation")

        self.assertTrue(presentation.started)
        self.assertEqual(
            presentation.properties,
            {
                "IsFullScreen": True,
                "IsAlwaysOnTop": True,
                "StartWithNavigator": False,
                "Pause": 0,
                "FirstPage": "",
            },
        )

    def test_start_presentation_from_first_slide_selects_slide_zero_before_start(self) -> None:
        slideshow = FakeSlideShowController(current_index=2, slides=self.slides, running=False)
        presentation = FakePresentation(slideshow)
        document = FakeDocument(self.slides, presentation, self.slides[2])
        dispatch_helper = FakeDispatchHelper()
        controller = ImpressController(FakeContext(document, dispatch_helper=dispatch_helper))

        controller.command("start_presentation_from_first_slide")

        self.assertFalse(presentation.started)
        self.assertEqual(document.current_controller.selected_pages, [])
        self.assertEqual(presentation.properties, {})
        self.assertEqual(len(dispatch_helper.calls), 1)
        self.assertEqual(dispatch_helper.calls[0][1], ".uno:Presentation")

    def test_start_presentation_from_first_slide_falls_back_when_dispatch_fails(self) -> None:
        slideshow = FakeSlideShowController(current_index=2, slides=self.slides, running=False)
        presentation = FakePresentation(slideshow)
        document = FakeDocument(self.slides, presentation, self.slides[2])
        dispatch_helper = FakeDispatchHelper(should_fail=True)
        controller = ImpressController(FakeContext(document, dispatch_helper=dispatch_helper))

        controller.command("start_presentation_from_first_slide")

        self.assertTrue(presentation.started)
        self.assertEqual(document.current_controller.selected_pages, [self.slides[0]])
        self.assertEqual(
            presentation.properties,
            {
                "IsFullScreen": True,
                "IsAlwaysOnTop": True,
                "StartWithNavigator": False,
                "Pause": 0,
                "FirstPage": "Agenda",
            },
        )

    def test_state_ignores_placeholder_text_from_notes_page(self) -> None:
        slide = FakeSlide(
            "Agenda",
            ["Agenda"],
            ["Real presenter note", "<number>", "<date/time>", "<footer>"],
        )
        slideshow = FakeSlideShowController(current_index=0, slides=[slide])
        document = FakeDocument([slide], FakePresentation(slideshow), slide)
        controller = ImpressController(FakeContext(document))

        state = controller.state()

        self.assertEqual(state.notes, "Real presenter note")

    def test_slide_navigation_falls_back_to_editing_view(self) -> None:
        document = FakeDocument(self.slides, FakePresentation(None), self.slides[1])
        controller = ImpressController(FakeContext(document))

        controller.command("previous_slide")
        controller.command("goto_slide", 2)

        self.assertEqual(
            document.current_controller.selected_pages,
            [self.slides[0], self.slides[2]],
        )

    def test_state_falls_back_to_controller_slide_object_when_index_is_invalid(self) -> None:
        slideshow = FakeSlideShowController(
            current_index=0,
            slides=self.slides,
            current_slide_override=self.slides[1],
            fail_current_slide_index=True,
        )
        document = FakeDocument(self.slides, FakePresentation(slideshow), self.slides[0])
        controller = ImpressController(FakeContext(document))

        state = controller.state()

        self.assertEqual(state.current_slide, 1)
        self.assertEqual(state.current_title, "Metrics")

    def test_state_uses_controller_next_slide_index_when_available(self) -> None:
        slideshow = FakeSlideShowController(current_index=0, slides=self.slides, next_index=2)
        document = FakeDocument(self.slides, FakePresentation(slideshow), self.slides[0])
        controller = ImpressController(FakeContext(document))

        state = controller.state()

        self.assertEqual(state.next_slide, 2)
        self.assertEqual(state.next_title, "Wrap Up")

    def test_state_tracks_blank_pause_and_end_of_deck_helpers(self) -> None:
        current_time = [100.0]
        slideshow = FakeSlideShowController(current_index=2, slides=self.slides, paused=True)
        document = FakeDocument(self.slides, FakePresentation(slideshow), self.slides[2])
        controller = ImpressController(FakeContext(document), monotonic=lambda: current_time[0])

        controller.state()
        controller.command("blank_screen")
        current_time[0] = 145.0

        state = controller.state()

        self.assertTrue(state.running)
        self.assertTrue(state.paused)
        self.assertTrue(state.blanked)
        self.assertTrue(state.at_end_of_deck)
        self.assertEqual(state.remaining_slides, 0)
        self.assertEqual(state.elapsed_seconds, 45)
        self.assertEqual(state.status_message, "Presentation paused with the projector blanked")

        controller.command("next_slide")
        unblanked_state = controller.state()

        self.assertFalse(unblanked_state.blanked)


if __name__ == "__main__":
    unittest.main()
