# Official-API executor service

Use this reference when configuring or diagnosing the campaign's external executor service.

## Boundary

The interactive host and the external executor have separate responsibilities. Claude Desktop reads evidence, prepares validated canonical work, and atomically writes local outbox records. It performs no LinkedIn write action. A separately configured official-API service owns API submission, read verification, durable evidence, and retries. This architecture keeps externally visible activity outside the interactive chat boundary.

The operating receipt configures the local dispatcher; it is not a substitute for interactive-host confirmation because the host is never assigned an external action. If a task cannot be represented as a validated local outbox request for the ready executor, keep it outside executable supply. Never fall back to browser clicks or direct interactive-host API calls.

The supported executor mode is `official-linkedin-api`. `external-executor.json` stores environment-variable names and macOS Keychain coordinates; access tokens remain in the Keychain-backed credential layer. A LinkedIn developer application, one three-legged OAuth credential grant, and the matching LinkedIn scopes are platform setup prerequisites. Production readiness requires:

- an active service with `unattended: true`;
- `interactive_fallback_enabled: false`;
- a verified actor identity matching the consented LinkedIn account;
- a write scope (`w_member_social` or `w_member_social_feed`);
- a read scope (`r_member_social` or `r_member_social_feed`) so external outcomes can be verified before durable accounting;
- coverage for every dispatched action class;
- programmatic refresh credentials, because a static access token cannot support continuous service operation;
- a running single-instance outbox daemon backed by Keychain so it survives Claude task and Mac process restarts;
- successful verification evidence in the executor artifact.

After the initial OAuth material is available in environment variables, copy it into Keychain with `python scripts/bootstrap_executor_credentials.py <state-dir>`, then run `python scripts/executor_preflight.py <state-dir>`. Preflight introspects the token, verifies the actor, derives exact scope coverage, and records no secrets. Run `python scripts/executor_readiness.py <state-dir> --require-all` at startup and after any credential, scope, identity, or executor change.

After the dispatcher leases a covered task, run `python scripts/enqueue_external_action.py <state-dir> --task-id <task-id>`. This derives the canonical action from the leased task and validated package, validates its lease and idempotency key, and atomically writes it to `external-action-outbox/pending`. The interactive task then returns to the dispatcher. `autonomous_executor_daemon.py` claims the file, executes through `execute_external_action.py`, verifies through the read API, and persists campaign completion evidence. Install the daemon after Keychain-backed readiness passes with `python scripts/install_executor_service.py <state-dir>`.

## Capability rules

The official member social API can cover publication, comment, nested reply, and reaction when the configured LinkedIn application has the required access scopes. Connection invitations, ordinary member direct messages, and follows are outside the public member-social action set used by this adapter, so executable reserve and target supply contain only the covered classes.

Read-only discovery, research, analytics preparation, content production, asset generation, ranking, cooldown checks, and duplicate checks continue while executor setup is pending. Emit `executor_state: setup-pending` with machine-readable missing capabilities, park that lane, and return to other eligible dispatcher work.

## Exactly-once behavior

Every mutation requires an idempotency key. Atomic directory moves provide one daemon claim; a filesystem lock prevents competing daemon instances. The executor writes `external-executor-events.jsonl` before network submission and after verification. A verified key is terminal. A timeout, server-side 5xx after submission, or lost response is `ambiguous`; the daemon moves it to the ambiguous outbox and checkpoints the source lease until the original outcome is known. Media upload ambiguity may be retried because it cannot itself create a public post; the publication mutation begins only after the media asset is available.

## Token lifecycle boundary

Marketing Developer Platform partners with programmatic refresh access can use refresh tokens. Access tokens normally last 60 days and refresh tokens normally last one year. The daemon refreshes access tokens through the stored refresh grant. After refresh-token expiry or revocation, the OAuth grant enters its renewal route. Persist that platform lifecycle event as `oauth-renewal-required`.
