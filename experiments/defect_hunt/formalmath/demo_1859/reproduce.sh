#!/usr/bin/env bash
# Reproduce the FormalMATH olymid-ref-base_1859 certificate in FormalMATH's own environment
# (Lean v4.11.0, Mathlib 8edf04f — the versions pinned by the repl commit in FormalMATH-Bench's README).
# Needs: elan (https://github.com/leanprover/elan), git, ~6 GB disk. About 5 minutes, mostly the Mathlib download.
set -euo pipefail
cd "$(dirname "$0")"
lake update                      # resolves Mathlib at the pinned commit only
lake exe cache get               # precompiled Mathlib, no local build
lake env lean Cert1859.lean      # must print exactly one warning (the benchmark statement's own `sorry`)
                                 # and: 'olymid_ref_base_1859_is_false' depends on axioms: [propext, Classical.choice, Quot.sound]
