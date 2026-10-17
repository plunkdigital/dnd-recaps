> Historical implementation notes, archived 2026-10-17. See [current state](../PROJECT_STATE.md).

# Summary citation recovery

2026-10-16: user reports the older summarizer failed after completed GPU diarization.
Read-only cache diagnostics found compressed citation ranges and some nonexistent
IDs in intermediate responses. Do not loosen validation or infer range expansions.

- [x] Identify the failing stage using cache structure and ID diagnostics only.
- [x] Require exact individual citations and reject malformed references at every narrative stage.
- [x] Add one cached evidence-based rewrite after citation failure, with regression tests.
- [x] Verify offline suite, update state/workflow, and give a summary-only retry command.

Keep raw responses and GPU caches. No credentials or paid calls in agent validation.
Current working changes also include automatic relevance review; keep that work.

Result: 72 offline tests passed. Checks reject bare, grouped, compressed, shorthand,
and unknown IDs even alongside an otherwise valid citation. One rewrite uses only
the original validated input, not the invalid draft; both responses stay cached.
Repeated invocations reuse the recovery cache. Incomplete responses never become
cached successes or trigger recovery. Errors name the failing narrative stage.
Live API behavior and semantic support still require human review. The original
old summary caches are retained for provenance and are not promoted to drafts.
