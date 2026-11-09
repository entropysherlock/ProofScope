# SOTA-3 held-out checksum: forensic audit (SOTA-4 Task A/B)

## Question
`theory-and-core` in SOTA-3 run 42701174017 stopped at
`test "$(cat research/cjcs/core_heldout/*.json | sha256sum)" = bb8628b6…`. The review said "probably
newline normalization". That was a guess; this is the evidence.

## Evidence (reproducible: `git` + the delivered SOTA-3 patch)
1. **Original bytes.** The SOTA-3 change was delivered as `proofscope-sota3-cjcs.patch`
   (sha256 `f0f1c74a5db0053571d310bb1ff8bd7b6f9543c2416385fbbe8d6ca7b6bd96e8`, 24 hunks marked
   `\ No newline at end of file`). Applied to `5769208`, it reproduces the recorded digest exactly:
   `cat research/cjcs/core_heldout/*.json | sha256sum` = **`bb8628b61ff16efd674dc6380a94bc64f301f37ae273ae26f7768027b8a29495`**.
2. **Repository bytes** at `3791511`: the same command gives
   **`8cc0460c14c7a9fa2ea7ffa64edd9ee849727fd6791e0d63d65ae4d177e57419`**.
3. **Whole-tree byte comparison** (original vs repository, every tracked file): exactly 24 files differ,
   the 10 `core_dev` and 14 `core_heldout` JSON files, and in every one the repository file equals the
   original followed by exactly one byte `0x0A`. Nothing else in the tree differs. Per held-out file the
   size grows by one byte (h01: 241→242 … h14: 263→264); the parsed JSON values are identical.
4. Removing that one final byte from each repository file reproduces `bb8628b6…` exactly.

## Diagnosis
Not file ordering (same 14 names, same glob order), not an altered dataset (identical JSON values, every
byte before the final LF identical), not a wrong recorded checksum (the recorded value is the digest of the
original bytes). Cause: **newline normalization in transit** — each JSON file that was authored without a
final newline received one when the patch was applied/uploaded (the commit before 3791511 is an
"Add files via upload"). The gate itself was fragile: it hashed raw bytes of files whose final newline is
not semantically meaningful.

## Status of the held-out set
**Authenticated.** The intended files are recoverable byte-for-byte (strip one trailing LF) and are
verified against the digest recorded before the first run. They are kept unchanged in the repository.
They remain **developer-authored** (written by the engine developer, Claude) and were first run in SOTA-3,
so they are regression/development evidence, never independent evidence.

## Repair (bench/sota4/integrity.py)
* Canonical JSON digest per file (UTF-8 strict, no BOM, duplicate keys and NaN rejected, sorted keys,
  compact separators). Line endings and insignificant whitespace do not matter; values, types, key sets
  and array order do.
* `research/cjcs/core_heldout.MANIFEST.json`: sorted file names with canonical digests, a set digest over
  the ordered list, and the legacy record. **Computed from the authenticated original bytes, not from the
  checkout.** `--require-legacy` additionally reconstructs `bb8628b6…` from the checkout.
* Tests (`tests/sota4/test_integrity.py`, 15): LF/CRLF/whitespace variants hash identically; value, type,
  order, key changes change the digest; names and order are committed; missing, renamed, duplicated and
  extra files are detected; invalid JSON (truncated, duplicate key, NaN, BOM, non-UTF-8) is rejected; a
  manifest recomputed from a tampered checkout cannot reproduce the recorded digest.
* The SOTA-3 workflow is not modified; SOTA-4's integrity job reproduces its failure and records it.
