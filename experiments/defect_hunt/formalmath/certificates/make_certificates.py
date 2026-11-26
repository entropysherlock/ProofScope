"""Build one standalone Lean certificate per hand-checked FormalMATH finding.

Each file contains the benchmark's `autoformalization` text **byte-for-byte** (from originals.jsonl, exported from
SphereLab/FormalMATH-All at the revision in originals_meta.json) with `sorry` appended as its proof, followed by a
theorem proving the NEGATION of that statement (`¬ (type_of% @T)`), and `#print axioms` for the certificate.
The certificate must not depend on `sorryAx`: it uses only the statement's type, never its (missing) proof.
"""
import hashlib, json
from pathlib import Path

HERE = Path(__file__).parent
ORIG = {json.loads(l)["theorem_names"]: json.loads(l)
        for l in (HERE.parent / "originals.jsonl").read_text().splitlines() if l.strip()}
META = json.loads((HERE.parent / "originals_meta.json").read_text())

# row id -> (Lean theorem name, category, witness in words, proof of ¬ statement)
CERTS = {
    "olymid-ref-base_1859": ("olymid_ref_base_1859", "WRONG_STATED_ANSWER", "(a, b, c) = (0, 1, 1)",
        "intro h\n  exact h 0 1 1 (by norm_num) (by norm_num) (by norm_num)"),
    "olymid-ref-base_918": ("olymid_ref_base_918", "WRONG_STATED_ANSWER", "x = 0",
        "intro h\n  have h0 := @h 0 (by simp)\n  norm_num at h0"),
    "olymid-ref-base_10553": ("olymid_ref_base_10553", "WRONG_STATED_ANSWER", "(a, b, c) = (1, -1, 1)",
        "intro h\n  obtain ⟨t, ⟨rfl, h2, -⟩ | ⟨rfl, h2, -⟩⟩ := @h 1 (-1) 1 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num)\n  all_goals norm_num at h2"),
    "theorem_proving_zh_blue_988": ("algebra_33567", "INCORRECT_STATEMENT", "(x, y, z) = (0, -1, -1)",
        "intro h\n  have h0 := @h 0 (-1) (-1) (by norm_num)\n  norm_num at h0"),
    "theorem_proving_zh_blue_1350": ("inequalities_8712", "INCORRECT_FORMALIZATION", "(x, y, z) = (0, 1, 1)",
        "intro h\n  have h0 := (h 0 1 1 le_rfl zero_le_one zero_le_one).2\n  norm_num at h0"),
    "olymid-ref-base_2124": ("olymid_ref_base_2124", "INCORRECT_FORMALIZATION", "x = 0",
        "intro h\n  have h0 := (h 0 le_rfl).2\n  norm_num at h0"),
    "omni_theorem_3461": ("omni_theorem_3461", "INCORRECT_FORMALIZATION", "x = 0",
        "intro h\n  exact h 0 (by norm_num)"),
    "theorem_proving_zh_blue_1245": ("algebra_68645", "MISSING_DOMAIN_ASSUMPTION", "(a, b, c) = (0, 0, 1)",
        "intro h\n  have h0 := h 0 0 1\n  norm_num at h0"),
}


def build():
    index = []
    for rid, (name, cat, witness, proof) in CERTS.items():
        row = ORIG[rid]
        src = row["autoformalization"]
        assert src.rstrip().endswith(":= by"), rid
        sha = hashlib.sha256(src.encode()).hexdigest()
        cert = f"{name}_is_false"
        text = (f"/-\nFormalMATH-All row `{rid}` (dataset revision {META['revision']}).\n"
                f"Lines below up to the marker are the dataset's `autoformalization` field, byte-for-byte\n"
                f"(SHA-256 {sha}); only the proof placeholder `sorry` is appended.\n"
                f"Category: {cat}. Counterexample: {witness}.\n-/\n"
                + src + "\n  sorry\n\n"
                f"-- ===== ProofScope certificate: the statement above is false =====\n"
                f"theorem {cert} : ¬ (type_of% @{name}) := by\n  {proof}\n\n"
                f"-- expected: depends only on standard axioms (no sorryAx)\n#print axioms {cert}\n")
        (HERE / f"{rid}.lean").write_text(text)
        index.append({"row": rid, "file": f"{rid}.lean", "theorem": name, "certificate": cert, "category": cat,
                      "counterexample": witness, "autoformalization_sha256": sha})
    (HERE / "index.json").write_text(json.dumps({"dataset": META["dataset"], "revision": META["revision"],
                                                 "certificates": index}, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    build()
