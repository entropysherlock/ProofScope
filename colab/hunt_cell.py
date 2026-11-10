# ProofScope DEFECT HUNT — single Colab cell (Python 3, CPU runtime).
# Looks for formal-math benchmark statements that are provably FALSE or VACUOUS (contradictory hypotheses),
# each backed by a Lean certificate that Lean's own checker replays.
# First run in a fresh runtime: ~12–18 min (one-time Mathlib download). Every later run in the same runtime: ~5 min.
# Each run continues where the previous one stopped.
BENCH = "putnam"        # "putnam" (PutnamBench, 672 problems; not in the 2026 prior audit) or "formalmath" (5,560)
RUN_MINUTES = 5.0       # target length of a run once Mathlib is installed
SAVE_TO_DRIVE = False   # True: also copy findings to Google Drive (MyDrive/proofscope_hunt)

import hashlib, json, os, shutil, subprocess, sys, time
from pathlib import Path
os.chdir("/content")
T0 = time.time()
ROOT, BRANCH = Path("/content"), "research/sota9-usable-auditor"
LEAN_V, LEAN_SHA = "4.34.1", "47bf4bbd78f70c2e9670598ab7124d92b6efb7330ff33e5fbb4030f6fd72e4e4"
REPL_SHA, MATHLIB_SHA = "193cf4bb9a22bb3fc6d25774f0fe6a70db1fd6ee", "d13f23b723b8a846827a245b89c10fc7d3f11612"
cache, repo = ROOT / "ps_cache", ROOT / "ProofScope"
lean_dir, repl_dir, ml = ROOT / f"lean-{LEAN_V}", cache / f"repl-{REPL_SHA[:12]}-lean{LEAN_V}", cache / "mathlib4"
cache.mkdir(exist_ok=True)
STEPS = []

def sh(cmd, cwd=None, check=True, quiet=True, timeout=None):
    p = subprocess.run(cmd, shell=True, cwd=cwd, text=True, capture_output=True, timeout=timeout)
    if (not quiet) or p.returncode: print((p.stdout + p.stderr)[-2500:])
    if check and p.returncode: raise RuntimeError(f"step failed ({p.returncode}): {cmd[:120]}")
    return p

def step(name, fn):
    t = time.time(); print(f"▶ {name}", flush=True)
    try:
        r = fn(); STEPS.append((name, "ok", round(time.time() - t))); return r
    except Exception as e:
        STEPS.append((name, f"FAIL: {e}", round(time.time() - t))); raise

def get_repo():
    if repo.exists(): shutil.rmtree(repo)
    sh(f"git clone -q --branch {BRANCH} https://github.com/entropysherlock/ProofScope {repo}")
    return sh("git rev-parse --short HEAD", cwd=repo).stdout.strip()

def get_lean():
    os.environ["PATH"] = f"{lean_dir}/bin:" + os.environ["PATH"]
    if (lean_dir / "bin/lean").exists() and f"version {LEAN_V}" in sh("lean --version", check=False).stdout:
        return print("  Lean already installed")
    arc = cache / f"lean-{LEAN_V}.tar.zst"
    ok = lambda: arc.exists() and hashlib.sha256(arc.read_bytes()).hexdigest() == LEAN_SHA
    if not ok():
        sh(f"curl -fsSL --retry 4 -o {arc} https://github.com/leanprover/lean4/releases/download/v{LEAN_V}/lean-{LEAN_V}-linux.tar.zst")
        if not ok(): raise RuntimeError("Lean archive SHA-256 mismatch (infrastructure problem, not a result)")
    if not shutil.which("unzstd"): sh("apt-get -qq install -y zstd")
    lean_dir.mkdir(exist_ok=True); sh(f"tar --use-compress-program=unzstd -xf {arc} -C {lean_dir} --strip-components=1")
    assert f"version {LEAN_V}" in sh("lean --version").stdout

def get_repl():
    exe = repl_dir / ".lake/build/bin/repl"
    if not (exe.exists() and sh("git rev-parse HEAD", cwd=repl_dir, check=False).stdout.strip() == REPL_SHA):
        shutil.rmtree(repl_dir, ignore_errors=True)
        sh(f"git clone -q https://github.com/leanprover-community/repl {repl_dir}"); sh(f"git checkout -q {REPL_SHA}", cwd=repl_dir)
        (repl_dir / "lean-toolchain").write_text(f"leanprover/lean4:v{LEAN_V}\n"); sh("lake build repl", cwd=repl_dir)
    os.environ["PROOFSCOPE_REPL"] = str(exe)

def get_mathlib():
    olean = ml / ".lake/build/lib/lean/Mathlib.olean"
    if not olean.exists():
        print("  first time in this runtime: downloading Mathlib's precompiled files (about 5–12 min)…", flush=True)
        if not (ml / ".git").exists():
            ml.mkdir(parents=True, exist_ok=True)
            sh("git init -q && git remote add origin https://github.com/leanprover-community/mathlib4", cwd=ml)
        sh(f"git fetch -q --depth 1 origin {MATHLIB_SHA} && git checkout -q FETCH_HEAD", cwd=ml)
        tc = (ml / "lean-toolchain").read_text().strip()
        if not tc.endswith(LEAN_V): print(f"  note: Mathlib pins {tc}; running with Lean {LEAN_V}")
        lock = (ml / "lake-manifest.json").read_text()
        sh("lake exe cache get", cwd=ml, timeout=2400)                 # never `lake update`
        assert (ml / "lake-manifest.json").read_text() == lock, "Mathlib lockfile changed"
    assert olean.exists() and olean.stat().st_size > 0, "Mathlib.olean missing after cache get"
    os.environ["LEAN_PATH"] = sh("lake env printenv LEAN_PATH", cwd=ml).stdout.strip()

def get_data():
    sys.path.insert(0, str(repo))
    for m in [m for m in sys.modules if m == "proofscope" or m.startswith("proofscope.")]: del sys.modules[m]
    from proofscope.hunt_data import putnam_rows, formalmath_rows, write_jsonl
    data = cache / f"{BENCH}.jsonl"
    if not data.exists():
        if BENCH == "putnam":
            pb = cache / "PutnamBench"
            if not pb.exists(): sh(f"git clone -q --depth 1 https://github.com/trishullab/PutnamBench {pb}")
            rows = putnam_rows(pb)
        else:
            try: import datasets  # noqa
            except ImportError: sh(f"{sys.executable} -m pip -q install datasets")
            rows = formalmath_rows()
        write_jsonl(rows, data)
    return sum(1 for _ in data.open())

def hunt(minutes):
    out = ROOT / "ps_hunt" / BENCH
    cmd = (f"{sys.executable} -m proofscope.defect_hunt --data {cache / (BENCH + '.jsonl')} --out {out} "
           f"--minutes {minutes:.2f} --workers 2")
    p = subprocess.run(cmd, shell=True, cwd=repo, text=True, capture_output=True, env=dict(os.environ))
    if p.returncode: print((p.stdout + p.stderr)[-3000:]); raise RuntimeError("hunt process failed")
    return json.loads((out / "last_run_summary.json").read_text()), out

verdict, summary, out, total = None, None, None, None
try:
    head = step("ProofScope (latest branch)", get_repo)
    step(f"Lean {LEAN_V}", get_lean)
    step("Lean REPL", get_repl)
    step("Mathlib (pinned)", get_mathlib)
    total = step(f"benchmark data: {BENCH}", get_data)
    first_run = time.time() - T0 > 240
    minutes = 3.5 if first_run else max(2.0, RUN_MINUTES - (time.time() - T0) / 60 - 0.25)
    summary, out = step(f"scan + certify ({minutes:.1f} min)", lambda: hunt(minutes))
    verdict = "RAN"
except Exception as e:
    verdict = f"FAIL — {e}"

print("\n" + "\n".join(f"  {n:<40} {s:<8} {t:>5} s" for n, s, t in STEPS))
print("\n================ VERDICT ================")
if verdict != "RAN":
    print(f"The run did not finish: {verdict}\nThis is a setup/infrastructure problem, not a result about any benchmark. Paste this output to Claude.")
else:
    done = len((out / "done_ids.txt").read_text().split()) if (out / "done_ids.txt").exists() else 0
    allf = [json.loads(l) for l in (out / "findings.jsonl").read_text().splitlines()] if (out / "findings.jsonl").exists() else []
    c = summary["status_counts"]
    print(f"Benchmark: {BENCH} · this run checked {summary['scanned_this_run']} statements · progress {done}/{total} · run time {time.time() - T0:.0f} s")
    print(f"  compiled and searched, nothing found ........ {c.get('NO_DEFECT_FOUND', 0)}  (not proof they are correct — only that this search found no defect)")
    print(f"  did not compile with our Mathlib version .... {c.get('COMPILE_FAIL', 0) + c.get('COMPILE_TIMEOUT', 0)}  (version drift — not counted as defects)")
    print(f"  skipped (unfilled answer / other) ........... {sum(v for k, v in c.items() if k.startswith('SKIP') or k == 'PROBE_FAIL')}")
    print(f"  defect candidates → certified this run ...... {summary['candidates']} → {len(summary['verified_findings'])}")
    print()
    if summary["verified_findings"]:
        print("NEW CERTIFIED FINDINGS (Lean proved them; axioms clean; leanchecker replayed):")
        for f in summary["verified_findings"]:
            what = ("the formal statement is FALSE — Lean proved its negation" if f["kind"] == "FALSE"
                    else "the hypotheses CONTRADICT each other — the 'theorem' is true for a trivial reason")
            print(f"\n• {f['id']}: {what}.\n  how: {f['proof'][:220]}\n  {f['novelty']}")
            if f.get("autobound"): print("  ⚠ it only compiles because an undefined name was silently turned into a variable")
            if f.get("informal"): print(f"  informal problem: {f['informal'][:300]}")
        print("\nMeaning: each finding is a machine-checked defect in the benchmark as written. Before reporting one, Claude will")
        print("compare it with the informal problem and check whether it is already known.")
    else:
        print("Meaning: no certified defects in this batch. That is the normal outcome for a well-curated benchmark;")
        print("run this cell again to continue the scan where it stopped.")
    print(f"\nAll findings so far for {BENCH}: {len(allf)}  (saved in {out}/findings.jsonl)")
    if SAVE_TO_DRIVE:
        from google.colab import drive; drive.mount("/content/drive")
        d = Path("/content/drive/MyDrive/proofscope_hunt"); d.mkdir(parents=True, exist_ok=True)
        for f in ("findings.jsonl", "results.jsonl"):
            if (out / f).exists(): shutil.copy(out / f, d / f"{BENCH}_{f}")
        print(f"Copied to Google Drive: {d}")
