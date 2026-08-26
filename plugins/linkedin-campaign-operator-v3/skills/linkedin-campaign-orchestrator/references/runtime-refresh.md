# Runtime plugin refresh

Claude installs every marketplace plugin version in a separate cache directory. Updating the installed record does not by itself replace instructions already loaded into a running session.

## Stage-boundary check

On a new or resumed Claude Code session, run `resume_campaign.py` before this version check. Self-revival restores durable consent and task state; instruction refresh then determines which installed scripts and skills govern the recovered task.

At pre-flight, every scheduled wake, and before every stage, read `runtime_instructions.active_version` and `runtime_instructions.install_path` from `campaign-state.json`. Run the resolver under the recorded install path. Only when no recorded path exists, use the currently loaded skill directory:

```text
python <active-install-path>/skills/linkedin-campaign-orchestrator/scripts/resolve_latest_plugin.py --session-version <active-version> --state-dir <state-dir>
```

The resolver validates the installed registry, selected cache path, plugin manifest, and current skill files. It also writes the detected version and path to campaign state atomically. Persisting the newest path prevents removal of an older cache directory from breaking later refresh checks.

## Applying a newer installed version

1. If `update_available` is false, continue normally.
2. In Claude Desktop, directly read the returned `orchestrator_skill` completely, then read every returned supporting `SKILL.md`. Treat those files as the active operating instructions for the remainder of the session.
3. After all files load, rerun the returned resolver with the same arguments plus `--activate`. This normalizes `session_version`, `active_version`, and `detected_version` to the installed version, records the newest install path, detection time, activation time, and `direct-loaded` refresh mode, and clears the update-pending result.
4. Use scripts, references, and assets only from that newest returned install path. Revalidate mutable state and resume from the last confirmed stage. Never repeat an external action merely because instructions changed.
5. If the active client explicitly lists `/reload-plugins` as an available command, it may be used before direct verification. Never assume the command exists; Claude Desktop Code sessions may not expose it.

Direct loading covers this plugin's skills, references, scripts, and assets, which are all components in this plugin. If a future release adds or changes MCP servers, hooks, agents, or other session-initialized components, a client-supported plugin reload or a new session is required before those components can be used.

## Release workflow

After publishing and installing a new version, notify each active campaign session with the fixed instruction to run its stage-boundary resolver immediately. In Claude Desktop, verify that the session directly loads the newest orchestrator and all returned child skills, records `refresh_mode: direct-loaded`, migrates and validates state, and resumes the stored stage. If a client advertises `/reload-plugins`, use it and verify its component counts and load errors before performing the same state/version check. Do not terminate or replace campaign state during refresh.
