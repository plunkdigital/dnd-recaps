# Relevance coverage recovery

Follow-up: batch 4 has one source assigned across multiple groups, plus three
omissions. Extend the same conservative manual-review fallback to invalid or
conflicting groups; keep only independently validated, nonconflicting groups.
If the response cannot be parsed, withhold every source in that batch. Never claim
complete model classification in these cases. Provider-incomplete/network failures
still stop processing. Replay the four cached batches offline before close-out.

2026-10-16: Session 1 batch 1 returned valid JSON classifying 35 of 50 IDs.
Fifteen segments were omitted. No unknown IDs, duplicates or malformed fields were
found. Current strict parser stopped safely, but could not resume from that cache.

- [x] Diagnose the cached response without printing private provider text.
- [x] Withhold missing IDs as explicit unclassified manual checks; retain strict validation for other faults.
- [x] Verify cached real-response coverage offline and add regression tests.
- [x] Update current state/workflow and verify suite, links and whitespace.

No guessing relevance, ignored omissions, deletion of caches, secret loading,
live provider calls, or repeated GPU processing. A report must disclose unclassified
segments, not claim the model classified everything. Preserve human review logs.

Initial result: all 76 offline tests passed. The existing cached first response accounts
for all 50 sources: 35 campaign sources retained, 15 withheld/unclassified and listed
for review. Raw cache hash is unchanged; no inference or provider call occurred.
Regression coverage includes cached reruns, wholly empty classifications, unchanged
strict rejection of other schema/identity faults, and batch-specific omission groups.
Generated reports and provenance explicitly distinguish extraction coverage from
partial model classification. Live semantic accuracy remains subject to review.

Follow-up verified: 80 offline tests pass. All four existing cached relevance
responses were replayed offline without changes or provider calls. Source counts
are 50/47/67/56; manual-review counts are 15/0/18/15, with 41 campaign sources
retained in batch 4. Tests cover invalid schemas/fields, unknown IDs, conflicting
groups, malformed groups overlapping valid ones, and unlocatable invalid items.
Untrusted groups never enter notes. Invalid whole responses become explicit
whole-batch manual checks, not successful model classifications. Incomplete provider
status and network errors still fail the stage. Raw responses and human logs remain.
