# Recording intake and chronology

Reviewed 2026-10-16. Six M4A recordings are present in the inbox. Original filenames
and media contents were preserved. FFmpeg and FFprobe are now available locally.
No cloud processing or secret access was needed for this inventory.

The local, Git-ignored `recordings/catalog/inventory.json` records source hashes,
sizes, durations, embedded creation timestamps, audio-stream properties, and proposed
order. `recordings/catalog/order-review.md` is the readable review copy. These are
metadata-derived candidates, not reviewed session numbering. They contain no DM lore.

## Confirmed chronology

The user confirmed the six-recording sequence on 2026-10-16. The local catalog now
records that confirmation and stable `session-001-...` through `session-006-...` IDs.
This confirms relative order, not that embedded dates are exact play dates or that
no sessions are missing. `played_on` remains blank pending date confirmation.

Order is based on the M4A container's `creation_time`, normalized to UTC. These may
represent recorder clocks or export dates rather than actual play dates. Do not use
upload/modification time as recording chronology. All six files have distinct embedded
timestamps, so there is a complete candidate order without guessing from titles.

The batch uses sequential session IDs in this confirmed recording order. Original
filenames remain unchanged. The first three files have not yet been checked against
the supplied Sessions 1–3 recap; use audio to establish that match. Their recaps use
`context_policy: recording_only`, excluding later history from character/glossary/state
documents. Later recordings can use the supplied prior-session campaign history.

## Working with unsorted recordings

Stable descriptive IDs can be used before chronology is confirmed, for example:

```bash
PYTHONPATH=src python3 -m dnd_recaps prepare recording-spice-bag "recordings/inbox/Spice Bag.m4a"
```

This creates a local copy and upload chunks, not a new chronological fact. Other
recordings can be prepared independently; cross-session context must still follow
reviewed chronology. The inventory itself does not prepare or transcribe them.
Transcription and summaries require the separately documented cloud commands.

The Windows `:Zone.Identifier` sidecar files are download-origin metadata, not
recordings. They were excluded from the catalog and left in place. No attempt was
made to inspect their download-origin URLs. Exact source hashes identify duplicates;
different hashes do not rule out overlapping recordings.

The user confirmation is recorded alongside the local catalog. Preserve original
hashes and names as provenance. Never infer order from
the published campaign's chapter sequence or from DM spoiler context.

## First transcription and recap batch

Once preparation is complete, the local operator can run all six cloud stages with:

```bash
bash scripts/generate_recaps.sh --allow-cloud
```

Run from the repository root. This loads the local `.env` through the existing CLI
and processes each recording in confirmed order, stopping on the first failure.
Rerun the same command to reuse completed transcription and summary caches. Do not
edit normalized transcripts while rerunning this batch: transcription rebuilds them
from raw cached responses. Outputs are drafts under each session's `summaries/`.

The agent runtime has no environment-provided API key and may not read the protected
`.env`, including indirectly through a script. The operator command is necessary
for this environment's cloud stages; do not put a real key in `config/codex-test.env`.
