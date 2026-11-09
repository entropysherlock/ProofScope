import Lean
/-!
# CJCS one-process search (SOTA-4, experimental). UNTRUSTED.

`#cjcs_search "<json>"` runs the SOTA-3 CJCS obligation search inside an already-initialized environment
(one Lean REPL process per pair). It only *proposes*: for every obligation it reports the index of the
first tactic alternative that elaborated. Nothing it reports is a certificate. The engine writes a clean
certificate module containing exactly the proposed alternatives, which an independent `lean` process
compiles and `leanchecker` replays, with the unchanged axiom policy (`proofscope/certify.py`).

Semantics kept from SOTA-3 (`proofscope/certify.py` + `proofscope/experimental/cjcs.py`):

* An obligation `k : S` with alternatives `t₀ … tₙ` is elaborated as the same declaration SOTA-3 used,
  `theorem k : S := by first | ((t₀); done) | … | ((tₙ); done)`, under the same `maxHeartbeats 200000`,
  with one addition: each alternative is followed by `trace "CJCS_ALT i"`. `first` keeps the state
  (including messages) of the first alternative that closes the goal and discards the others, so exactly
  one marker survives and names the alternative `first` chose. Heartbeat and recursion-depth exceptions
  are not caught by `first` (checked on Lean 4.34.1) and fail the declaration, as before.
* `Elab.async false`: the proof is elaborated synchronously so its messages are visible to the search.
* An obligation whose dependencies did not succeed is not attempted (`dep_failed`); in SOTA-3 it was
  attempted and, because Lean keeps a failed declaration (with `sorryAx`) in the environment, a dependent
  obligation could pass the SOTA-3 probe and then break the whole certificate module (finding F3).
* A declaration is kept in the search environment only if it produced no error and does not depend on
  `sorryAx`; otherwise the command state is restored exactly, so a failed attempt can never be used by a
  later obligation.

The verifier is authoritative regardless of anything reported here.
-/

open Lean Elab Command

namespace ProofScope.CJCSSearch

structure Ob where
  name : String
  stmt : String
  alts : Array String
  deps : Array String := #[]
  deriving FromJson, Inhabited

structure Req where
  obligations : Array Ob
  budget : Nat := 200000
  deriving FromJson

/-- Run one command given as source text in the current command state; report whether it elaborated
without error messages. Messages produced by the attempt are discarded; a failed attempt leaves the
environment unchanged. -/
def axiomsOf (n : Name) : CommandElabM (Array Name) := collectAxioms n

/-- Elaborate `src`; keep the result only if it produced no error, declared `full`, and `full` does not
depend on `sorryAx`. Otherwise the command state is restored exactly. -/
def attempt (src : String) (full : Name) : CommandElabM (Bool × String × Option Nat) := do
  let saved ← get
  match Parser.runParserCategory (← getEnv) `command src "<cjcs_search>" with
  | .error e => return (false, s!"parse: {e}", none)
  | .ok cmd =>
    modify fun st => { st with messages := {} }
    let ok ← try
        elabCommand cmd
        pure !(← get).messages.hasErrors
      catch _ => pure false
    let ok ← if ok then
        if !(← getEnv).contains full then pure false
        else pure !(← axiomsOf full).contains ``sorryAx
      else pure false
    let firstErr ← if ok then pure "" else do
      let ms := (← get).messages.toList.filter (·.severity == .error)
      match ms.head? with
      | some m => pure ((← m.data.toString).take 300).toString
      | none => pure "declaration missing or depends on sorryAx"
    let mut alt? : Option Nat := none
    for m in (← get).messages.toList do
      if m.severity == .information then
        let t ← m.data.toString
        match (t.splitOn "CJCS_ALT ") with
        | [_, n] => alt? := n.trimAscii.toString.toNat?
        | _ => pure ()
    let ok := ok && alt?.isSome
    let env ← getEnv
    if ok then
      set { saved with env := env }
    else
      set saved
    return (ok, firstErr, alt?)

elab "#cjcs_search " s:str : command => do
  let req : Req ← match Json.parse s.getString >>= fromJson? with
    | .ok r => pure r
    | .error e => throwError "cjcs_search: bad request: {e}"
  let ns ← getCurrNamespace
  let mut good : Std.HashSet String := {}
  let mut rows : Array Json := #[]
  for ob in req.obligations do
    let env ← getEnv
    -- a dependency is met if it was proposed in this request or is already a declaration of the
    -- environment (proposed by an earlier request of the same session)
    if !(ob.deps.all fun d => good.contains d || env.contains (ns ++ d.toName)) then
      rows := rows.push (Json.mkObj [("name", Json.str ob.name), ("status", Json.str "dep_failed")])
      continue
    let h0 ← IO.getNumHeartbeats
    -- exactly the SOTA-3 declaration (`proofscope/certify.py`, `_theorem`), with a success marker after
    -- each alternative: `first` keeps the state (and messages) of the first alternative that closes the goal
    -- and discards the others, so exactly one marker survives and names the alternative `first` chose
    let alts := (List.range ob.alts.size).map fun i =>
      s!"    | ((({ob.alts[i]!}); done); trace \"CJCS_ALT {i}\")"
    let src := s!"set_option Elab.async false in\nset_option maxHeartbeats {req.budget} in\n" ++
      s!"theorem {ob.name} : {ob.stmt} := by\n  first\n" ++ "\n".intercalate alts
    let (ok, err, alt?) ← attempt src (ns ++ ob.name.toName)
    let exhausted := !ok && ((err.splitOn "deterministic) timeout").length > 1 ||
      (err.splitOn "maximum recursion depth").length > 1)
    let won : Option Nat := if ok then alt? else none
    let tried := ob.alts.size
    let lastErr := err
    let spent := ((← IO.getNumHeartbeats) - h0) / 1000
    match won with
    | some i =>
      good := good.insert ob.name
      rows := rows.push (Json.mkObj [("name", Json.str ob.name), ("status", Json.str "proposed"),
        ("alt", toJson i), ("tried", toJson tried), ("heartbeats_k", toJson spent)])
    | none =>
      rows := rows.push (Json.mkObj [("name", Json.str ob.name),
        ("status", Json.str (if exhausted then "budget_exhausted" else "failed")),
        ("tried", toJson tried), ("heartbeats_k", toJson spent), ("last_error", Json.str lastErr)])
  logInfo m!"CJCS_SEARCH {(Json.arr rows).compress}"

end ProofScope.CJCSSearch
