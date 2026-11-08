# Pair spec reference

A pair spec is a JSON file describing one comparison between a custom definition and a reference.

| Field | Required | Meaning |
|---|---|---|
| `id` | yes | Unique name. Becomes the Lean namespace `ProofScopeCert.<Id>`. |
| `binders` | yes | List of `[name, type]` pairs, e.g. `[["n", "Nat"], ["t", "Nat"]]`. |
| `custom` | yes | Lean term for the definition under audit, applied to the binders. |
| `reference` | yes | Lean term for the justified reference notion. |
| `relation` | no | `"eq"` (default) compares values with `=`; `"iff"` compares propositions with `↔`. |
| `domain` | no | Lean proposition: the inputs on which the theorem actually uses the definition. Default `True`. |
| `bounds` | no | Upper bounds for natural-number binders. Adds finite-box obligations checked with `decide +kernel`. |
| `preamble` | no | Lean code placed before the obligations, typically the challenge's own definitions, copied verbatim. |
| `imports` | no | Modules to import, e.g. `["Mathlib"]`. Needs `--project` pointing at a Lake project that has them. |
| `lemmas` | no | Helper lemmas written for this pair. Kernel-checked like everything else, and flagged as pair-specific in the report. |
| `tactics` | no | Extra tactics per obligation (`equal_all`, `agree_domain`, `witness_all`, `witness_domain`, and the `_bounded` versions). Flagged as pair-specific. |
| `reference_source` | no | Where the reference notion comes from (paper, textbook, Mathlib). |
| `expected` | no | Ground-truth label for benchmark cases. |
| `group` | no | `real`, `control` or `mutant`. |

## Obligations

| Obligation | Statement |
|---|---|
| `equal_all` | `∀ x, custom x ~ reference x` |
| `agree_domain` | `∀ x, domain x → custom x ~ reference x` |
| `witness_all` | `∃ x, ¬ (custom x ~ reference x)` |
| `witness_domain` | `∃ x, domain x ∧ ¬ (custom x ~ reference x)` |
| `*_bounded` | The same with every binder `< bound`. |

Each obligation is attempted with a generic tactic portfolio; every alternative must close the goal. The ones
that succeed are recompiled in a clean module, checked with `#print axioms` (anything depending on `sorryAx` or
a non-standard axiom is rejected) and replayed with `leanchecker`. Only survivors count.

## Theorem relevance

The `domain` field is where theorem relevance comes from. Getting it right is a human judgement: read the
theorem statement, find every place the definition is used, and write the strongest condition those uses
guarantee. A certificate is only as relevant as that domain.
