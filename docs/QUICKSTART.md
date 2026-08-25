# Quickstart

## One-minute path

Install the marketplace and plugin for your agent, connect a Chrome session already signed in to LinkedIn, then say:

```text
Start my LinkedIn growth campaign. Discover my profile details, initialize campaign state, and execute the next valid stage.
```

The orchestrator reads the connected profile, creates state under `campaign-data/`, validates it, and routes the next task to the appropriate supporting skill.

## Deterministic setup

Use the initializer when you want every starting value to be explicit:

```bash
python3 plugins/linkedin-campaign-operator-v3/skills/linkedin-campaign-orchestrator/scripts/init_campaign.py \
  campaign-data/my-linkedin-growth \
  --campaign-id my-linkedin-growth \
  --owner-name "Your Name" \
  --profile-url "https://www.linkedin.com/in/your-handle/" \
  --timezone "Europe/London" \
  --niche "Your professional niche" \
  --followers-baseline 1200 \
  --connections-baseline 2400 \
  --followers-goal 10000 \
  --connections-goal 10000
```

Run the validator before execution:

```bash
python3 plugins/linkedin-campaign-operator-v3/skills/linkedin-campaign-orchestrator/scripts/validate_campaign.py \
  campaign-data/my-linkedin-growth
```

## Resume

```text
Resume my LinkedIn campaign from its last verified state. Audit the pipeline and execute the highest-priority valid task.
```

## Inspect status

```bash
python3 plugins/linkedin-campaign-operator-v3/skills/linkedin-campaign-orchestrator/scripts/campaign_status.py \
  campaign-data/my-linkedin-growth
```
