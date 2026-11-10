# ProofScope SOTA-9 — single Colab cell (paste into one code cell and run; Python 3, CPU runtime).
# Core mode (default): about 4–5 min on a fresh runtime, about 3 min when Lean/REPL are already cached in this runtime. Mathlib mode (MATHLIB=True): add roughly 5–15 min, and ~6 GB disk.
# Nothing persists unless DRIVE_CACHE=True; the cache is then re-verified by SHA-256 / git commit before use.
BRANCH, COMMIT = "research/sota9-usable-auditor", None      # set COMMIT to an exact sha to pin the run
MATHLIB = False          # True: also fetch pinned Mathlib + precompiled cache, enable `import Mathlib`
DRIVE_CACHE = False      # True: keep the Lean archive and built REPL in Google Drive between sessions
LAUNCH_UI = True         # start the researcher UI in an output window at the end
EXPENSIVE = False        # True: full 88-test regression (+~2 min); never runs benchmarks

import hashlib, json, os, shutil, subprocess, sys, time, threading
from pathlib import Path
if Path("/content").exists(): os.chdir("/content")   # the old working folder may have been deleted
T0 = time.time(); ROOT = Path(os.environ.get("PS_ROOT", "/content")); SRC = os.environ.get("PS_SRC", "https://github.com/entropysherlock/ProofScope")
LEAN_V, LEAN_SHA = "4.34.1", "47bf4bbd78f70c2e9670598ab7124d92b6efb7330ff33e5fbb4030f6fd72e4e4"
REPL_SHA, MATHLIB_SHA = "193cf4bb9a22bb3fc6d25774f0fe6a70db1fd6ee", "d13f23b723b8a846827a245b89c10fc7d3f11612"
STEPS = []

def sh(cmd, cwd=None, env=None, check=True, quiet=False):
    t = time.time(); p = subprocess.run(cmd, shell=True, cwd=cwd, env=env, text=True, capture_output=True)
    if not quiet or p.returncode: print((p.stdout + p.stderr)[-3000:])
    if check and p.returncode: raise RuntimeError(f"step failed ({p.returncode}): {cmd}")
    return p

def step(name, fn):
    t = time.time(); print(f"\n▶ {name}", flush=True)
    try:
        r = fn(); STEPS.append((name, "ok", round(time.time() - t, 1))); return r
    except Exception as e:
        STEPS.append((name, f"FAIL: {e}", round(time.time() - t, 1))); raise

cache = ROOT / "ps_cache"
if DRIVE_CACHE:
    from google.colab import drive; drive.mount("/content/drive"); cache = Path("/content/drive/MyDrive/proofscope_cache")
cache.mkdir(parents=True, exist_ok=True)
repo, lean_dir, repl_dir = ROOT / "ProofScope", ROOT / f"lean-{LEAN_V}", cache / f"repl-{REPL_SHA[:12]}-lean{LEAN_V}"

def get_repo():
    if repo.exists(): shutil.rmtree(repo)
    sh(f"git clone -q --branch {BRANCH} {SRC} {repo}")
    if COMMIT: sh(f"git checkout -q {COMMIT}", cwd=repo)
    head = sh("git rev-parse HEAD", cwd=repo, quiet=True).stdout.strip(); print("ProofScope HEAD", head); return head

def get_lean():
    arc = cache / f"lean-{LEAN_V}-linux.tar.zst"
    ok = lambda: arc.exists() and hashlib.sha256(arc.read_bytes()).hexdigest() == LEAN_SHA
    if not ok():
        sh(f"curl -fsSL --retry 4 -o {arc}.part https://github.com/leanprover/lean4/releases/download/v{LEAN_V}/lean-{LEAN_V}-linux.tar.zst && mv {arc}.part {arc}")
        if not ok(): arc.unlink(missing_ok=True); raise RuntimeError("Lean archive SHA-256 mismatch — refusing to use it (infrastructure error, not a result)")
    else: print("Lean archive from cache, SHA-256 verified")
    if not shutil.which("unzstd"): sh("apt-get -qq install -y zstd", quiet=True)
    lean_dir.mkdir(exist_ok=True); sh(f"tar --use-compress-program=unzstd -xf {arc} -C {lean_dir} --strip-components=1")
    os.environ["PATH"] = f"{lean_dir}/bin:" + os.environ["PATH"]
    v = sh("lean --version", quiet=True).stdout.strip(); assert f"version {LEAN_V}" in v, v; print(v)

def get_repl():
    exe = repl_dir / ".lake/build/bin/repl"
    if exe.exists() and sh("git rev-parse HEAD", cwd=repl_dir, quiet=True, check=False).stdout.strip() == REPL_SHA \
            and (repl_dir / "lean-toolchain").read_text().strip() == f"leanprover/lean4:v{LEAN_V}":
        print("REPL from cache (commit and toolchain verified)")
    else:
        shutil.rmtree(repl_dir, ignore_errors=True)
        sh(f"git clone -q https://github.com/leanprover-community/repl {repl_dir}"); sh(f"git checkout -q {REPL_SHA}", cwd=repl_dir)
        (repl_dir / "lean-toolchain").write_text(f"leanprover/lean4:v{LEAN_V}\n"); sh("lake build repl", cwd=repl_dir, quiet=True)
    out = sh(f'echo \'{{"cmd": "theorem t : 1 + 1 = 2 := rfl"}}\' | {exe}', quiet=True).stdout
    assert '"env"' in out and "error" not in out, out            # REPL actually elaborates
    os.environ["PROOFSCOPE_REPL"] = str(exe)

def get_mathlib():
    ml = cache / f"mathlib-{MATHLIB_SHA[:12]}"
    if not (ml / ".git").exists():
        shutil.rmtree(ml, ignore_errors=True); sh(f"git clone -q https://github.com/leanprover-community/mathlib4 {ml}")
    sh(f"git checkout -q {MATHLIB_SHA}", cwd=ml); sh("git diff --exit-code -- lake-manifest.json lean-toolchain", cwd=ml)
    lock = (ml / "lake-manifest.json").read_text()
    sh("lake exe cache get", cwd=ml, quiet=True)                   # never `lake update`
    assert (ml / "lake-manifest.json").read_text() == lock, "Mathlib lockfile changed"
    assert (ml / ".lake/build/lib/lean/Mathlib.olean").stat().st_size > 0
    os.environ["LEAN_PATH"] = sh("lake env printenv LEAN_PATH", cwd=ml, quiet=True).stdout.strip()
    os.environ["PROOFSCOPE_IMPORTS"] = "Mathlib"

def tests():
    mods = ["tests.sota9.test_audit", "tests.sota9.test_source_audit"]
    if EXPENSIVE: mods = ["tests.sota9.test_audit", "tests.sota9.test_source_audit", "tests.sota8.test_sota8", "tests.pilot25r.test_preamble", "tests.sota7.test_schema_integrity",
        "tests.sota7.test_scoring_adversarial", "tests.sota7.test_blinding_replay", "tests.sota6.test_repair", "tests.sota5.test_d03_regression",
        "tests.sota5.test_relations", "tests.sota5.test_lawrel", "tests.sota4.test_engine_hostile", "tests.sota4.test_integrity"]
    env = dict(os.environ); env.pop("PROOFSCOPE_IMPORTS", None); env.pop("LEAN_PATH", None)      # regressions are core-Lean
    p = sh(f"{sys.executable} -m unittest " + " ".join(mods), cwd=repo, env=env, check=False, quiet=True)
    tail = (p.stdout + p.stderr).strip().splitlines()[-3:]; print("\n".join(tail))
    skipped = "skipped" in tail[-1]
    if p.returncode or skipped: raise RuntimeError("tests failed" if p.returncode else "Lean tests were skipped — toolchain not visible")
    return tail[-3]

SOURCE_DEMO = """namespace Demo
variable {α : Type _} (xs : List α)
theorem len_app (ys : List α) : (xs ++ ys).length = xs.length + ys.length := by simp
theorem len_app_swap (ys : List α) : (ys ++ xs).length = xs.length + ys.length := by simp; omega
theorem div_self_any (n : Nat) : n / n = 1 := sorry
theorem div_self_pos (n : Nat) (h : n ≠ 0) : n / n = 1 := Nat.div_self (Nat.pos_of_ne_zero h)
end Demo
"""

def demos():
    sys.path.insert(0, str(repo)); os.chdir(repo)
    for m in [m for m in sys.modules if m == "proofscope" or m.startswith("proofscope.")]:
        del sys.modules[m]                                          # a rerun in the same runtime must load the fresh clone
    from proofscope.auditor import audit
    from proofscope.source_audit import source_audit
    cases = [("text", "∀ (n : Nat), n / n = 1", "∀ (n : Nat), n ≠ 0 → n / n = 1", {"PROVED_IMPLICATION", "DISPROVED_EQUIVALENCE"}),
             ("text", "∀ (n : Nat), succ n ≠ 0", "∀ (n : Nat), n + 1 ≠ 0", {"NOT_EVALUABLE"}),
             ("file", "len_app", "len_app_swap", {"PROVED_EQUIVALENT"}),
             ("file", "div_self_any", "div_self_pos", {"PROVED_IMPLICATION", "DISPROVED_EQUIVALENCE"})]
    for mode, r, c, want in cases:
        o = ROOT / "ps_demo" / hashlib.sha1((mode + r + c).encode()).hexdigest()[:8]
        rep = audit(r, c, [], o) if mode == "text" else source_audit(SOURCE_DEMO, r, c, o)
        print(f"  [{mode}] {rep['status']:<22} R: {r}   C: {c}   ({rep['resources']['wall_s'] if 'resources' in rep else '-'} s)")
        if rep["status"] not in want: raise RuntimeError(f"demo expected {want}, got {rep['status']}")

try:
    head = step("clone ProofScope", get_repo)
    step(f"Lean {LEAN_V} (SHA-256 pinned)", get_lean)
    step("Lean REPL (pinned commit, smoke-tested)", get_repl)
    if MATHLIB: step(f"Mathlib {MATHLIB_SHA[:12]} (precompiled cache)", get_mathlib)
    res = step("regression tests (core Lean)", tests)
    step("demo audits (" + ("Mathlib" if MATHLIB else "core Lean") + ")", demos)
    verdict = "PASS"
except Exception as e:
    verdict = f"FAIL — {e}"
print("\n" + "\n".join(f"  {n:<45} {s:<8} {t:>6} s" for n, s, t in STEPS))
print(f"\nVERDICT: {verdict}\nTotal: {time.time() - T0:.0f} s (fresh core runtime ≈ 4–5 min; Lean/REPL cached ≈ 3 min; MATHLIB adds ≈ 5–15 min)")
print("Mode:", "Mathlib" if MATHLIB else "core Lean", "· memory note: Mathlib imports map ~1.5 GB+ of .olean files; free Colab has ~12 GB RAM")
if verdict == "PASS":
    print("Meaning: Lean and the REPL are installed exactly as pinned. The SOTA-9 tests passed here: the report never "
          "upgrades an unknown, and theorems read straight from a Lean file are compared without re-typing anything "
          "(including a file that declares a fake axiom, which must not certify anything). The demos gave the expected "
          "honest answers: typed statements (one-way implication; 'not evaluable' without `open Nat`) and declarations "
          "read from a Lean file by name (equivalence with variables/universes kept exactly; one-way implication).")
else:
    print("Meaning: something failed; the step table above shows where. A failure is not a mathematical result.")

if verdict == "PASS" and LAUNCH_UI:
    from proofscope import ui
    from http.server import ThreadingHTTPServer
    try:
        srv = ThreadingHTTPServer(("127.0.0.1", 8765), ui.Handler); threading.Thread(target=srv.serve_forever, daemon=True).start()
    except OSError:
        print("UI port 8765 already in use (an earlier run's UI is still up; restart the runtime to load new UI code)")
    try:
        from google.colab import output; output.serve_kernel_port_as_window(8765, anchor_text="Open the ProofScope UI")
    except ImportError:
        print("UI on http://127.0.0.1:8765")
