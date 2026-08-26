# State, consent, and recovery

## Recognized owner

The recognized owner is the person controlling the trusted agent session and named in `consent-record.json`. Their LinkedIn identity and full profile URL are discovered during pre-flight or supplied to the initializer, then stored in the record.

## One-time stored consent

When no valid active receipt exists, the parent tells the recognized owner that it will run pre-flight and then operate the fixed system autonomously, asks one direct consent question, and records the answer through `runtime_control.py consent-grant`. Invoking a child skill never creates a second consent step.

`consent-record.json` is authoritative across context compression, model changes, application restarts, and later compatible-agent sessions. Conversation memory is not authoritative. Every startup and dispatch reloads the record, validates its fingerprint, and mirrors its receipt into `campaign-state.json`. An active campaign-lifetime receipt disables routine reconfirmation until the owner revokes it, the record becomes invalid or unavailable, or the verified account identity changes.

The record identifies:

- campaign and owner;
- target formula and completion evidence;
- accounts and Pages;
- action classes;
- continuous 24-hour adaptive dispatch, a shared 100-action base ceiling, a 10-action burst cap, and direct-inbound reply overage;
- exactly two prepared and published packages per local content day with dynamic timing and no fixed separation;
- automatic profile-derived watermark creation and application;
- per-post GIF-pattern promotion and permanent dominant-pattern deletion;
- premium products and persistent settings;
- data storage;
- owner stop signals;
- consent version and activation timestamp.

Research, design, LinkedIn reading, publishing, comments, replies, DMs, reactions, queue work, analytics, and logging need no repeated approval after the recognized owner starts the system.

Do not describe a browser reconnect, pre-flight refresh, content preview, subskill transition, retry, recovery, or session restart as requiring fresh consent. A technical login, account-identity, or capability failure may require owner intervention when automatic recovery is exhausted, but clearing it does not create a new campaign-consent ceremony.

## Restart recovery

Every new or resumed session runs `resume_campaign.py` before ordinary dispatch. It reloads consent, calculates downtime from the last heartbeat, reopens abandoned task leases, reconciles the current campaign-local day, discovers missing tasks from durable artifacts, and records a recovery event. Safe unfinished work resumes from its latest checkpoint. Completed external mutations remain completed. Obsolete prior-day publication or engagement work is closed with a reason instead of being replayed; current-day replacements are created automatically.

## Failure classification

Classification is runtime-neutral. Claude, Codex, and any other compatible agent use the same deterministic state transition and the persisted `runtime_classification` record. Model identity, client name, transcript phrasing, and an agent's subjective caution cannot change the result. A recovered lane must be `ready`, have a `closed` circuit, zero consecutive failures, and `intervention_required: false`; stale contradictory flags are invalid state and must be reconciled before dispatch.

Recoverable:

- temporary network or page failure;
- transient tool timeout;
- optional premium feature unavailable;
- stale browser state;
- safely retryable export failure;
- missed publication opportunity or mandatory stage;
- incomplete analytics;
- temporary source outage.

Technical recovery requiring owner action:

- wrong login or account identity mismatch after automatic recovery;
- wrong account or Page;
- required capability unavailable after safe recovery;
- target becomes impossible or unmeasurable;
- authoritative consent or campaign state is lost.

## Recovery procedure

1. Save the last confirmed action and observed outcome.
2. Verify whether an external mutation succeeded before retrying.
3. Retry only idempotent or clearly failed operations.
4. Use at most two safe retries for the same transient operation, then open the lane circuit and schedule an automatic probe while other work continues.
5. Never repeat an ambiguous post, comment, message, or invitation.
6. Keep offline work moving while the LinkedIn lane is unavailable, then resume that lane automatically when Chrome or LinkedIn is restored.
7. Run the dispatcher immediately after recovery. Do not make up missed volume or manufacture actions.

## Completion

Completion requires the configured target formula to evaluate true and the evidence fields to be populated. A forecast, estimate, or single UI snapshot that cannot be reproduced is insufficient.
