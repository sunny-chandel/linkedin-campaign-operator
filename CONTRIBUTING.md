# Contributing

Contributions that make LinkedIn Campaign Operator more reusable, observable, or effective are welcome.

## Start here

1. Fork the repository and create a focused branch.
2. Create a virtual environment and install the test dependencies from the README.
3. Make one coherent change and add deterministic tests for behavioral changes.
4. Run `.venv/bin/python -m pytest -q`.
5. Open a pull request explaining the user problem, the change, and the evidence that it works.

## Skill changes

- Keep `SKILL.md` concise and move detailed contracts into `references/`.
- Keep mutable campaign learning outside the installed plugin.
- Preserve resumability: never repeat an external action from an ambiguous result.
- Prefer scripts for validation, ranking, migration, and other deterministic work.
- Keep Claude and Codex manifests aligned when releasing a version.

## Good first contributions

- additional campaign configuration examples;
- new analytics import adapters;
- improvements to campaign-status summaries;
- more publication and engagement scoring fixtures;
- installation guides for additional agent environments;
- documentation translations.
