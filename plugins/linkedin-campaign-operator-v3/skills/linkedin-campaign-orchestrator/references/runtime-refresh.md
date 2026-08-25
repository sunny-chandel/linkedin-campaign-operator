# Runtime plugin refresh

Claude installs every marketplace plugin version in a separate cache directory. Updating the installed record does not by itself replace instructions already loaded into a running session.

## Stage-boundary check

At pre-flight and before every scheduled stage, run:

```text
python ${CLAUDE_SKILL_DIR}/scripts/resolve_latest_plugin.py --session-version 0.4.0
```

Use the version of this command contained in the active orchestrator. The resolver validates the installed registry, selected cache path, plugin manifest, and current skill files.

## Applying a newer installed version

1. If `update_available` is false, continue normally.
2. If `/reload-plugins` is available as a session command, run it in the active session. It is Claude's supported no-restart reload path.
3. If the command cannot be invoked programmatically, read the returned latest `orchestrator_skill` completely, then read the latest `SKILL.md` for each supporting stage before that stage executes. Treat those files as the active operating instructions for the remainder of the session.
4. Record the installed version, direct-loaded instruction version, install path, detection time, and refresh mode in `campaign-state.json`.
5. Revalidate mutable state and resume from the last confirmed stage. Never repeat an external action merely because instructions changed.

Direct loading covers this plugin's skills, references, scripts, and assets. If a future release adds or changes MCP servers, hooks, agents, or other session-initialized components, `/reload-plugins` is required before those components can be used.

## Release workflow

After publishing and installing a new version, submit `/reload-plugins` to every active campaign session, verify the reported component counts and absence of load errors, then verify the active plugin version. Do not terminate or replace campaign state during reload.
