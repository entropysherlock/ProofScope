import Lean
open Lean Elab Command

-- Deliberate negative control. Do NOT import as a trusted dependency.
set_option debug.skipKernelTC true in
run_cmd liftCoreM <| addDecl (.thmDecl
  { name := `kc_forged, levelParams := [], type := mkConst ``False, value := mkConst ``True.intro })

#print axioms kc_forged
