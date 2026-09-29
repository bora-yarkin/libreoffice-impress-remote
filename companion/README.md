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

## Build a standalone bundle

The PyInstaller build tool is isolated in the companion's `build` dependency
group; it is not installed as a runtime dependency. From the repository root,
run these commands on the target operating system and CPU architecture:

```sh
uv run --locked --package impress-remote-companion --group build python tools/build_companion.py
uv run --locked --package impress-remote-companion --group build python tools/verify_companion_bundle.py
```

On macOS or Linux, `make package-companion` is a shortcut for the build step.
The one-folder bundle is written to
`dist/companion/impress-remote-companion/`. It includes Python and the
companion's packaged page assets, so the target computer does not need Python.
Build on each target operating system and CPU architecture. GitHub Actions is
configured to build and launch-check bundles for Linux x64 on Ubuntu 22.04,
Windows x64, and both Intel and Apple Silicon macOS runners. The Ubuntu baseline
improves compatibility with newer systems that provide compatible glibc
versions; it does not guarantee support for every Linux distribution.

The bundle is an unpacked executable directory, not an installer or signed
release. To launch it without opening a browser automatically, run the
executable with `--no-browser`; it prints the setup page address to stderr.

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

ONLYOFFICE and Euro-Office host behavior remains unverified while live checks
are deferred. Bundle creation does not establish office-suite compatibility.
