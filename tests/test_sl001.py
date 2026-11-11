import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("sl001", Path(__file__).parent.parent / "experiments/SL-001/sl001.py")
sl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sl)

SRC = """
def Foo (k m : ℕ) : Prop :=
  ∀ n, n < m

@[category research open, AMS 11]
theorem erdos_1 : answer(sorry) ↔
    ∃ C > 0, ∀ k, k ≤ C := by
  sorry

theorem erdos_1.variants.x (n : ℕ) : n = n := rfl
"""


def test_statement_extraction_and_answer_wrapper():
    st = sl.theorem_statement(SRC, "erdos_1")
    assert st == ": answer(sorry) ↔ ∃ C > 0, ∀ k, k ≤ C"
    body, wrapped = sl.strip_answer(st)
    assert wrapped and body == ": ∃ C > 0, ∀ k, k ≤ C"
    assert sl.strip_answer(": P")[1] is False
    assert sl.theorem_statement(SRC, "erdos_1.variants.x") == "(n : ℕ) : n = n"
    assert sl.theorem_statement(SRC, "erdos_2") is None      # prefix must not match erdos_1


def test_decl_at_line_and_defs():
    lines = SRC.split("\n")
    ln = next(i for i, l in enumerate(lines) if l.startswith("theorem erdos_1 ")) + 1
    name, st = sl.decl_at_line(SRC, ln)
    assert name == "erdos_1" and "answer(sorry)" in st
    assert sl.defs(SRC)["Foo"].startswith("(k m : ℕ) : Prop")


def test_frozen_cases_are_well_formed():
    import json
    cases = [json.loads(l) for l in (Path(sl.__file__).parent / "cases.jsonl").read_text().splitlines()]
    assert len(cases) == 18 and len({c["case_id"] for c in cases}) == 18
    assert all(c["oai_commit_linked"] == sl.OAI_LINKED for c in cases)


def test_core_and_polarity_and_qualified_name():
    assert sl.core(": answer(sorry) ↔ ∃ x, P x") == ("∃ x, P x", "open")
    assert sl.core(": answer(False) ↔ ∃ x, P x") == ("∃ x, P x", "neg")
    assert sl.core(": ¬ ∃ x, P x") == ("∃ x, P x", "neg")
    assert sl.core(": ¬ (∃ x, P x)") == ("∃ x, P x", "neg")
    assert sl.core(": ∃ x, P x") == ("∃ x, P x", "pos")
    src = "namespace OAI\nnamespace A\nend A\nnamespace B\ntheorem main : T := by\n"
    assert sl.qualified_name(src, 5, "main") == "OAI.B.main"
