import Lean
open Lean Meta Elab Tactic

namespace ProofScope

/-- Collect `a % b` and `a / b` over ℕ (closed subterms only) from an elaborated expression. -/
partial def collectDivMod (e : Expr) (acc : Array (Expr × Expr)) : Array (Expr × Expr) :=
  let acc := if (e.isAppOfArity ``HMod.hMod 6 || e.isAppOfArity ``HDiv.hDiv 6)
      && e.getArg! 0 == mkConst ``Nat && !e.hasLooseBVars && !acc.contains (e.getArg! 4, e.getArg! 5)
    then acc.push (e.getArg! 4, e.getArg! 5) else acc
  match e with
  | .app f a => collectDivMod a (collectDivMod f acc)
  | .lam _ t b _ | .forallE _ t b _ => collectDivMod b (collectDivMod t acc)
  | .letE _ t v b _ => collectDivMod b (collectDivMod v (collectDivMod t acc))
  | .mdata _ b | .proj _ _ b => collectDivMod b acc
  | _ => acc

def addFact (pf : Expr) : TacticM Unit := withMainContext do
  let g ← getMainGoal
  let g' ← g.assert `ps_fact (← inferType pf) pf
  let (_, g'') ← g'.intro1P
  replaceMainGoal [g'']

/-- `ps_arith`: add library facts about every ℕ `a % b` / `a / b` in the goal and context, then `omega`.
`a % b < b` is added only after `0 < b` is itself proved by `omega`. Every fact is a library proof term. -/
elab "ps_arith" : tactic => do
  let tys ← withMainContext do
    let mut tys := #[← instantiateMVars (← getMainTarget)]
    for d in (← getLCtx) do
      if !d.isImplementationDetail then tys := tys.push (← instantiateMVars d.type)
    pure tys
  let pairs := tys.foldl (fun acc t => collectDivMod t acc) #[]
  for (a, b) in pairs do
    for (lem, args) in [(``Nat.mod_le, #[a, b]), (``Nat.div_mul_le_self, #[a, b]),
                        (``Nat.div_le_self, #[a, b]), (``Nat.mod_add_div, #[a, b])] do
      try addFact (← withMainContext (mkAppM lem args)) catch _ => pure ()
    try
      let hb ← withMainContext do
        let ty ← mkAppM ``LT.lt #[mkNatLit 0, b]
        let m ← mkFreshExprMVar ty
        let rest ← Tactic.run m.mvarId! (evalTactic (← `(tactic| omega)))
        unless rest.isEmpty do throwError "no"
        instantiateMVars m
      addFact (← withMainContext (mkAppM ``Nat.mod_lt #[a, hb]))
    catch _ => pure ()
  evalTactic (← `(tactic| omega))

end ProofScope
