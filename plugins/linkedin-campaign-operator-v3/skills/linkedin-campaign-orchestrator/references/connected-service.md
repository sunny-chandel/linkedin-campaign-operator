# Connected service handoff

Use this reference only when a ready campaign item needs the separately installed connected service or when a saved service result needs diagnosis.

## Responsibilities

Claude Code prepares and validates local campaign work. The connected service handles supported account activity and returns result evidence. Do not use browser interaction as a replacement for the service.

Before preparing a request, confirm:

- the selected profile matches campaign state;
- the service reports the required capability as available;
- the item is current, complete, and within campaign settings;
- quality, timing, cooldown, and duplicate checks pass;
- no earlier request has an unresolved outcome.

Prepare one canonical request from the saved package or response. Keep the public copy, media path, account identity, campaign ID, request ID, and evidence references together. The service result must include a stable result identity and verification time before the campaign ledger marks the item complete.

If the service is unavailable, save the item as ready and continue other local work. If a request outcome is unclear, leave it unresolved and check the original result before creating another request.

## Result handling

- A verified result completes the item and updates the relevant ledger.
- A confirmed rejection returns the item to the appropriate repair or revision stage.
- An unavailable capability leaves the item ready and records the next capability check.
- An unclear outcome remains isolated until the original request can be verified.

Do not expose service implementation details in routine campaign updates.
