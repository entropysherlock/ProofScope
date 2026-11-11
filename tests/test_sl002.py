import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("sl002check", Path(__file__).parent.parent / "experiments/SL-002/check.py")
ck = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ck)

OURS = """
/-- doc -/
def FCStatement : Prop :=
  ¬ ∃ (x : ℕ → ℤ) (C : ℤ),
    ∀ n, x n < C

theorem erdos_9 :
  ¬ ∃ (x : ℕ → ℤ) (C : ℤ),
    ∀ n, x n < C :=
  foo
"""
FC = """
@[category research solved]
theorem erdos_9 :
  ¬ ∃ (x : ℕ → ℤ) (C : ℤ),
      ∀ n, x n < C := by
  sorry
"""


def test_whitespace_insensitive_match():
    d = ck.def_body(OURS, "FCStatement").removeprefix(": Prop :=").strip()
    assert d == ck.thm_stmt(FC, "erdos_9").removeprefix(":").strip()
    assert ck.thm_stmt(OURS, "erdos_9") == ck.thm_stmt(FC, "erdos_9")


def test_one_character_change_detected():
    changed = FC.replace("x n < C", "x n ≤ C")
    assert ck.thm_stmt(OURS, "erdos_9") != ck.thm_stmt(changed, "erdos_9")


def test_escape_scan_pattern():
    assert ck.ESCAPES.search("theorem t : P := by sorry")
    assert ck.ESCAPES.search("axiom bad : False")
    assert not ck.ESCAPES.search("theorem t : P := by simpa using h")
