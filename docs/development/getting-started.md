<!-- SPDX-FileCopyrightText: 2026 Bora Yarkın -->
<!-- SPDX-License-Identifier: GPL-3.0-only -->

# Getting Started

```bash
git clone https://github.com/bora-yarkin/libreoffice-impress-remote.git
cd libreoffice-impress-remote
make venv
make sdk-download
make test
make oxt
```

On macOS, `make sdk-download` downloads the matching LibreOffice SDK disk image from the official archive and installs its SDK directory into `third_party/libreoffice-sdk/`.
