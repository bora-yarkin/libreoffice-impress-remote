<!-- SPDX-FileCopyrightText: 2026 Bora Yarkın -->
<!-- SPDX-License-Identifier: GPL-3.0-only -->

# Python Companion Shell

This is the first source implementation of the cross-suite companion shell. It
starts a loopback-only setup page in the default browser and shuts down when the
page's **Quit companion** button is used. It has no office connector, phone
listener, or runtime third-party dependency. Its local page follows the
browser's English or Turkish language preference. Companion strings are kept
separate from LibreOffice's packaged catalogs in this initial shell.

## Run from a virtual environment

From the repository root:

```sh
python3 -m venv companion/.venv
companion/.venv/bin/python -m pip install -e ./companion
companion/.venv/bin/impress-remote-companion
```

On Windows PowerShell, use `companion\.venv\Scripts\python.exe` and
`companion\.venv\Scripts\impress-remote-companion.exe` for the corresponding
commands.

The browser page listens only on IPv4 loopback at an OS-assigned port. It does
not accept phone or office traffic. The per-run shutdown token is delivered to
the same-origin page and is never placed in the URL or logs. If the browser
cannot be opened, the local page address is printed to stderr.
Press Ctrl+C in the terminal to stop the companion if the setup page is not
available.

The local HTTP surface is limited to `GET /`, its packaged CSS/JavaScript and
locale files, `GET /api/session`, and `POST /api/shutdown`. The shutdown request
must have an empty body, the exact setup-page origin, and the per-run token in
`X-Companion-Token`. Other paths are not served, and no cross-origin access is
enabled.

This source package is not yet frozen into standalone OS installers. The
packaging tool and platform builds remain a separate decision in the
[cross-suite plan](../docs/cross-suite-companion-plan.md). ONLYOFFICE and
Euro-Office host behavior remains unverified while live checks are deferred.
