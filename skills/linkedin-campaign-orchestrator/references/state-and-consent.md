# State, consent, and recovery

## Recognized owner

The recognized owner is the person controlling the trusted Claude session and named in `consent-record.json`. The fixed LinkedIn identity is Sunny Chandel at `https://www.linkedin.com/in/sunny-chandel-6a05bb401/`.

## Stored consent

Invoking the parent skill or explicitly telling it to start activates and stores consent for the fixed system. The record identifies:

- campaign and owner;
- target formula and completion evidence;
- accounts and Pages;
- action classes;
- fixed windows and counts;
- premium products and persistent settings;
- data storage;
- owner stop signals;
- consent version and activation timestamp.

Research, design, LinkedIn reading, publishing, comments, replies, DMs, reactions, queue work, analytics, and logging need no repeated approval after the recognized owner starts the system.

## Failure classification

Recoverable:

- temporary network or page failure;
- transient tool timeout;
- optional premium feature unavailable;
- stale browser state;
- safely retryable export failure;
- missed window;
- incomplete analytics;
- temporary source outage.

Hard blocker:

- interactive verification, technical signal, access message, wrong login, or identity mismatch;
- wrong account or Page;
- required capability unavailable after safe recovery;
- target becomes impossible or unmeasurable;
- authoritative consent or campaign state is lost.

## Recovery procedure

1. Save the last confirmed action and observed outcome.
2. Verify whether an external mutation succeeded before retrying.
3. Retry only idempotent or clearly failed operations.
4. Use at most two safe retries for the same transient operation before choosing a fallback or classifying it as blocked.
5. Never repeat an ambiguous post, comment, message, or invitation.
6. Resume at the next valid window. Do not make up missed volume later.

## Completion

Completion requires the configured target formula to evaluate true and the evidence fields to be populated. A forecast, estimate, or single UI snapshot that cannot be reproduced is insufficient.
