import Lean
/-!
# Drift extraction (elaborator side)

`#proofscope_drift (R) (L)` elaborates a reference `R` and a formal statement `L` and prints one line
`PROOFSCOPE_DRIFT <json>` with:

* the **edit sites**: a simultaneous traversal of the two elaborated terms, entering binders with
  shared types (fresh local variables) and applications with the same head and the same implicit
  arguments; every other mismatch is one edit `from → to`;
* the **chain** `S₀ = R, S₁, …, Sₙ = L`, where `Sₖ` applies the first `k` edits (each `Sₖ` is a
  well-scoped elaborated term; it is re-elaborated from its printed form and checked downstream);
* the **shared symbols** of `R` and `L` (operators outside linear arithmetic and logic, cut at their
  implicit/instance arguments) and every `Sₖ` abstracted over the **same** symbols, so that all step
  certificates live in one interpretation space and the composition theorems of
  `DriftSoundness.lean` apply.

v0.9 abstraction is **per occurrence**: only applications that are opaque under the policy are
abstracted; interpreted uses of the same operator (`2 * n`) stay concrete (fixes the documented
v0.8 defect without touching the frozen v0.8 engine).
-/

open Lean Meta Elab Command Term

namespace ProofScope.Drift

def interpretedHeads : List Name :=
  [``HAdd.hAdd, ``HSub.hSub, ``OfNat.ofNat, ``Nat.succ, ``LE.le, ``LT.lt, ``GE.ge, ``GT.gt, ``Eq, ``Ne,
   ``And, ``Or, ``Not, ``Iff, ``True, ``False, ``Neg.neg, ``Min.min, ``Max.max, ``Nat.cast, ``Int.ofNat,
   ``instOfNatNat, ``Exists, ``Nat.zero, ``List.nil, ``List.cons, ``Int.negSucc]

def isNumeral (e : Expr) : Bool :=
  e.isRawNatLit || (e.isAppOf ``OfNat.ofNat && e.getAppNumArgs == 3 && (e.getArg! 1).isRawNatLit)

def interpreted (e : Expr) : Bool :=
  match e.getAppFn.constName? with
  | none => true
  | some n =>
    if interpretedHeads.contains n then true
    else if n == ``HMul.hMul && e.getAppNumArgs == 6 then isNumeral (e.getArg! 4) || isNumeral (e.getArg! 5)
    else if (n == ``HDiv.hDiv || n == ``HMod.hMod) && e.getAppNumArgs == 6 then isNumeral (e.getArg! 5)
    else if n == ``Dvd.dvd && e.getAppNumArgs == 4 then isNumeral (e.getArg! 2)
    else false

def explicitMask (e : Expr) : MetaM (Array Bool) := do
  let info ← getFunInfoNArgs e.getAppFn e.getAppNumArgs
  return (Array.range e.getAppNumArgs).map fun i =>
    match info.paramInfo[i]? with
    | some p => p.binderInfo.isExplicit
    | none => true

def symbolOf (e : Expr) : MetaM Expr := do
  let args := e.getAppArgs
  let m ← explicitMask e
  let mut k := 0
  for i in [:args.size] do
    if !m[i]! && !args[i]!.hasLooseBVars && !args[i]!.hasFVar then k := i + 1 else break
  return mkAppN e.getAppFn (args.extract 0 k)

def opaqueApp (e : Expr) : Bool := e.isApp && e.getAppFn.isConst && !interpreted e

partial def collect (e : Expr) (acc : Array Expr) : MetaM (Array Expr) := do
  match e with
  | .app .. =>
    let mut acc := acc
    if opaqueApp e then
      let s ← symbolOf e
      unless acc.contains s do acc := acc.push s
    let args := e.getAppArgs
    let m ← explicitMask e
    for i in [:args.size] do
      if m[i]! then acc ← collect args[i]! acc
    if !e.getAppFn.isConst then acc ← collect e.getAppFn acc
    return acc
  -- binder types are types, not mathematical claims: never collected as symbols
  | .forallE _ t b _ => if b.hasLooseBVar 0 then collect b acc else collect b (← collect t acc)
  | .lam _ _ b _ => collect b acc
  | .mdata _ b => collect b acc
  | .letE _ _ v b _ => collect b (← collect v acc)
  | _ => return acc

/-- Replace opaque occurrences of `syms[i]` by `fvs[i]` (per occurrence, not every syntactic match). -/
partial def abstractOcc (syms fvs : Array Expr) (e : Expr) : MetaM Expr := do
  match e with
  | .app .. =>
    let args := e.getAppArgs
    if opaqueApp e then
      let s ← symbolOf e
      if let some i := syms.findIdx? (· == s) then
        let rest ← (args.extract s.getAppNumArgs args.size).mapM (abstractOcc syms fvs)
        return mkAppN fvs[i]! rest
    let f ← if e.getAppFn.isConst then pure e.getAppFn else abstractOcc syms fvs e.getAppFn
    return mkAppN f (← args.mapM (abstractOcc syms fvs))
  | .forallE n t b bi => return .forallE n (← abstractOcc syms fvs t) (← abstractOcc syms fvs b) bi
  | .lam n t b bi => return .lam n (← abstractOcc syms fvs t) (← abstractOcc syms fvs b) bi
  | .mdata _ b => abstractOcc syms fvs b
  | _ => return e

def ppS (e : Expr) : MetaM String := do
  let fmt ← withOptions (fun o => (o.setBool `pp.funBinderTypes true).setBool `pp.numericTypes true
      |>.setBool `pp.fieldNotation false) (ppExpr e)
  return toString fmt

/-- Simultaneous traversal. Takes `L`'s side at the first `k` edit sites; records every edit. -/
partial def hybrid (k : Nat) (p q : Expr) : StateT (Nat × Array (String × String)) MetaM Expr := do
  if p == q then return p
  let edit : StateT (Nat × Array (String × String)) MetaM Expr := do
    let (c, log) ← get
    set (c + 1, log.push (← ppS p, ← ppS q))
    return if c < k then q else p
  match p, q with
  | .mdata _ p', _ => hybrid k p' q
  | _, .mdata _ q' => hybrid k p q'
  | .forallE n t b bi, .forallE _ t' b' _ =>
    if !b.hasLooseBVar 0 && !b'.hasLooseBVar 0 then
      -- implication: hypothesis and conclusion are separate edit sites
      let t2 ← hybrid k t t'
      let b2 ← hybrid k (b.lowerLooseBVars 1 1) (b'.lowerLooseBVars 1 1)
      return .forallE n t2 b2 bi
    else if t == t' then
      withLocalDecl n bi t fun fv => do
        let r ← hybrid k (b.instantiate1 fv) (b'.instantiate1 fv)
        mkForallFVars #[fv] r
    else edit
  | .lam n t b bi, .lam _ t' b' _ =>
    if t == t' then
      withLocalDecl n bi t fun fv => do
        let r ← hybrid k (b.instantiate1 fv) (b'.instantiate1 fv)
        mkLambdaFVars #[fv] r
    else edit
  | .app .., .app .. =>
    let (fp, ap) := (p.getAppFn, p.getAppArgs)
    let (fq, aq) := (q.getAppFn, q.getAppArgs)
    if fp == fq && ap.size == aq.size then
      let m ← explicitMask p
      let diffExplicit := (List.range ap.size).filter (fun i => m[i]! && ap[i]! != aq[i]!)
      -- v0.9.1: recurse only when exactly one explicit argument differs; a change in several arguments
      -- (an argument permutation such as `gcd a b` → `gcd b a`, or `x = 1` → `1 = x`) is ONE edit, so no
      -- meaningless intermediate statement (`gcd b b`) is ever built.
      if diffExplicit.length == 1 && (List.range ap.size).all (fun i => m[i]! || ap[i]! == aq[i]!) then
        let mut out := #[]
        for i in [:ap.size] do
          out := out.push (← if m[i]! then hybrid k ap[i]! aq[i]! else pure ap[i]!)
        return mkAppN fp out
    edit
  | _, _ => edit

elab "#proofscope_drift " r:term:max l:term:max : command => liftTermElabM do
  let R ← elabTerm r (some (mkSort .zero))
  let L ← elabTerm l (some (mkSort .zero))
  synthesizeSyntheticMVarsNoPostponing
  let R ← instantiateMVars R
  let L ← instantiateMVars L
  if R.hasMVar || L.hasMVar then throwError "statement has unresolved metavariables"
  let (_, (n, edits)) ← (hybrid 0 R L).run (0, #[])
  let sr ← collect R #[]
  let sl ← collect L #[]
  let shared0 := sr.filter (sl.contains ·)
  let shared := shared0.extract 0 3
  let decls ← shared.mapIdxM fun j s => return (Name.mkSimple s!"x{j + 1}", ← inferType s)
  let mut chain : Array Json := #[]
  for k in [:n + 1] do
    let (S, _) ← (hybrid k R L).run (0, #[])
    let concrete ← ppS S
    let abs ← withLocalDeclsDND decls fun fvs => do ppS (← abstractOcc shared fvs S)
    chain := chain.push (Json.mkObj [("concrete", concrete), ("abstract", abs)])
  let syms ← shared.mapM fun s => return Json.mkObj [("symbol", ← ppS s), ("type", ← ppS (← inferType s))]
  let out := Json.mkObj [
    ("policy", "LINEAR_CORE_SHARED_OCC"),
    ("symbols", Json.arr syms), ("symbols_truncated", toJson (decide (shared0.size > 3))),
    ("edits", Json.arr (edits.map fun (a, b) => Json.mkObj [("from", a), ("to", b)])),
    ("chain", Json.arr chain)]
  logInfo m!"PROOFSCOPE_DRIFT {out.compress}"

end ProofScope.Drift
