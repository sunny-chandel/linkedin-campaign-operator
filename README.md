# LinkedIn Campaign Operator for Claude

A Claude plugin for running Sunny Chandel's automated organic LinkedIn 10k/10k system.

The plugin contains six composable Agent Skills:

- `linkedin-campaign-orchestrator`
- `linkedin-content-research`
- `linkedin-content-production`
- `linkedin-engagement-planning`
- `linkedin-premium-router`
- `linkedin-analytics-learning`

It separates immutable skill instructions from mutable campaign state, validates target and consent configuration, enforces qualification and cooldown rules, and maintains a versioned runtime-learning ledger.

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

The parent starts Sunny Chandel's preconfigured organic LinkedIn system for 10,000 followers and 10,000 connections. It checks connected Chrome first, verifies the fixed LinkedIn identity, checks Claude Design and file upload, discovers account state, and routes automatically through the five supporting skills. It does not open a generic campaign-setup form.

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
