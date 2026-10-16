# First recording batch

User confirmed chronology and requested transcription and recaps on 2026-10-16.
Scope: all six supplied recordings, one independent draft recap per recording,
in confirmed order. Keep originals, raw responses, draft status, and spoiler isolation.

- [x] Record user-confirmed order and stable batch/session IDs in the local catalog.
- [x] Prepare all six recordings locally and verify source/chunk integrity.
- [ ] Run transcription using authorized credentials, preserving completed caches.
- [ ] Generate and inspect narrative recaps; record actual results and remaining review.

Credential check: no `OPENAI_API_KEY` is present in the agent process environment.
The real `.env` is protected by a non-escalatable filesystem read denial. Agent
execution cannot load it indirectly through the CLI either. Finish offline preparation
and provide a concrete operator command for the cloud stages unless an authorized
runtime credential becomes available. Do not copy secrets into the test configuration.

Do not use the existing Sessions 1–3 secondary recap as proof of new audio facts.
Historical context must not introduce later-session discoveries into an earlier recap.

Resume note, 2026-10-16: preparations for recordings 1–2 passed source/chunk hash
verification. The interrupted third recording had an empty manifest and incomplete
chunks; its directory was preserved under `sessions/interrupted-session-003-dark-cauldron`
and is being regenerated from the unchanged source. No cloud calls occurred.
The batch shell command uses only the six canonical prepared session IDs, excluding
the interrupted directory. Latest implementation suite: all 22 tests passed.

Offline preparation is complete: all six source recordings and 63 prepared chunks
passed hash verification, audio-format checks, and expected-duration checks. The
ignored `recordings/catalog/batch-readiness.json` records the result. No transcription
or recap has been generated: cloud work remains pending operator execution, not failed
API processing. Run locally from the repository root:

```bash
bash scripts/generate_recaps.sh --allow-cloud
```

The command loads `.env` locally, resumes completed request caches, and stops on the
first failure. Review completed drafts before sharing. No commit or push performed.
