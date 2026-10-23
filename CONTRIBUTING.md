# Contributing to PassAD

English and Turkish contributions are welcome. Keep each change focused and explain the administrator or end-user problem it solves.

## Before opening a pull request

1. Read the current scope and operational notes in [README.md](README.md).
2. For a substantial behavior change, open an issue describing the intended result before implementing it.
3. Work on a branch or fork and keep unrelated formatting, dependency updates, and feature work separate.
4. Use an isolated AD test domain, disposable test accounts, synthetic user data, and a test SMTP recipient.

Never include `.env`, service passwords, session signing secrets, live reset tokens, production logs, or real directory exports in patches, screenshots, or issue reports. Email redirection does not prevent AD password writes.

## Development and validation

Dependencies are listed in `requirements.txt`; the Docker images use Python 3.10. The checked-in Compose configuration is the reference for the current runtime and environment-variable wiring.

There is no checked-in automated test suite or CI workflow at present. Do not invent a passing-test or coverage claim. For a code change, state exactly what you checked and what remains untested. Add focused automated tests when introducing testable behavior, and keep them independent of production AD and SMTP.

For documentation-only changes, verify the referenced file paths, configuration names, and commands against the checked-in source. Run `git diff --check` before submitting.

## Reporting a bug

Include the revision, runtime/Compose versions, expected behavior, actual behavior, and minimal reproduction steps. Use a synthetic account and a redacted error excerpt. State whether the problem concerns directory lookup, user password change, administrator reset, email delivery, or scheduling.

For security-sensitive details, use GitHub private vulnerability reporting if it is enabled. Do not file live credentials or exploit details affecting a real deployment in a public issue. A private contact and disclosure policy still need to be established.

## Pull request description

Explain the trigger and resulting behavior, the affected files, how you validated the change, and any deployment or data-migration impact. Keep future roadmap proposals separate from features that the patch actually implements.

By contributing, you agree that your contributions are provided under this repository's [MIT license](LICENSE). Preserve applicable third-party notices and identify the origin of any reused code.
