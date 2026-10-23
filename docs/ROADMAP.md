# Proposed roadmap

This is a proposed backlog, not a release schedule or a description of features already available in the public repository. Individual changes need implementation, validation, and review.

## Make the public revision easier to maintain

- Add isolated tests for token expiry, replacement, and single-use behavior.
- Add mocked AD and SMTP tests for successful, partial, and failed operations.
- Add CI that runs those tests without production credentials.
- Establish a private security reporting channel and disclosure process.
- Document versioned releases and migration requirements.

## Improve the administrator workflow

- Search users by name, username, and email; filter by password-expiry state.
- Keep the selected user and filter context after an action.
- Show the target identity, recipient, and consequence before a password reset.
- Distinguish connection errors, loading, empty results, and action failures.
- Add date and username filters to audit logs.

## Evaluate a broader architecture

- Publish and document a reviewed multi-domain implementation.
- Evaluate PostgreSQL persistence and a dedicated scheduler lifecycle.
- Define how configuration updates are propagated across web workers and scheduler processes.
- Provide a migration path from the current SQLite deployment before replacing it.

Any publication of an existing deployment's implementation must first remove operational secrets, private directory data, and environment-specific network configuration.
