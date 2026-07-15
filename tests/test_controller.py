# SPDX-FileCopyrightText: 2026 Bora Yarkın
# SPDX-License-Identifier: GPL-3.0-only

import unittest

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
    def __init__(self, current_index: int, slides: list[FakeSlide]):
        self.current_index = current_index
        self.slides = slides
        self.commands: list[tuple[str, int | None]] = []

    def getCurrentSlideIndex(self) -> int:
        return self.current_index

    def getCurrentSlide(self):
        return self.slides[self.current_index]

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


class FakePresentation:
    def __init__(self, controller):
        self.controller = controller
        self.started = False
        self.ended = False

    def getController(self):
        return self.controller

    def start(self) -> None:
        self.started = True

    def end(self) -> None:
        self.ended = True


class FakeCurrentController:
    def __init__(self, slide):
        self.slide = slide

    def getCurrentPage(self):
        return self.slide


class FakeDocument:
    def __init__(self, slides: list[FakeSlide], presentation, current_page):
        self.draw_pages = FakeDrawPages(slides)
        self.presentation = presentation
        self.current_controller = FakeCurrentController(current_page)

    def getDrawPages(self):
        return self.draw_pages

    def getPresentation(self):
        return self.presentation

    def getCurrentController(self):
        return self.current_controller


class FakeDesktop:
    def __init__(self, document):
        self.document = document

    def getCurrentComponent(self):
        return self.document


class FakeServiceManager:
    def __init__(self, document):
        self.document = document

    def createInstanceWithContext(self, _service_name: str, _ctx):
        return FakeDesktop(self.document)


class FakeContext:
    def __init__(self, document):
        self.document = document

    def getServiceManager(self):
        return FakeServiceManager(self.document)


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
        controller = ImpressController(FakeContext(document))

        state = controller.state()

        self.assertTrue(state.running)
        self.assertEqual(state.current_slide, 1)
        self.assertEqual(state.slide_count, 3)
        self.assertEqual(state.current_title, "Metrics")
        self.assertEqual(state.notes, "Focus on churn")
        self.assertEqual(state.next_slide, 2)
        self.assertEqual(state.next_title, "Wrap Up")
        self.assertIn("Wrap Up", state.next_preview)
        self.assertTrue(state.can_go_previous)
        self.assertTrue(state.can_go_next)

    def test_state_falls_back_to_editing_view_when_slideshow_is_not_running(self) -> None:
        document = FakeDocument(self.slides, FakePresentation(None), self.slides[2])
        controller = ImpressController(FakeContext(document))

        state = controller.state()

        self.assertFalse(state.running)
        self.assertEqual(state.current_slide, 2)
        self.assertEqual(state.current_title, "Wrap Up")
        self.assertEqual(state.next_slide, None)
        self.assertFalse(state.can_go_next)

    def test_commands_dispatch_to_presentation_and_slideshow(self) -> None:
        slideshow = FakeSlideShowController(current_index=0, slides=self.slides)
        presentation = FakePresentation(slideshow)
        document = FakeDocument(self.slides, presentation, self.slides[0])
        controller = ImpressController(FakeContext(document))

        controller.command("start_presentation")
        controller.command("next_slide")
        controller.command("goto_slide", 2)
        controller.command("end_presentation")

        self.assertTrue(presentation.started)
        self.assertTrue(presentation.ended)
        self.assertEqual(slideshow.commands, [("next_slide", None), ("goto_slide", 2)])
