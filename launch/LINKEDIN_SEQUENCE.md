# LinkedIn launch sequence

## Post 1 — Founder story

I stopped treating LinkedIn as a blank text box.

I built it like an operating system.

Today I’m open-sourcing LinkedIn Campaign Operator: eight Agent Skills that research, write, plan engagement, measure results, and remember the campaign across sessions.

It started as my own 10k followers / 10k connections system. Now anyone can configure it for their profile, timezone, niche, and goals.

Works with Claude Code and Codex. Free. MIT licensed.

Your LinkedIn operating system. Inside your AI agent.

GitHub: {{url}}

Comment “operator” and I’ll send the one-minute install path.

## Post 2 — Product demonstration

Most AI LinkedIn tools answer one question:

“What should I post?”

This one answers a harder question:

“What is the next useful action in the whole campaign?”

LinkedIn Campaign Operator keeps state for research, content packages, engagement queues, analytics, experiments, blockers, and verified actions.

Then it routes the next stage to one of eight specialized skills.

Here is the full install-to-first-action flow: {{demo_url}}

## Post 3 — Architecture

The design decision that changed this project:

Skills are versioned. Campaign learning is mutable.

So I keep instructions in the plugin and state in ordinary JSON/JSONL outside it.

That means the operator can:

- resume after a new session
- migrate old campaigns
- audit incomplete stages
- avoid repeating ambiguous actions
- learn without silently rewriting itself

The architecture and code are open: {{url}}

## Post 4 — Eight skills carousel caption

One LinkedIn campaign. Eight specialist agents.

1. Orchestrator
2. Content research
3. Content production
4. Engagement planning
5. Analytics learning
6. Brand system
7. GIF intelligence
8. Premium router

Save this carousel, install the operator, and choose the first workflow you want to run.

{{url}}

## Post 5 — Community invitation

LinkedIn Campaign Operator is now public.

The best next features will come from real campaigns.

Try one prompt. Share the artifact it produced. Open an issue for the workflow you want next.

Good first contributions are labeled. Examples and architecture docs are live. The first community case studies will be featured on the site.

Start here: {{url}}
