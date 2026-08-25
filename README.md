# LinkedIn Campaign Operator for Claude

A Claude plugin for running Sunny Chandel's adaptive organic LinkedIn 10k/10k system.

The plugin contains eight composable Agent Skills:

- `linkedin-campaign-orchestrator`
- `linkedin-content-research`
- `linkedin-content-production`
- `linkedin-engagement-planning`
- `linkedin-premium-router`
- `linkedin-analytics-learning`
- `linkedin-brand-system`
- `linkedin-gif-creative-intelligence`

Version 0.6.0 adds one-time campaign-lifetime consent, automatic consent reload across model and session changes, pinned-browser reuse, expiring task leases and checkpoints, crash self-revival, transactional IST rollover, lane circuit breakers, adaptive reserve sizing and pass limits, starvation prevention, and reusable pre-flight evidence. It retains the shared 100-action base ceiling, direct-inbound overage, bursts capped at 10, qualified reciprocity, exactly two dynamically timed daily posts, branding, GIF intelligence, subscription optimization, and evidence-based learning.

## Install from the marketplace

Add this repository as a marketplace in Claude using:

```text
sunny-chandel/linkedin-campaign-operator
```

Then install `linkedin-campaign-operator-v3` from the `sunny-linkedin-tools` marketplace. In Claude Code, the equivalent commands are:

```text
/plugin marketplace add sunny-chandel/linkedin-campaign-operator
/plugin install linkedin-campaign-operator-v3@sunny-linkedin-tools
```

Invoke the parent skill with:

```text
/linkedin-campaign-operator-v3:linkedin-campaign-orchestrator
```

The parent starts Sunny Chandel's preconfigured organic LinkedIn system for 10,000 followers and 10,000 connections. On the first run it asks one automation-consent question and stores the resulting receipt. Later sessions self-revive from durable state without asking again, reconcile missed work and IST rollover, reuse the pinned verified browser and valid pre-flight evidence, and route automatically through the seven supporting skills. It does not open a generic campaign-setup form or use fixed engagement clusters.

When an installed update becomes available to an already-running Claude Desktop session, the orchestrator resolves and directly loads the newest installed skill instructions at its next dispatcher wake or stage boundary, records the newest cache path, migrates state, terminates legacy fixed-sleep behavior, and continues without restarting. `/reload-plugins` is used only in clients that explicitly expose that command.

## Install for development

```bash
claude --plugin-dir /absolute/path/to/linkedin-campaign-operator/plugins/linkedin-campaign-operator-v3
```

Then invoke:

```text
/linkedin-campaign-operator-v3:linkedin-campaign-orchestrator
```

See [TESTING.md](TESTING.md) for safe first-run and trigger tests.

## Standards

The package follows the Claude plugin layout and open Agent Skills format. Every skill uses a `SKILL.md` entrypoint with progressive disclosure through focused references, assets, and deterministic helper scripts.
