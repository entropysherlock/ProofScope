# Demonstration: how ProofScope detects and certifies one real benchmark defect

**The benchmark.** [FormalMATH](https://github.com/Sphere-AI-Lab/FormalMATH-Bench) is a public Lean 4 benchmark of 5,560 competition problems used to evaluate AI theorem provers ([SphereLab/FormalMATH-All](https://huggingface.co/datasets/SphereLab/FormalMATH-All), revision `8eea2550`).

**The defect.** Row `olymid-ref-base_1859` states that a system of real equations has **no solution**. It has solutions: (0, 1, 1) is one. Lean certifies this, and the benchmark's own reference solution lists such solutions.

## 1. The problem as published

Informal statement (dataset field `refined_statement`):

> (Netherlands). Find all triples (a, b, c) of real numbers such that ab + bc + ca = 1 and a²b + c = b²c + a = c²a + b.
> Prove that the answer is: **None**

Formal statement (dataset field `autoformalization`, verbatim):

```lean
theorem olymid_ref_base_1859 (a b c : ℝ) (h1 : a * b + b * c + c * a = 1)
(h2 : a^2 * b + c = b^2 * c + a) (h3 : b^2 * c + a = c^2 * a + b) :
False:= by
```

A prover that "solves" this item would have to derive `False` from three equations that are simultaneously satisfiable. That is impossible, so the item can never be solved.

## 2. Detection: ProofScope's defect hunter

[`proofscope/defect_hunt.py`](../../../../proofscope/defect_hunt.py) loads each statement unchanged into a Lean REPL with Mathlib. For this row it then does three things:

1. **Probe.** It reads the binder structure: three real variables, three equational hypotheses, and the conclusion `False`.
2. **Search.** It tries to prove `¬ (type_of% @olymid_ref_base_1859)`, the negation of the statement exactly as written. One of its tactics instantiates the numeric variables at small values, smallest first. At (a, b, c) = (0, 1, 1), every hypothesis closes by `norm_num`.
3. **Certify.** It re-proves the negation in a clean Lean module. It then checks that `#print axioms` shows only `propext`, `Classical.choice` and `Quot.sound`, and that `leanchecker` replays the module.

The full-benchmark run is [run 44002011370](https://github.com/entropysherlock/ProofScope/actions/runs/44002011370). Planted-defect controls ran with it, and they passed.

## 3. The standalone certificate

[`Cert1859.lean`](Cert1859.lean) contains the dataset's `autoformalization` field byte-for-byte (its SHA-256 is recorded in the file header), with only the proof placeholder `sorry` appended. The certificate follows:

```lean
theorem olymid_ref_base_1859_is_false : ¬ (type_of% @olymid_ref_base_1859) := by
  intro h
  exact h 0 1 1 (by norm_num) (by norm_num) (by norm_num)
```

The certificate uses only the *type* of the benchmark theorem, never its missing proof. So `#print axioms` shows no `sorryAx`.

## 4. Independent reproduction on two pinned toolchains

| Environment | Result |
|---|---|
| Lean v4.11.0 with Mathlib `8edf04f`. This is FormalMATH's own environment: `repl@adbbfcb`, test/Mathlib manifest. | compiles; standard axioms only |
| Lean v4.34.1 with Mathlib `d13f23b` | compiles; standard axioms only; `leanchecker` replay OK |

The CI evidence for all 8 hand-checked findings is [run 44006962915](https://github.com/entropysherlock/ProofScope/actions/runs/44006962915).

To reproduce on your own machine (about 5 minutes):

```bash
git clone --branch research/defect-hunt-ci https://github.com/entropysherlock/ProofScope
cd ProofScope/experiments/defect_hunt/formalmath/demo_1859
./reproduce.sh
```

## 5. Human check against the informal problem

The Lean certificate shows that the *formal* statement is false. A human check is still needed to classify the defect:

- **Arithmetic.** At (0, 1, 1): ab + bc + ca = 0 + 1 + 0 = 1. a²b + c = 1, b²c + a = 1 and c²a + b = 1, so all three expressions are equal. The intended domain is real numbers, and the witness is real.
- **The dataset's own reference solution** (`solution` field) finds the solutions explicitly: "if e.g. a = 0 then b = c = ±1, … a = b = c = ±1/√3 or a = b = ±1, c = 0, and these are indeed solutions."
- **Classification: wrong stated answer.** The answer "None" contradicts the problem's own reference solution. The Lean encoding faithfully formalizes that wrong answer.

## Scope of the claim

This certifies one defective benchmark item. It does **not** claim that FormalMATH is unreliable overall, or that ProofScope finds all defects.

The released per-item results of the ICML 2026 audit by Ammanamanchi, Bhat and Biderman contain no finding for this row. That evidence is limited: it shows only that this audit, with its checkers, did not report it.
