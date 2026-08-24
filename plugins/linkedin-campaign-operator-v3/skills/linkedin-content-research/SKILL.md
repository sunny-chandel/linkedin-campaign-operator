---
name: linkedin-content-research
description: Research fresh LinkedIn campaign topics, primary sources, platform changes, and credible trends. Use when creating research briefs or checking claims and algorithm advice.
compatibility: Requires internet access. Use current direct sources and respect site access rules.
metadata:
  author: sunny
  version: "0.3.2"
---

# LinkedIn content research

Produce evidence-ranked research briefs for the campaign. Do not draft the final post until the brief is complete.

## Automated execution

In automated mode, start immediately when routed by the parent orchestrator. Never ask the owner to choose a topic, niche, audience, region, source, or angle. Read them from campaign state and the connected profile; if an optional value is unavailable, infer it from verified recent evidence or record it as `unknown` and continue. If a preferred source is unavailable, try another primary source and then the strongest credible alternative. Return the best fact-checked brief possible with uncertainty clearly marked. Escalate only when no usable evidence can be obtained after safe recovery and a truthful publication package cannot be produced.

## Workflow

1. Read the target audience, region, content pillars, exclusions, previous topics, and open experiments from campaign state.
2. Search fresh primary sources first: official changelogs, engineering posts, research papers, arXiv, product documentation, release notes, and original repositories.
3. Separately check what is currently receiving credible attention in the niche.
4. Distinguish the event date from the publication date.
5. Confirm every material claim from the original source when possible.
6. Record conflicting evidence and uncertainty instead of forcing a conclusion.
7. Reject recycled topics, unsupported statistics, anonymous algorithm hacks, and engagement-pod advice.
8. Produce a structured research brief using [source hierarchy](references/source-hierarchy.md).

## Research brief contract

Return:

- proposed topic and region;
- why it matters now;
- intended professional audience;
- primary-source URLs and dates;
- verified claims;
- claims that must not be stated as fact;
- competing interpretation;
- recommended post angle;
- suitable asset concept;
- experiment opportunity, if any;
- confidence level and recheck date.

Do not treat popularity as evidence of truth. Use the connected Chrome session when LinkedIn information is needed.
