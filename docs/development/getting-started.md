<!-- SPDX-FileCopyrightText: 2026 Bora Yarkın -->
<!-- SPDX-License-Identifier: GPL-3.0-only -->

# Getting Started

```bash
git clone https://github.com/bora-yarkin/libreoffice-impress-remote.git
cd libreoffice-impress-remote
python -m venv .venv
. .venv/bin/activate
pip install -e '.[dev,security]' -e './server[dev]'
make test
make oxt
```
