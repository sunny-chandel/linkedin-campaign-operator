# Architecture

LinkedIn Campaign Operator separates versioned instructions from mutable campaign state.

```text
orchestrator
├── research → production → publication package
├── engagement planning → ranked action queue
├── premium router → feature utilization plan
├── analytics learning → experiments and strategy weights
├── brand system → reusable identity assets
└── GIF intelligence → creative pattern library
```

The orchestrator owns lifecycle state, pre-flight, routing, recovery, and completion. Supporting skills produce bounded artifacts and return control to the orchestrator.

Campaign state is ordinary JSON and JSONL outside the plugin. This makes execution inspectable, resumable, migratable, and testable. Deterministic scripts validate schemas, rank candidates, select opportunities, migrate older state, audit pipeline completion, and produce status summaries.

The dispatcher chooses work from evidence rather than a fixed checklist. It prioritizes blockers, direct inbound, publication opportunities, recovery debt, qualified reciprocity, queue replenishment, content production, and analytics. A wait decision is valid only after the pipeline audit finds no executable or recoverable work.
