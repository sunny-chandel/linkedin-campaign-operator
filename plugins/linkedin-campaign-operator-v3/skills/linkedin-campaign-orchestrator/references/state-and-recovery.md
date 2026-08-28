# State and recovery

Store the recognized owner, full profile URL, campaign goals, working limits, regions, content preferences, and stop state in durable campaign configuration. A new campaign records these settings once from the owner's start request, verified profile evidence, packaged defaults, and values recorded as unknown.

Routine startup must be evidence-driven. Reuse the saved browser binding. For a new personal campaign, select the connected device matching the current host platform, verify the signed-in personal profile read-only, and save the binding. Detect connected-service availability from capability evidence. Missing optional preferences use packaged defaults or remain unknown; they do not stop the next useful local task.

Every resume reloads the newest installed plugin, campaign configuration, canonical evidence, content pipeline, repair state, work queue, stage ledger, analytics, learning, experiments, subscription state, and brand assets.

Lifecycle states are `ready`, `running`, `recovering`, `waiting`, `completed`, and `owner-stopped`. Derive the current state from saved evidence.

On restart, expire abandoned local task claims, verify unclear service results, recalculate due work, refresh stale packages, and resume from the last confirmed checkpoint. Capability failures preserve the current task and next retry trigger while unaffected local work continues.

Completion requires the configured goal formula and reproducible evidence, or an explicit owner stop.
