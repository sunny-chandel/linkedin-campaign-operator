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

It separates versioned skill instructions from mutable campaign state, refreshes running-session instructions when the installed plugin changes, validates target and consent configuration, enforces adaptive engagement limits and cooldown rules, generates profile-derived watermark assets, learns GIF construction from current creator references, optimizes already-active LinkedIn subscriptions, and maintains runtime learning.

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

The parent starts Sunny Chandel's preconfigured organic LinkedIn system for 10,000 followers and 10,000 connections. It checks connected Chrome first, verifies the fixed LinkedIn identity, checks Claude Design and file upload, refreshes the profile-derived watermark kit, discovers account and subscription state, calculates the best use of verified included features, and routes automatically through the seven supporting skills. It does not open a generic campaign-setup form.

When an installed update becomes available to an already-running Claude Desktop session, the orchestrator resolves and directly loads the newest installed skill instructions at its next scheduled wake or stage boundary, records the newest cache path, migrates state, and continues without restarting. `/reload-plugins` is used only in clients that explicitly expose that command.

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
