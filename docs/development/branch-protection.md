<!-- SPDX-FileCopyrightText: 2026 Bora Yarkın -->
<!-- SPDX-License-Identifier: GPL-3.0-only -->

# Branch Protection

Recommended `main` protection:

- require pull request before merge
- require CODEOWNERS review
- require status checks
- require branches to be up to date before merge
- require conversation resolution
- block force pushes
- block deletions
- require signed commits when practical

Recommended required checks:

```text
Product CI / Python Lint And Tests
Product CI / Build Extension Package
Product CI / Security And Supply Chain Checks
GitHub Native Security / CodeQL
GitHub Native Security / OpenSSF Scorecard
```

The current connector can write repository files, branches, commits, PRs, and issues, but repository settings and branch protection may still need to be applied manually in GitHub settings.
