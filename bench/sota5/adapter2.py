"""Adapter v2 (SOTA-5): statement printing that keeps coercion targets, and a standalone round-trip check.

Finding (docs/sota5/README.md, section C): the frozen adapter prints with `pp.fullNames`,
`pp.funBinderTypes`, `pp.proofs`, `pp.deepTerms`, but not `pp.coercions.types`. A cast such as
`((n - 1 : ℕ) : ℤ)` prints as `↑(n - 1)`; elaborated again without an expected type, `↑` is resolved to the
identity on ℕ and the statement changes meaning (d03: a false statement becomes `∀ n : ℕ, n - 1 = n - 1`).
The frozen runner catches this with its round-trip check (the case becomes INPUT_NOT_EVALUABLE);
the SOTA-4 measurement tool `bench/sota4/specs.py` printed statements but did not run the check, so the
engines received the wrong statements there. bench/adapters/proofscope.py is frozen and is not modified.

v2 changes, nothing else:
  * print with `pp.coercions.types true` (a cast prints as `(↑x : T)`);
  * the check elaborates the printed text **on its own** as `abbrev ps_printed : Prop := (printed)`, exactly
    as an engine will, and then requires `ps_printed = type_of% @decl` by `with_reducible rfl`.
A case that fails either check is not given to any engine (status INPUT_NOT_EVALUABLE, with the log).
"""
from __future__ import annotations

from bench.adapters import proofscope as V1
from bench.adapters._decl import rename, split_header, with_sorry

PRINT = V1.PRINT.replace(
    "withOptions (fun o =>\n      (((o.setBool `pp.fullNames true).setBool `pp.funBinderTypes true).setBool `pp.proofs true).setBool `pp.deepTerms true)",
    "withOptions (fun (o : Options) =>\n      ((((o.setBool `pp.fullNames true).setBool `pp.funBinderTypes true).setBool `pp.proofs true)"
    ".setBool `pp.deepTerms true).setBool `pp.coercions.types true)")
assert PRINT != V1.PRINT, "frozen adapter PRINT changed; v2 patch point not found"


def side_file(header: str, decl: str, name: str, imports: list[str]) -> str:
    return V1.side_file(header, decl, name, imports).replace(V1.PRINT.replace("{name}", name), PRINT.replace("{name}", name))


def check_file(header: str, decl: str, name: str, imports: list[str], printed: str) -> str:
    imps, rest = split_header(header)
    body = "\n".join(rest)
    return ("\n".join(imports) + f"\n\nsection\n{body}\n\n{rename(with_sorry(decl), name)}\n\nend\n\n"
            f"abbrev ps_printed_standalone : Prop := ({printed})\n"
            f"example : ps_printed_standalone = type_of% @{name} := by with_reducible rfl\n")
