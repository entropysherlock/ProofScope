import Lean
/-!
# ClaimDelta abstraction (elaborator side)

`#proofscope_abstract (P) (Q)` elaborates two propositions, finds the **opaque symbols they share**
(applications whose head is outside the interpreted theory, cut at the longest closed argument
its implicit and instance arguments, e.g. `HPow.hPow` from `2 ^ n`, `Nat.gcd` from `Nat.gcd a b`), and for every nonempty
subset of those symbols prints both statements with that subset replaced by fresh variables.

Interpreted theory (policy `LINEAR_CORE_SHARED`): logical connectives, quantifiers, `=`, `≠`, `≤`, `<`, `≥`, `>`,
`+`, `-`, numerals, `Nat.succ`, `min`, `max`, multiplication by a numeral, `/` and `%` by a numeral,
divisibility by a numeral. Everything else is a candidate symbol.

Only symbols occurring in **both** statements are abstracted: a symbol used by one side only is part
of how that side is written, not shared mathematical content, so it stays interpreted.

Output: one line `PROOFSCOPE_ABSTRACT <json>`. Nothing here is trusted: every printed statement is
re-elaborated, and the link to the original (`(fun xs => body) syms ↔ original`) is checked by
`Iff.rfl` as a certificate obligation.
-/

open Lean Meta Elab Command Term

namespace ProofScope.Abstract

def interpretedHeads : List Name :=
  [``HAdd.hAdd, ``HSub.hSub, ``OfNat.ofNat, ``Nat.succ, ``LE.le, ``LT.lt, ``GE.ge, ``GT.gt, ``Eq, ``Ne,
   ``And, ``Or, ``Not, ``Iff, ``True, ``False, ``Neg.neg, ``Min.min, ``Max.max, ``Nat.cast, ``Int.ofNat,
   ``instOfNatNat, ``Exists, ``Nat.zero]

def isNumeral (e : Expr) : Bool :=
  e.isRawNatLit || (e.isAppOf ``OfNat.ofNat && e.getAppNumArgs == 3 && (e.getArg! 1).isRawNatLit)

/-- Is this application part of the interpreted theory? -/
def interpreted (e : Expr) : Bool :=
  let h := e.getAppFn
  match h.constName? with
  | none => true
  | some n =>
    if interpretedHeads.contains n then true
    else if n == ``HMul.hMul && e.getAppNumArgs == 6 then isNumeral (e.getArg! 4) || isNumeral (e.getArg! 5)
    else if (n == ``HDiv.hDiv || n == ``HMod.hMod) && e.getAppNumArgs == 6 then isNumeral (e.getArg! 5)
    else if n == ``Dvd.dvd && e.getAppNumArgs == 4 then isNumeral (e.getArg! 2)
    else false

/-- The symbol of an opaque application: its head with the leading *implicit and instance* arguments
(types, instances). Explicit arguments, including numerals, stay outside the symbol, so `2 ^ n` and
`3 ^ n` share the symbol `HPow.hPow` and a changed constant is a change of claim, not a change of symbol. -/
def symbolOf (e : Expr) : MetaM Expr := do
  let args := e.getAppArgs
  let info ← getFunInfoNArgs e.getAppFn args.size
  let mut k := 0
  for i in [:args.size] do
    let implicit := match info.paramInfo[i]? with
      | some p => !p.binderInfo.isExplicit
      | none => false
    if implicit && !args[i]!.hasLooseBVars && !args[i]!.hasFVar then k := i + 1 else break
  return mkAppN e.getAppFn (args.extract 0 k)

/-- Only explicit arguments carry mathematical content; types and typeclass instances are part of
the symbol (v0.8 fix: instances such as `instHAdd` were previously collected as symbols). -/
def explicitArgs (e : Expr) : MetaM (Array Expr) := do
  let args := e.getAppArgs
  let info ← getFunInfoNArgs e.getAppFn args.size
  let mut out := #[]
  for i in [:args.size] do
    match info.paramInfo[i]? with
    | some p => if p.binderInfo.isExplicit then out := out.push args[i]!
    | none => out := out.push args[i]!
  return out

partial def collect (e : Expr) (acc : Array Expr) : MetaM (Array Expr) := do
  match e with
  | .app .. =>
    let mut acc := acc
    if e.getAppFn.isConst && !interpreted e then
      let s ← symbolOf e
      unless acc.contains s do acc := acc.push s
    for a in ← explicitArgs e do acc ← collect a acc
    if !e.getAppFn.isConst then acc ← collect e.getAppFn acc
    return acc
  | .forallE _ t b _ => collect b (← collect t acc)
  | .lam _ t b _ => collect b (← collect t acc)
  | .mdata _ b => collect b acc
  | .letE _ t v b _ => collect b (← collect v (← collect t acc))
  | _ => return acc

def ppS (e : Expr) : MetaM String := do
  let fmt ← withOptions (fun o => (o.setBool `pp.funBinderTypes true).setBool `pp.numericTypes true
      |>.setBool `pp.fieldNotation false) (ppExpr e)
  return toString fmt

/-- Replace each symbol in `syms` by the matching free variable. -/
def abstractWith (e : Expr) (syms : Array Expr) (fvs : Array Expr) : Expr :=
  e.replace fun t => match syms.findIdx? (· == t) with
    | some i => some fvs[i]!
    | none => none

elab "#proofscope_abstract " p:term:max q:term:max : command => liftTermElabM do
  let P ← elabTerm p (some (mkSort .zero))
  let Q ← elabTerm q (some (mkSort .zero))
  synthesizeSyntheticMVarsNoPostponing
  let P ← instantiateMVars P
  let Q ← instantiateMVars Q
  if P.hasMVar || Q.hasMVar then throwError "statement has unresolved metavariables"
  let sp ← collect P #[]
  let sq ← collect Q #[]
  let shared := sp.filter (sq.contains ·)
  let only := (sp.filter (!shared.contains ·)) ++ (sq.filter (!shared.contains ·))
  let shared := shared.extract 0 4
  let mut syms : Array Json := #[]
  for s in shared do
    syms := syms.push (Json.mkObj [("symbol", ← ppS s), ("type", ← ppS (← inferType s))])
  let mut subsets : Array Json := #[]
  let n := shared.size
  for mask in [1:2 ^ n] do
    let idx := (List.range n).filter (fun i => (mask >>> i) % 2 == 1)
    let chosen := (idx.map (shared[·]!)).toArray
    let decls ← chosen.mapIdxM fun j s => return ((Name.mkSimple s!"x{idx[j]! + 1}"), ← inferType s)
    let entry ← withLocalDeclsDND decls fun fvs => do
      let pb ← ppS (abstractWith P chosen fvs)
      let qb ← ppS (abstractWith Q chosen fvs)
      return Json.mkObj [("symbols", toJson (idx.map (· + 1))), ("ref", pb), ("lean", qb)]
    subsets := subsets.push entry
  let out := Json.mkObj [("policy", "LINEAR_CORE_SHARED"), ("symbols", Json.arr syms),
    ("one_sided_symbols", Json.arr (← only.mapM fun s => return Json.str (← ppS s))),
    ("truncated", toJson (decide (sp.size + sq.size > 0 && shared.size == 4))),
    ("ref", ← ppS P), ("lean", ← ppS Q), ("subsets", Json.arr subsets)]
  logInfo m!"PROOFSCOPE_ABSTRACT {out.compress}"

end ProofScope.Abstract
