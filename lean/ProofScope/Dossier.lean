import Lean

/-!
# ProofScope theorem intelligence

`#proofscope_dossier n₁ n₂ …` and `#proofscope_dossier_module M` emit one JSON object per declaration,
computed from the *elaborated* declaration in the environment (not from source text):

* kind, universe parameters, pretty-printed type and conclusion;
* every leading ∀-binder with its binder info, and a role: `hypothesis` (a proposition),
  `instance` (typeclass machinery) or `parameter` (data);
* the quantifier prefix of the conclusion (∀/∃/∧/∨/→/¬/↔ head symbols, depth-limited);
* statement dependencies (constants in the type) and direct proof dependencies (constants in the value
  that are not in the type), each with the module that declares it;
* the axioms the declaration transitively depends on (`Lean.collectAxioms`);
* declaration ranges and module.

Lines are logged as `PROOFSCOPE_DOSSIER <json>`. Nothing here is a proof; `kernel_status` is filled in by
the driver after `leanchecker` replay.
-/

open Lean Elab Command Meta

namespace ProofScope

def modOf (env : Environment) (n : Name) : String :=
  match env.getModuleIdxFor? n with
  | some i => toString (env.header.moduleNames[i.toNat]!)
  | none => "(this file)"

def binderInfoStr : BinderInfo → String
  | .default => "explicit" | .implicit => "implicit"
  | .strictImplicit => "strict_implicit" | .instImplicit => "instance_implicit"

/-- Head-symbol skeleton of a proposition, e.g. `∀ → ∃ ∧`. -/
partial def shape (e : Expr) (depth : Nat := 6) : MetaM (List String) := do
  if depth == 0 then return ["…"]
  let e ← whnfR e
  match e with
  | .forallE _ d b _ =>
    if (← isProp d) && !b.hasLooseBVars then
      return "→" :: (← shape b (depth - 1))
    else
      return "∀" :: (← withLocalDeclD `x d fun x => shape (b.instantiate1 x) (depth - 1))
  | _ =>
    match e.getAppFnArgs with
    | (``Exists, #[_, p]) =>
      match p with
      | .lam n d b bi => return "∃" :: (← withLocalDecl n bi d fun x => shape (b.instantiate1 x) (depth - 1))
      | _ => return ["∃"]
    | (``And, #[a, b]) => return ["∧(" ++ " ".intercalate (← shape a (depth - 1)) ++ " | "
                                   ++ " ".intercalate (← shape b (depth - 1)) ++ ")"]
    | (``Or, #[_, _]) => return ["∨"]
    | (``Iff, #[_, _]) => return ["↔"]
    | (``Not, #[_]) => return ["¬"]
    | (``Eq, _) => return ["="]
    | (``LE.le, _) => return ["≤"]
    | (``LT.lt, _) => return ["<"]
    | (``Ne, _) => return ["≠"]
    | (``False, _) => return ["False"]
    | (``True, _) => return ["True"]
    | (f, _) => return [if f.isAnonymous then "atom" else toString f]

/-- `machinery`: instances, class projections (notation such as `+`, `≤`, `OfNat.ofNat`) and the logical
connectives; `definition`: a definition whose meaning a reviewer may need to check; `type`/`theorem`/... otherwise. -/
def depRole (env : Environment) (n : Name) : String :=
  let logical := [``Eq, ``Ne, ``Not, ``And, ``Or, ``Iff, ``Exists, ``True, ``False]
  if logical.contains n then "logic"
  else if isInstanceCore env n then "machinery"
  else if (env.getProjectionFnInfo? n).any (·.fromClass) then "machinery"
  -- reducible notation definitions shipped with Lean itself, such as `GE.ge` and `GT.gt`
  else if getReducibilityStatusCore env n == .reducible
      && ["Init", "Lean", "Std"].contains ((modOf env n).splitOn ".").head! then "machinery"
  else match env.find? n with
    | some (.defnInfo _) => "definition"
    | some (.opaqueInfo _) => "definition"
    | some (.inductInfo _) => "type"
    | some (.ctorInfo _) => "constructor"
    | some (.thmInfo _) => "theorem"
    | some (.axiomInfo _) => "axiom"
    | _ => "other"

def constList (env : Environment) (ns : Array Name) : Json :=
  Json.arr <| (ns.qsort Name.lt).map fun n =>
    Json.mkObj [("name", toString n), ("module", modOf env n), ("role", depRole env n)]

def isInteresting (env : Environment) (n : Name) : Bool :=
  !n.isInternal && !isAuxRecursor env n && !isNoConfusion env n && !(n.isStr && n.getString!.startsWith "proof_")

def dossier (n : Name) : CommandElabM Json := do
  let env ← getEnv
  let some ci := env.find? n | return Json.mkObj [("theorem_id", toString n), ("error", "unknown constant")]
  let kind := match ci with
    | .thmInfo _ => "theorem" | .defnInfo _ => "definition" | .axiomInfo _ => "axiom"
    | .opaqueInfo _ => "opaque" | .inductInfo _ => "inductive" | .ctorInfo _ => "constructor"
    | .recInfo _ => "recursor" | .quotInfo _ => "quotient"
  let tyConsts := ci.type.getUsedConstants
  let valConsts := match ci.value? (allowOpaque := true) with
    | some v => v.getUsedConstants.filter (fun c => !tyConsts.contains c)
    | none => #[]
  let axioms ← liftCoreM <| collectAxioms n
  let ranges ← liftCoreM <| findDeclarationRanges? n
  let (typeStr, binders, conclStr, shp) ← liftTermElabM <| do
    let tyS := toString (← ppExpr ci.type)
    forallTelescope ci.type fun xs body => do
      let mut bs : Array Json := #[]
      for x in xs do
        let d ← x.fvarId!.getDecl
        let isP ← isProp d.type
        let isCls := (← isClass? d.type).isSome
        let role := if d.binderInfo == .instImplicit || isCls then "instance"
                    else if isP then "hypothesis" else "parameter"
        let nm := if d.userName.hasMacroScopes then "_inst" else toString d.userName
        bs := bs.push <| Json.mkObj [("name", nm), ("binder", binderInfoStr d.binderInfo),
                                     ("role", role), ("type", toString (← ppExpr d.type))]
      let cS := toString (← ppExpr body)
      let sh ← if (← isProp body) then shape body else pure ["(not a proposition)"]
      return (tyS, bs, cS, sh)
  let unresolved : List String :=
    ["transitive proof dependencies are not enumerated (only direct ones); axioms are transitive"]
      ++ (if ranges.isNone then ["no declaration ranges stored for this declaration"] else [])
  return Json.mkObj [
    ("theorem_id", toString n), ("kind", kind), ("module", modOf env n),
    ("universe_params", Json.arr (ci.levelParams.toArray.map (fun l => Json.str (toString l)))),
    ("elaborated_type", typeStr), ("binders", Json.arr binders),
    ("hypotheses", Json.arr (binders.filter (fun b => b.getObjValD "role" == Json.str "hypothesis"))),
    ("conclusion", conclStr), ("conclusion_shape", " ".intercalate shp),
    ("statement_dependencies", constList env tyConsts),
    ("proof_dependencies", constList env valConsts),
    ("axioms", Json.arr ((axioms.qsort Name.lt).map (fun a => Json.str (toString a)))),
    ("source_locations", match ranges with
      | some r => Json.mkObj [("start_line", r.range.pos.line), ("end_line", r.range.endPos.line)]
      | none => Json.null),
    ("unresolved_items", Json.arr (unresolved.toArray.map Json.str))]

def emit (n : Name) : CommandElabM Unit := do
  logInfo m!"PROOFSCOPE_DOSSIER {(← dossier n).compress}"

syntax (name := dossierCmd) "#proofscope_dossier" (ppSpace ident)+ : command
syntax (name := dossierModCmd) "#proofscope_dossier_module" ident (num)? : command

@[command_elab dossierCmd] def elabDossier : CommandElab := fun stx => do
  for id in stx[1].getArgs do
    let n ← liftCoreM <| realizeGlobalConstNoOverloadWithInfo id
    emit n

/-- Dossiers for every theorem declared in module `M` (optionally the first `k`, in name order). -/
@[command_elab dossierModCmd] def elabDossierModule : CommandElab := fun stx => do
  let env ← getEnv
  let m := stx[1].getId
  let some idx := env.getModuleIdx? m | throwError "module {m} is not imported"
  let limit := if stx[2].isNone then 1000000 else stx[2][0].isNatLit?.getD 1000000
  let names := (env.header.moduleData[idx.toNat]!.constNames).filter fun n =>
    isInteresting env n && (env.find? n).any (·.isTheorem)
  for n in ((names.qsort Name.lt).toList.take limit) do
    emit n

end ProofScope
