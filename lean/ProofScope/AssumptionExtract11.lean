import Lean
/-!
# Assumption extraction v1.1 (elaborator side)

v1.1 changes (dependent-structure linking): every binder gets a fresh *accessible* name (hygienic and
inaccessible names such as `inst✝` cannot be printed back), and the binder info of shared binders is
reported so instance binders are re-declared as instance binders `[i : C α]`. Soundness does not depend
on this: every certificate is elaborated in the canonical context that a kernel-checked `R ↔ canonical`
ties to the original statement (`ProofScope.Linking.link_transport`).


`#proofscope_assumptions (R) (L)` telescopes both elaborated statements in step:

* binders with definitionally equal types are **shared**: model binders (types, operations, points)
  or shared hypotheses (Prop-typed, including Prop-valued typeclass instances);
* a Prop-typed binder present only in `L` is an **added assumption**, only in `R` a **dropped** one;
* an instance-implicit *data* binder present on one side only (`[Inhabited α]`, `[DecidableEq α]`) is
  the assumption `Nonempty (Cls)`;
* an added or dropped binder that later parts of the statement depend on is marked `dependent`; there is
  no well-typed statement without it, so downstream it is INCONCLUSIVE, never compared;
* the remaining conclusions are compared by definitional equality.

Output `PROOFSCOPE_ASSUMPTIONS <json>` with everything printed in the context of the shared binders.
-/

open Lean Meta Elab Command Term

namespace ProofScope.Assumptions11

def ppS (e : Expr) : MetaM String := do
  -- v1.1.1: `pp.analyze` adds the type ascriptions needed to re-elaborate the printed term
  -- (e.g. `(default : α)`), which the link certificates then check
  let fmt ← withOptions (fun o => (o.setBool `pp.funBinderTypes true).setBool `pp.numericTypes true
      |>.setBool `pp.fieldNotation false |>.setBool `pp.analyze true) (ppExpr e)
  return toString fmt

structure Acc where
  model : Array (Name × Expr) := #[]
  hyps : Array Expr := #[]
  added : Array (Expr × Bool) := #[]
  dropped : Array (Expr × Bool) := #[]
  -- v1.0.1: how many model binders and shared hypotheses precede each added/dropped assumption.
  -- A witness must instantiate *all* of them (a point `x : α` already proves `Nonempty α`).
  addedPrefix : Array (Nat × Nat) := #[]
  droppedPrefix : Array (Nat × Nat) := #[]
  fvars : Array Expr := #[]

def asAssumption (t : Expr) (bi : BinderInfo) : MetaM (Option Expr) := do
  if ← isProp t then return some t
  if bi.isInstImplicit then return some (← mkAppM ``Nonempty #[t])
  return none

def cleanName (n : Name) (k : Nat) : Name :=
  if n.hasMacroScopes || n.isInaccessibleUserName || n.isAnonymous || n.toString.contains '✝' then
    Name.mkSimple s!"i{k}"
  else n.eraseMacroScopes

partial def go (r l : Expr) (acc : Acc) (k : Acc → Expr → Expr → MetaM Json) : MetaM Json := do
  let r ← whnfCore r
  let l ← whnfCore l
  match r, l with
  | .forallE n t b bi, .forallE _ t' b' _ =>
    if ← isDefEq t t' then
      return ← withLocalDecl (cleanName n acc.fvars.size) bi t fun fv => do
        let acc := if ← isProp t then { acc with hyps := acc.hyps.push t, fvars := acc.fvars.push fv }
                   else { acc with model := acc.model.push (n, t), fvars := acc.fvars.push fv }
        go (b.instantiate1 fv) (b'.instantiate1 fv) acc k
    -- an assumption only in L?
    if let some a ← asAssumption t' (l.bindingInfo!) then
      return ← withLocalDecl `h bi t' fun fv => go r (b'.instantiate1 fv)
        { acc with added := acc.added.push (a, b'.hasLooseBVar 0), addedPrefix := acc.addedPrefix.push (acc.model.size, acc.hyps.size) } k
    if let some a ← asAssumption t bi then
      return ← withLocalDecl `h bi t fun fv => go (b.instantiate1 fv) l
        { acc with dropped := acc.dropped.push (a, b.hasLooseBVar 0), droppedPrefix := acc.droppedPrefix.push (acc.model.size, acc.hyps.size) } k
    k acc r l
  | .forallE n t b bi, _ =>
    if let some a ← asAssumption t bi then
      withLocalDecl n bi t fun fv => go (b.instantiate1 fv) l { acc with dropped := acc.dropped.push (a, b.hasLooseBVar 0), droppedPrefix := acc.droppedPrefix.push (acc.model.size, acc.hyps.size) } k
    else k acc r l
  | _, .forallE n t b bi =>
    if let some a ← asAssumption t bi then
      withLocalDecl n bi t fun fv => go r (b.instantiate1 fv) { acc with added := acc.added.push (a, b.hasLooseBVar 0), addedPrefix := acc.addedPrefix.push (acc.model.size, acc.hyps.size) } k
    else k acc r l
  | _, _ => k acc r l

elab "#proofscope_assumptions11 " r:term:max l:term:max : command => liftTermElabM do
  let R ← elabTerm r (some (mkSort .zero))
  let L ← elabTerm l (some (mkSort .zero))
  synthesizeSyntheticMVarsNoPostponing
  let R ← instantiateMVars R
  let L ← instantiateMVars L
  if R.hasMVar || L.hasMVar then throwError "statement has unresolved metavariables"
  let out ← go R L {} fun acc cr cl => do
    let same ← isDefEq cr cl
    -- binders in the scope of the assumptions: those occurring in a hypothesis or an added/dropped
    -- assumption, closed under "occurs in the type of a binder in scope"
    let props := acc.hyps ++ acc.added.map (·.1) ++ acc.dropped.map (·.1)
    let modelFvs := acc.fvars.filter fun fv => !(props.any (· == fv))
    let mut scope : Array Expr := #[]
    for fv in acc.fvars.reverse do
      let used := props.any (·.containsFVar fv.fvarId!) ||
        (← scope.anyM fun s => return (← inferType s).containsFVar fv.fvarId!)
      if used && !(← isProp (← inferType fv)) then scope := scope.push fv
    let _ := modelFvs
    let modelVars ← acc.fvars.filterM (fun fv => do return !(← isProp (← inferType fv)))
    let pair (x : Expr × Bool) : MetaM Json := do
      return Json.mkObj [("prop", ← ppS x.1), ("dependent", toJson x.2)]
    return Json.mkObj [
      ("model", Json.arr (← modelVars.mapM fun fv => do
          return Json.mkObj [("name", toJson (← fv.fvarId!.getUserName).toString), ("type", ← ppS (← inferType fv)),
                             ("inst", toJson (← fv.fvarId!.getBinderInfo).isInstImplicit),
                             ("in_scope", toJson (scope.contains fv))])),
      ("hyps", Json.arr (← acc.hyps.mapM fun h => return Json.str (← ppS h))),
      ("added", Json.arr (← acc.added.mapM pair)),
      ("dropped", Json.arr (← acc.dropped.mapM pair)),
      ("added_prefix", toJson (acc.addedPrefix.map fun (m, h) => [m, h])),
      ("dropped_prefix", toJson (acc.droppedPrefix.map fun (m, h) => [m, h])),
      ("conclusion_same", toJson same),
      ("conclusion_ref", ← ppS cr), ("conclusion_lean", ← ppS cl)]
  logInfo m!"PROOFSCOPE_ASSUMPTIONS11 {out.compress}"

end ProofScope.Assumptions11

namespace ProofScope.Assumptions11
open Lean Meta Elab Command

/-- Read the witnesses out of a checked existential proof term (`Exists.intro w h`, nested). The
witness is taken from the kernel-checked declaration, not from the search that produced it. -/
partial def witnessesOf (e : Expr) : MetaM (Array Expr) := do
  let e ← instantiateMVars e
  let e := e.consumeMData
  if e.isAppOfArity ``Exists.intro 4 then
    let w := e.getArg! 2
    return #[w] ++ (← witnessesOf (e.getArg! 3))
  let e' ← whnfCore e
  if e' != e then witnessesOf e' else return #[]

elab "#proofscope_witness11 " id:ident : command => liftTermElabM do
  let n ← realizeGlobalConstNoOverloadWithInfo id
  let some ci := (← getEnv).find? n | throwError "unknown declaration"
  let v ← match ci with
    | .thmInfo t => pure t.value
    | .defnInfo d => pure d.value
    | _ => throwError "no value"
  let ws ← witnessesOf v
  let strs ← ws.mapM fun w => do return toString (← withOptions (·.setBool `pp.funBinderTypes true) (ppExpr w))
  logInfo m!"PROOFSCOPE_WITNESS11 {(Json.arr (strs.map Json.str)).compress}"

end ProofScope.Assumptions11
