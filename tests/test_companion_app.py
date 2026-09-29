# SPDX-FileCopyrightText: 2026 Bora Yarkın
# SPDX-License-Identifier: GPL-3.0-only

from unittest.mock import Mock

from impress_remote_companion import app


def test_main_disables_browser_when_requested(monkeypatch) -> None:
    server = object()
    run = Mock(return_value=0)
    monkeypatch.setattr(app, "create_local_control_server", lambda: server)
    monkeypatch.setattr(app, "run", run)

    assert app.main(["--no-browser"]) == 0

    run.assert_called_once_with(server, open_browser=False)


def test_main_opens_browser_by_default(monkeypatch) -> None:
    server = object()
    run = Mock(return_value=0)
    monkeypatch.setattr(app, "create_local_control_server", lambda: server)
    monkeypatch.setattr(app, "run", run)

    assert app.main([]) == 0

    run.assert_called_once_with(server, open_browser=True)
