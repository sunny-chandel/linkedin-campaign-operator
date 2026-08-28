# State and recovery

Store the recognized owner, full profile URL, campaign goals, working limits, regions, content preferences, and stop state in durable campaign configuration. A new campaign records these settings once from the owner's start request and verified profile evidence.

Every resume reloads the newest installed plugin, campaign configuration, canonical evidence, content pipeline, repair state, work queue, stage ledger, analytics, learning, experiments, subscription state, and brand assets.

Lifecycle states are `ready`, `running`, `recovering`, `waiting`, `completed`, and `owner-stopped`. Derive the current state from saved evidence.

On restart, expire abandoned local task claims, verify unclear service results, recalculate due work, refresh stale packages, and resume from the last confirmed checkpoint. Capability failures preserve the current task and next retry trigger while unaffected local work continues.

Completion requires the configured goal formula and reproducible evidence, or an explicit owner stop.
