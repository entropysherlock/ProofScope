# SOTA-14 reproduction

Toolchain: Lean 4.34.1 (commit 5045d005), core only, no Mathlib.

    mkdir -p build/ProofScope
    lean -o build/ProofScope/ScopeElim.olean ScopeElim.lean
    LEAN_PATH=build lean -o build/ProofScope/Adversarial.olean Adversarial.lean
    LEAN_PATH=build lean -o build/ProofScope/Cases.olean Cases.lean
    LEAN_PATH=build leanchecker --fresh ProofScope.ScopeElim
    LEAN_PATH=build leanchecker --fresh ProofScope.Adversarial
    LEAN_PATH=build leanchecker --fresh ProofScope.Cases

Expected: no errors, no warnings, all three replays exit 0. Axioms: Theorems A, A0, the sufficiency
half of B and `choice_of_fun_schematic` are axiom-free; `fun_schematic` uses
`propext, Classical.choice, Quot.sound`; the square lemmas use `propext, Quot.sound`.

ProofScope v1.2 behaviour on the new cases (branch `v1.2-review` @ 0824134):

    python3 -m proofscope.adelta12 s14_cancel.json --out out_ad        # INCONCLUSIVE
    python3 -m proofscope.claimdelta cd_s14_twice.json cd_s14_shift.json --out out_cd   # INCONCLUSIVE x2

`Cases.lean` certifies LEAN_WEAKER for `cd_s14_twice` and SCHEMA_EQUIVALENT for `cd_s14_shift`.