#!/usr/bin/env python3
"""SL-001 smoke tests 1-4.  Expected outcomes are frozen in PROTOCOL.md section 9."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from kernel_check import check  # noqa: E402

S = Path(__file__).parent / "smoke"
P = "SL001.Smoke."


def relation(fwd, bwd, witness):
    """Frozen decision rule: nothing stronger than the certificates."""
    f, b, w = (x is not None and x["outcome"] == "certified" for x in (fwd, bwd, witness))
    if f and b:
        return "equivalent: certified both directions"
    if f and w:
        return "A implies B certified; separating witness certified (B does not imply A on this class)"
    if f:
        return "A implies B certified; reverse direction undecided"
    return "undecided"


def main():
    res, ok = {}, True

    def expect(name, got, want):
        nonlocal ok
        passed = got == want
        ok &= passed
        res[name] = {"got": got, "expected": want, "pass": passed}

    # 1. a statement against itself
    f = check(str(S / "S1_self.lean"), P + "fwd", "∀ n, SL001.Smoke.A n → SL001.Smoke.A n")
    expect("smoke1_self", relation(f, f, None), "equivalent: certified both directions")
    # 2. one-way implication with a genuine separating case
    f = check(str(S / "S2_forward.lean"), P + "fwd", "∀ n, SL001.Smoke.A n → SL001.Smoke.B n")
    b = check(str(S / "S2_backward_attempt.lean"), P + "bwd", "∀ n, SL001.Smoke.B n → SL001.Smoke.A n")
    expect("smoke2_reverse_attempt_outcome", b["outcome"], "compile_failure")
    expect("smoke2_without_witness", relation(f, b, None), "A implies B certified; reverse direction undecided")
    w = check(str(S / "S2_witness.lean"), P + "witness", "∃ n, SL001.Smoke.B n ∧ ¬ SL001.Smoke.A n")
    expect("smoke2_with_witness", relation(f, b, w),
           "A implies B certified; separating witness certified (B does not imply A on this class)")
    # a correct proof offered for the WRONG direction must not certify that direction
    wrong = check(str(S / "S2_forward.lean"), P + "fwd", "∀ n, SL001.Smoke.B n → SL001.Smoke.A n")
    expect("smoke2_direction_check", wrong["outcome"], "compile_failure")
    # 3. invalid declarations
    e = check(str(S / "S3_error_recovered.lean"), P + "fwd", "∀ n, SL001.Smoke.B n → SL001.Smoke.A n")
    expect("smoke3_error_recovered", e["outcome"], "compile_failure")
    s = check(str(S / "S3_sorry.lean"), P + "fwd", "∀ n, SL001.Smoke.B n → SL001.Smoke.A n")
    expect("smoke3_sorry", s["outcome"], "unsupported_input")
    # 4. a valid proof of something weaker than the target
    t = check(str(S / "S4_weaker.lean"), P + "cert", "∀ p : Nat → Prop, (∀ n, p (n + 1)) → SL001.Smoke.Target p")
    expect("smoke4_does_not_establish_target", t["outcome"], "compile_failure")
    a = check(str(S / "S4_weaker.lean"), P + "cert", "∀ p : Nat → Prop, (∀ n, p (n + 1)) → SL001.Smoke.Proved p")
    expect("smoke4_actual_proposition", a["outcome"], "certified")
    r = check(str(S / "S4_weaker.lean"), P + "target_implies_proved",
              "∀ p, SL001.Smoke.Target p → SL001.Smoke.Proved p")
    expect("smoke4_relation", relation(r, None, None), "A implies B certified; reverse direction undecided")
    res["_all_pass"] = ok
    res["_note"] = ("Harness behaviour tests on synthetic core-Lean statements. They are not SL-001 "
                    "results and produce no ledger records.")
    out = Path(__file__).parent / "results" / "smoke"
    out.mkdir(parents=True, exist_ok=True)
    (out / "smoke.json").write_text(json.dumps(res, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(res, indent=2, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
