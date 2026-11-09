import Lean
/-!
# Boundary witness synthesis (v1.0)

A strict/non-strict or equality change around an abstracted operator (`x a a < a + 2` against
`x a a ≤ a + 2`) is separated by an interpretation that puts the operator *exactly on the boundary*:
`x := fun a _ => a + 2`. A fixed witness pool cannot contain such terms in general.

`#proofscope_boundary (fun (x₁ : T₁) … => S)` elaborates an abstracted statement and, for every
comparison atom `x_i t₁ … tₖ ⋈ e` (or `e ⋈ x_i …`) where the `tⱼ` are bound variables and `e`
mentions only those variables, prints the candidate interpretation `fun t₁ … tₖ => e` for `x_i`.
Candidates are only *proposals*: each is used inside a separation certificate that Lean checks.
-/

open Lean Meta Elab Command Term

namespace ProofScope.Boundary

def relHeads : List Name := [``Eq, ``LT.lt, ``LE.le, ``Ne, ``GT.gt, ``GE.ge]

partial def atoms (xs : Array Expr) (e : Expr) (acc : Array (Nat × Expr)) : MetaM (Array (Nat × Expr)) := do
  match e with
  | .forallE n t b bi => withLocalDecl n bi t fun fv => atoms xs (b.instantiate1 fv) acc
  | .lam n t b bi => withLocalDecl n bi t fun fv => atoms xs (b.instantiate1 fv) acc
  | .mdata _ b => atoms xs b acc
  | .app .. =>
    let mut acc := acc
    let f := e.getAppFn
    let args := e.getAppArgs
    if f.isConst && relHeads.contains f.constName! && args.size ≥ 2 then
      let lhs := args[args.size - 2]!
      let rhs := args[args.size - 1]!
      for (s, o) in [(lhs, rhs), (rhs, lhs)] do
        if let some i := xs.findIdx? (· == s.getAppFn) then
          let sargs := s.getAppArgs
          if sargs.size > 0 && sargs.all (·.isFVar) && !sargs.any (xs.contains ·) then
            let allowed := sargs.map (·.fvarId!)
            unless o.hasAnyFVar (fun fv => !allowed.contains fv) do
              let lam ← withLocalDeclsDND (← sargs.mapIdxM fun j a => do
                  return (Name.mkSimple s!"b{j}", ← inferType a)) fun news => do
                -- the first occurrence of each argument variable becomes the lambda variable
                let mut body := o
                let mut seen : Array FVarId := #[]
                for j in [:sargs.size] do
                  let a := sargs[j]!.fvarId!
                  unless seen.contains a do
                    body := body.replaceFVarId a news[j]!
                    seen := seen.push a
                mkLambdaFVars news body
              acc := acc.push (i, lam)
    for a in args do acc ← atoms xs a acc
    return acc
  | _ => return acc

elab "#proofscope_boundary " t:term:max : command => liftTermElabM do
  let e ← elabTerm t none
  synthesizeSyntheticMVarsNoPostponing
  let e ← instantiateMVars e
  let out ← lambdaTelescope e fun xs body => do
    let found ← atoms xs body #[]
    let mut per : Array (Array String) := xs.map fun _ => #[]
    for (i, lam) in found do
      let s := toString (← withOptions (fun o => (o.setBool `pp.funBinderTypes true).setBool `pp.numericTypes true)
        (ppExpr lam))
      unless per[i]!.contains s do per := per.set! i (per[i]!.push s)
    return Json.arr (per.map fun a => Json.arr (a.map Json.str))
  logInfo m!"PROOFSCOPE_BOUNDARY {out.compress}"

end ProofScope.Boundary
