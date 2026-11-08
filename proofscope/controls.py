"""Positive/negative kernel controls.

Before trusting any "certified" result we check that this machine's checker can tell an honest module
from a forged one. The forged module inserts `kc_forged : False := True.intro` with kernel type checking
switched off. The elaborator accepts it and `#print axioms` reports no axioms, so only kernel replay can
catch it. If leanchecker accepts the forged module, replay results on this machine are worthless.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from .toolchain import Toolchain

GOOD = """\
-- ProofScope positive control: honest module, core Lean only.
theorem kc_good_add : 1 + 1 = 2 := rfl
theorem kc_good_zero_add (n : Nat) : 0 + n = n := Nat.zero_add n
"""

FORGED = """\
-- ProofScope negative control: deliberately forged declaration. Never import this module.
import Lean
open Lean Elab Command

set_option debug.skipKernelTC true in
run_cmd liftCoreM <| addDecl (.thmDecl
  { name := `kc_forged, levelParams := [], type := mkConst ``False, value := mkConst ``True.intro })

#print axioms kc_forged
"""


def run_controls(tc: Toolchain, workdir: Path | None = None) -> dict:
    root = Path(workdir or tempfile.mkdtemp(prefix="proofscope_kc_"))
    src = root / "src" / "KernelControl"
    build = root / "build"
    src.mkdir(parents=True, exist_ok=True)
    (src / "Good.lean").write_text(GOOD)
    (src / "Forged.lean").write_text(FORGED)

    res: dict = {"workdir": str(root), "steps": {}}
    for name in ("Good", "Forged"):
        c = tc.compile(src / f"{name}.lean", build / "KernelControl" / f"{name}.olean", root / "src")
        res["steps"][f"compile_{name}"] = c.as_dict()
    forged_compile = res["steps"]["compile_Forged"]
    res["forged_axioms_look_clean"] = "does not depend on any axioms" in forged_compile["output_tail"]

    good = tc.replay("KernelControl.Good", build, fresh=False)
    forged = tc.replay("KernelControl.Forged", build, fresh=False)
    res["steps"]["replay_Good"] = good.as_dict()
    res["steps"]["replay_Forged"] = forged.as_dict()

    res["honest_accepted"] = (res["steps"]["compile_Good"]["returncode"] == 0 and good.returncode == 0)
    res["forged_rejected"] = (forged_compile["returncode"] == 0 and forged.returncode != 0
                              and "kc_forged" in forged.output)
    res["passed"] = bool(res["honest_accepted"] and res["forged_rejected"])
    return res
