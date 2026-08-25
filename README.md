# LinkedIn Campaign Operator

[![Validate public release](https://github.com/sunny-chandel/linkedin-campaign-operator/actions/workflows/ci.yml/badge.svg)](https://github.com/sunny-chandel/linkedin-campaign-operator/actions/workflows/ci.yml)
[![Latest release](https://img.shields.io/github/v/release/sunny-chandel/linkedin-campaign-operator)](https://github.com/sunny-chandel/linkedin-campaign-operator/releases/latest)
[![MIT license](https://img.shields.io/badge/license-MIT-1557ff)](LICENSE)

**Your LinkedIn operating system. Inside your AI agent.**

LinkedIn Campaign Operator is a free, open-source collection of Agent Skills for researching topics, writing LinkedIn posts, planning thoughtful engagement, publishing at evidence-based times, measuring results, and carrying campaign learning across sessions.

**Website:** [linkedin-campaign-operator.sunnychandel73.chatgpt.site](https://linkedin-campaign-operator.sunnychandel73.chatgpt.site)

It runs in Claude Code and Codex, keeps mutable campaign data outside the plugin, and resumes from verified state instead of starting over every day.

## What it does

- researches fresh topics and verifies public claims;
- produces posts, creative briefs, and publication packages;
- ranks engagement opportunities by predicted value;
- operates an adaptive work queue across content, engagement, and analytics;
- tracks followers, connections, post performance, and experiments;
- builds a reusable profile-derived brand and watermark system;
- discovers included premium features and routes useful ones into the workflow;
- stores state, logs, decisions, and learning in auditable JSON artifacts.

The included 10,000-follower and 10,000-connection strategy is the default. Your identity, profile URL, timezone, niche, baselines, and growth goals are configurable.

## The eight skills

| Skill | Role |
| --- | --- |
| `linkedin-campaign-orchestrator` | Governs state, routing, recovery, and next actions |
| `linkedin-content-research` | Finds topics, sources, and defensible claims |
| `linkedin-content-production` | Creates captions, creative briefs, and publish packages |
| `linkedin-engagement-planning` | Scores and prepares high-value engagement actions |
| `linkedin-analytics-learning` | Compares results and updates runtime learning |
| `linkedin-brand-system` | Maintains profile-derived visual identity assets |
| `linkedin-gif-creative-intelligence` | Learns and specifies effective GIF patterns |
| `linkedin-premium-router` | Maps included LinkedIn features to campaign work |

## Install in Claude Code

```text
/plugin marketplace add sunny-chandel/linkedin-campaign-operator
/plugin install linkedin-campaign-operator-v3@sunny-linkedin-tools
```

Then run:

```text
/linkedin-campaign-operator-v3:linkedin-campaign-orchestrator
```

## Install in Codex

```bash
codex plugin marketplace add sunny-chandel/linkedin-campaign-operator
codex plugin add linkedin-campaign-operator-v3@linkedin-campaign-operator
```

Open a new task and ask:

```text
Start my LinkedIn growth campaign.
```

## Initialize campaign state manually

The orchestrator can discover account details from connected Chrome. For a deterministic setup, run:

```bash
python3 plugins/linkedin-campaign-operator-v3/skills/linkedin-campaign-orchestrator/scripts/init_campaign.py \
  campaign-data/linkedin-growth \
  --owner-name "Your Name" \
  --profile-url "https://www.linkedin.com/in/your-handle/" \
  --timezone "Asia/Kolkata" \
  --niche "AI engineering" \
  --followers-goal 10000 \
  --connections-goal 10000
```

Validate it:

```bash
python3 plugins/linkedin-campaign-operator-v3/skills/linkedin-campaign-orchestrator/scripts/validate_campaign.py \
  campaign-data/linkedin-growth
```

## Example prompts

```text
Build today's LinkedIn content and engagement plan.
```

```text
Research two timely AI infrastructure topics and prepare source-backed briefs.
```

```text
Analyze my latest post snapshots and choose the next best campaign action.
```

```text
Resume my campaign from the last verified state and complete the next executable stage.
```

## Development

```bash
python3 -m venv .venv
.venv/bin/pip install pytest pyyaml pillow
.venv/bin/python -m pytest -q
```

For a local Claude Code plugin session:

```bash
claude --plugin-dir /absolute/path/to/linkedin-campaign-operator/plugins/linkedin-campaign-operator-v3
```

See [TESTING.md](TESTING.md) for behavioral acceptance tests and [CONTRIBUTING.md](CONTRIBUTING.md) for the contribution workflow.

## Project structure

```text
plugins/linkedin-campaign-operator-v3/
├── .claude-plugin/plugin.json
├── .codex-plugin/plugin.json
└── skills/
    ├── linkedin-campaign-orchestrator/
    └── seven supporting skills/
```

Each skill uses the open `SKILL.md` convention, progressive disclosure through focused references, and deterministic helper scripts where repeatability matters.

## License

MIT © Sunny Chandel
