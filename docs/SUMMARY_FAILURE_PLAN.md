# Direct summary failure repair

Started 2026-10-17. The latest direct Session 1 run withheld 1,980 segments and
stopped with a generic error at its first scene. Preserve every cache and ID.

- [x] Reconstruct the current cached path without API calls or writes; identify
  actual malformed response types and expose safe exception locations.
- [x] Preserve valid cached classifications, then repair unclassified sources with a
  strict per-source classification schema; never guess categories or reuse a
  malformed response as evidence. Preserve valid existing classifications.
- [x] Prevent long-running direct CLI processes from mixing lazily imported module
  versions. Keep private exception values out of diagnostics.
- [x] Exercise the complete CLI path with realistic synthetic provider output,
  replay actual caches read-only, and run the full offline suite.
- [x] Document verified results, cache reuse, and remaining live-provider limits.

## Actual findings and verification

Read-only replay reproduced all 74 existing request identities. Thirty completed
responses were non-JSON; 41 batches withheld 1,980 source IDs. Valid cached decisions
are retained. The new path prepares 84 bounded native label requests to repair only
those IDs, then new narrative requests. No old cache body was edited or promoted.

The historical generic exception cannot be confirmed without its traceback. The
current files replay to the next uncached scene request without reproducing it.
A concrete late-import hazard was removed: narrative, relevance and campaign modules
now load together at CLI startup, rather than importing narrative after long provider
work. Unexpected exceptions now report only their class and safe code location.

Verification includes a full direct CLI test with synthetic multi-window transcript,
non-JSON cached response shapes, strict native labels, final story generation and a
second run with no additional provider calls. Separate cases cover fresh strict
classification, preservation of valid unrelated categories, exact ID coverage,
uncertain questions, duplicate keys and private-error redaction. No actual recordings
or paid calls are used in automated tests. Live model quality remains unverified.
