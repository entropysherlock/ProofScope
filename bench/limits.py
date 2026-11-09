"""Run one tool invocation under a CPU budget for its whole process tree and account for its resources.

Accounting semantics (SOTA-2; protocol amendment A7):

* The budget limits the **complete process tree** of one tool invocation for one pair: the process the
  runner starts and every descendant (Lean, Lake, REPL servers, worker pools). It is not a per-process
  limit. (SOTA-1 used `prlimit --cpu`, which is per process: a tool with four busy children could use four
  budgets and still be reported OK; tests/bench/test_bench.py reproduces this.)
* The tree is the new session the runner creates (`start_new_session=True`), plus orphans, which return
  to the runner because it is a child subreaper (`PR_SET_CHILD_SUBREAPER`) and are reaped and counted here.
* Enforcement: every 20 ms the runner sums `utime + stime + cutime + cstime` (from /proc/<pid>/stat) over
  the live processes of the session, plus the CPU of reaped orphans. A dead descendant's time reaches
  exactly one live ancestor's cutime/cstime when its parent reaps it, so the sum counts each process once.
  When the sum exceeds the limit, the whole session is killed and the status is TIMEOUT_CPU.
  Enforcement is calibrated, not exact: overshoot is bounded by the polling interval times the number of
  busy cores, and the observed overshoot is recorded on every record (`cpu_overshoot_s`).
* Final accounting: `cpu_tree_s = max(wait4 rusage of the root, which includes every descendant that was
  waited for, + reaped orphans, peak polled tree sum)`. Peak memory is the peak polled sum of VmRSS over
  the tree (and never less than the root's ru_maxrss).
* A per-process RLIMIT_CPU of limit + 5 s remains as a backstop only.

Statuses: OK, TIMEOUT_CPU (tree budget exhausted), TIMEOUT_WALL (wall cap; never reported as a CPU limit),
OOM (tree RSS cap or allocation failure), KILLED (signal not caused by the runner), ERROR (non-zero exit),
LAUNCH_ERROR (the executable, working directory or an input path does not exist; checked before launch).
"""
from __future__ import annotations

import ctypes
import os
import shutil
import signal
import subprocess
import threading
import time
from dataclasses import asdict, dataclass

CLK = os.sysconf("SC_CLK_TCK")
POLL_S = 0.02


@dataclass
class Run:
    exit_code: int | None
    signal: str | None
    status: str
    cpu_tree_s: float
    cpu_root_wait4_s: float
    cpu_peak_polled_s: float
    cpu_limit_s: float
    cpu_overshoot_s: float
    wall_s: float
    max_rss_mb: float
    processes_seen: int
    stdout: str
    stderr: str

    def as_dict(self) -> dict:
        d = asdict(self)
        d["cpu_s"] = self.cpu_tree_s
        return d


def _set_subreaper() -> bool:
    try:
        libc = ctypes.CDLL("libc.so.6", use_errno=True)
        return libc.prctl(36, 1, 0, 0, 0) == 0  # PR_SET_CHILD_SUBREAPER
    except OSError:
        return False


SUBREAPER = _set_subreaper()


def _session_stats(sid: int) -> tuple[float, float, set[int]]:
    """(CPU seconds incl. reaped descendants, RSS MB, pids) over the live processes of session `sid`."""
    cpu_ticks, rss_kb, pids = 0, 0, set()
    for d in os.listdir("/proc"):
        if not d.isdigit():
            continue
        try:
            with open(f"/proc/{d}/stat") as f:
                st = f.read()
            fields = st[st.rindex(")") + 2:].split()
            # after the comm field: index 0 = state (field 3), 3 = session (field 6),
            # 11..14 = utime, stime, cutime, cstime (fields 14..17)
            if int(fields[3]) != sid:
                continue
            cpu_ticks += int(fields[11]) + int(fields[12]) + int(fields[13]) + int(fields[14])
            pids.add(int(d))
            with open(f"/proc/{d}/status") as f:
                for line in f:
                    if line.startswith("VmRSS:"):
                        rss_kb += int(line.split()[1])
                        break
        except (OSError, ValueError, IndexError):
            continue
    return cpu_ticks / CLK, rss_kb / 1024, pids


def _reap_orphans(root: int) -> float:
    """Reap children of the runner other than `root` (orphans re-parented to the subreaper); CPU seconds."""
    total = 0.0
    for pid in [int(d) for d in os.listdir("/proc") if d.isdigit()]:
        if pid == root:
            continue
        try:
            with open(f"/proc/{pid}/stat") as f:
                st = f.read()
            ppid = int(st[st.rindex(")") + 2:].split()[1])
        except (OSError, ValueError, IndexError):
            continue
        if ppid != os.getpid():
            continue
        try:
            rpid, _, ru = os.wait4(pid, os.WNOHANG)
        except ChildProcessError:
            continue
        if rpid == pid:
            total += ru.ru_utime + ru.ru_stime
    return total


def check_launch(cmd: list[str], cwd: str | None, inputs: list[str]) -> str | None:
    """Fail before launch on a missing executable, working directory or input file."""
    if cwd is not None and not os.path.isdir(cwd):
        return f"working directory does not exist: {cwd}"
    exe = cmd[0]
    if os.sep in exe:
        if not os.path.exists(exe):
            return f"executable does not exist: {exe}"
    elif shutil.which(exe) is None:
        return f"executable not found on PATH: {exe}"
    for p in inputs:
        if not os.path.isabs(p):
            return f"input path is not absolute: {p}"
        if not os.path.exists(p):
            return f"input file does not exist: {p}"
    return None


def run_limited(cmd: list[str], cpu_s: float, mem_mb: int, wall_s: float, cwd: str | None = None,
                env: dict | None = None, inputs: tuple[str, ...] = ()) -> Run:
    err = check_launch(cmd, cwd, list(inputs))
    if err:
        return Run(None, None, "LAUNCH_ERROR", 0.0, 0.0, 0.0, cpu_s, 0.0, 0.0, 0.0, 0, "", err)
    backstop = int(cpu_s) + 5
    full = ["prlimit", f"--cpu={backstop}:{backstop + 1}", "--"] + cmd
    t0 = time.monotonic()
    p = subprocess.Popen(full, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         start_new_session=True)
    bufs = {"out": [], "err": []}

    def pump(stream, key):
        for chunk in iter(lambda: stream.read(65536), b""):
            bufs[key].append(chunk)

    ts = [threading.Thread(target=pump, args=(p.stdout, "out"), daemon=True),
          threading.Thread(target=pump, args=(p.stderr, "err"), daemon=True)]
    for t in ts:
        t.start()
    sid = p.pid
    cause, peak_cpu, peak_rss, seen, orphan_cpu = None, 0.0, 0.0, set(), 0.0
    status_word, ru = 0, None
    while True:
        pid, status_word, ru = os.wait4(p.pid, os.WNOHANG)
        if pid == p.pid:
            break
        orphan_cpu += _reap_orphans(p.pid)
        cpu, rss, pids = _session_stats(sid)
        seen |= pids
        peak_cpu = max(peak_cpu, cpu + orphan_cpu)
        peak_rss = max(peak_rss, rss)
        if cause is None:
            if cpu + orphan_cpu > cpu_s:
                cause = "TIMEOUT_CPU"
            elif rss > mem_mb:
                cause = "OOM"
            elif time.monotonic() - t0 > wall_s:
                cause = "TIMEOUT_WALL"
            if cause:
                try:
                    os.killpg(sid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
        time.sleep(POLL_S)
    # the root is gone: kill whatever is left of its session (no descendant may outlive the pair) and count it
    left_cpu, _, left = _session_stats(sid)
    if left:
        peak_cpu = max(peak_cpu, left_cpu + orphan_cpu + ru.ru_utime + ru.ru_stime)
        try:
            os.killpg(sid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        time.sleep(0.2)
    orphan_cpu += _reap_orphans(p.pid)
    for t in ts:
        t.join(timeout=5)
    for stream in (p.stdout, p.stderr):
        stream.close()
    p.returncode = os.waitstatus_to_exitcode(status_word)
    wall = time.monotonic() - t0
    rc = p.returncode
    sig = signal.Signals(-rc).name if rc is not None and rc < 0 else None
    root_cpu = ru.ru_utime + ru.ru_stime
    tree = max(root_cpu + orphan_cpu, peak_cpu)
    dec = lambda b: b"".join(b).decode("utf-8", "replace")
    err_text = dec(bufs["err"])
    if cause:
        status = cause
    elif tree > cpu_s:
        status = "TIMEOUT_CPU"  # finished, but the tree used more than the budget between two polls
    elif sig:
        status = "TIMEOUT_CPU" if sig == "SIGXCPU" else "KILLED"
    elif rc == 0:
        status = "OK"
    elif any(m in err_text for m in ("MemoryError", "out of memory", "bad_alloc", "Cannot allocate")):
        status = "OOM"
    else:
        status = "ERROR"
    return Run(rc, sig, status, round(tree, 3), round(root_cpu, 3), round(peak_cpu, 3), cpu_s,
               round(max(0.0, tree - cpu_s), 3), round(wall, 3), round(max(ru.ru_maxrss / 1024, peak_rss), 1),
               len(seen), dec(bufs["out"]), err_text)
