# Changelog

## 5.0.4 — Agent-neutral runtime classification

- made Claude, Codex, and other compatible agents use one durable lifecycle-classification contract;
- made lane recovery clear stale intervention requirements and recalculate the lifecycle state;
- exposed persisted runtime classification in campaign status and self-revival results;
- added regression coverage for identical recovered-state interpretation across agents.

## 5.0.3 — Pinned-browser continuity

- made an exact stored Chrome device ID authoritative across fresh sessions;
- required direct browser selection with the pinned ID instead of an interactive device picker;
- made display-label changes and unrelated connected devices non-ambiguous;
- added release-contract coverage for zero-question pinned-browser reuse.

## 5.0.2 — Deterministic rejection and restart reconciliation

- made candidate qualification mandatory before drafting or surfacing an engagement action;
- made failed gates and sub-65 scores automatic rejections that continue discovery without owner escalation;
- added machine-readable `owner_input_required` and `next_step` ranker directives;
- reconciled pending publication stages from verified publication evidence after a restart;
- added regression coverage for below-gate autonomous rejection and evidence-backed publication recovery.

## 1.1.0 — Reliable autonomous recovery

- added a campaign-lifetime consent receipt that reloads across model, client, and machine restarts;
- added deterministic session self-revival, downtime detection, task leases, checkpoints, retry backoff, and missed-work reconciliation;
- added campaign-local transactional day rollover so stale publication counters cannot block a new day;
- added pinned-browser reuse, reusable pre-flight evidence, lane circuit breakers, and automatic offline fallback;
- added adaptive reserve sizing, bounded discovery passes, and anti-starvation task rotation;
- generalized the recovery runtime to each campaign's configured owner, profile, timezone, and required regions;
- added restart, consent persistence, browser recovery, circuit breaker, reserve, and rollover acceptance tests.

## 1.0.0 — Public release

- converted the original single-owner campaign into a reusable public operator;
- added configurable owner, profile, timezone, niche, baselines, and growth goals;
- added a Codex plugin manifest and repository marketplace;
- retained Claude Code marketplace installation;
- changed campaign day accounting to use the configured local timezone;
- added public documentation, examples, website, launch assets, and an MIT license;
- added acceptance coverage for custom public campaign initialization.

## 0.5.0

- introduced continuous adaptive dispatch, reciprocity, dynamic publishing, runtime instruction refresh, pipeline audits, and persistent learning.
