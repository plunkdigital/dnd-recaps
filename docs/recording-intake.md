# Recording intake and chronology

Reviewed 2026-10-16. Six M4A recordings are present in the inbox. Original filenames
and media contents were preserved. FFmpeg and FFprobe are now available locally.
No cloud processing or secret access was needed for this inventory.

The local, Git-ignored `recordings/catalog/inventory.json` records source hashes,
sizes, durations, embedded creation timestamps, audio-stream properties, and proposed
order. `recordings/catalog/order-review.md` is the readable review copy. These are
metadata-derived candidates, not reviewed session numbering. They contain no DM lore.

## Proposed chronology

Order is based on the M4A container's `creation_time`, normalized to UTC. These may
represent recorder clocks or export dates rather than actual play dates. Do not use
upload/modification time as recording chronology. All six files have distinct embedded
timestamps, so there is a complete candidate order without guessing from titles.

Do not rename originals or assign canonical session numbers until the timestamps
are confirmed against the table calendar or recorded content. The first three files
have not been proven to match the supplied Sessions 1–3 notes. There may be missing
sessions, multi-part recordings, or exports made after play.

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

When order is reviewed, record its basis and reviewer/date alongside the local
catalog. Preserve original hashes and names as provenance. Never infer order from
the published campaign's chapter sequence or from DM spoiler context.
