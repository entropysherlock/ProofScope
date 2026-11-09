"""Run one tool invocation under a CPU budget for its whole process tree and account for its resources.

Accounting semantics (SOTA-2; protocol amendment A7):

* The budget limits the **complete process tree** of one tool invocation for one pair: the process the
  runner starts and every descendant (Lean, Lake, REPL servers, worker pools). It is not a per-process
  limit. (SOTA-1 used `prlimit --cpu`, which is per process: a tool with four busy children could use four
  budgets and still be reported OK; tests/bench/test_bench.py reproduces this.)
* The tree is every **descendant by ancestry** of the process the runner starts (parent links in /proc),
  tracked from the first poll on, so a descendant that leaves the session (`setsid`, as LeanInteract
  does for its Lean REPL: `start_new_session=True` in lean_interact/server.py) is still charged and killed.
  (SOTA-2 tracked the session only; the BEq+ REPL escaped it, its CPU arrived in one step when it was
  reaped, which is the 3.654 s overshoot of run 42694874449.) Orphans return to the runner because it is a
  child subreaper (`PR_SET_CHILD_SUBREAPER`); a previously tracked pid keeps being tracked after
  re-parenting, and is reaped and counted here.
* Enforcement: every 20 ms the runner sums `utime + stime + cutime + cstime` (from /proc/<pid>/stat) over
  the live tracked processes, plus the CPU of reaped orphans. A dead descendant's time reaches
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
    polls: int = 0
    mean_poll_ms: float = 0.0

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


def _proc_table() -> dict[int, tuple[int, int, int, float]]:
    """pid -> (ppid, session, starttime ticks, cpu seconds incl. reaped descendants) for all processes."""
    tab = {}
    for d in os.listdir("/proc"):
        if not d.isdigit():
            continue
        try:
            with open(f"/proc/{d}/stat") as f:
                st = f.read()
            f_ = st[st.rindex(")") + 2:].split()
            # after comm: 0 state, 1 ppid, 3 session, 11..14 utime stime cutime cstime, 19 starttime
            tab[int(d)] = (int(f_[1]), int(f_[3]), int(f_[19]),
                           (int(f_[11]) + int(f_[12]) + int(f_[13]) + int(f_[14])) / CLK)
        except (OSError, ValueError, IndexError):
            continue
    return tab


def _rss_mb(pid: int) -> float:
    try:
        with open(f"/proc/{pid}/status") as f:
            for line in f:
                if line.startswith("VmRSS:"):
                    return int(line.split()[1]) / 1024
    except OSError:
        pass
    return 0.0


class Tree:
    """Descendants of `root` by ancestry. A tracked process is identified by (pid, starttime) so pid reuse
    cannot attach an unrelated process."""

    def __init__(self, root: int):
        self.root = root
        self.members: dict[int, int] = {}     # pid -> starttime
        self.seen = 0

    def update(self) -> tuple[float, float, list[int]]:
        tab = _proc_table()
        if self.root in tab and self.root not in self.members:
            self.members[self.root] = tab[self.root][2]
        changed = True
        while changed:
            changed = False
            me = os.getpid()
            for pid, (ppid, _sid, start, _cpu) in tab.items():
                orphan = ppid == me and pid != self.root     # re-parented to the subreaper before we saw it
                if pid not in self.members and (orphan or (ppid in self.members and tab.get(ppid, (0, 0, -1))[2] == self.members[ppid])):
                    self.members[pid] = start
                    self.seen += 1
                    changed = True
        live = [p for p, st in self.members.items() if p in tab and tab[p][2] == st]
        # forget dead members (their CPU is in an ancestor's cutime or was reaped by the runner)
        self.members = {p: self.members[p] for p in live}
        cpu = sum(tab[p][3] for p in live)
        rss = sum(_rss_mb(p) for p in live)
        return cpu, rss, live

    def kill(self) -> None:
        for p in list(self.members):
            try:
                os.kill(p, signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                pass


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
    tree = Tree(p.pid)
    cause, peak_cpu, peak_rss, orphan_cpu = None, 0.0, 0.0, 0.0
    status_word, ru, polls, poll_cost = 0, None, 0, 0.0
    while True:
        pid, status_word, ru = os.wait4(p.pid, os.WNOHANG)
        if pid == p.pid:
            break
        t_poll = time.perf_counter()
        orphan_cpu += _reap_orphans(p.pid)
        cpu, rss, _live = tree.update()
        poll_cost += time.perf_counter() - t_poll
        polls += 1
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
                tree.kill()
                try:
                    os.killpg(p.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
        time.sleep(POLL_S)
    # the root is gone: account for and kill every remaining tracked descendant (nothing may outlive the pair)
    left_cpu, _, left = tree.update()
    if left:
        peak_cpu = max(peak_cpu, left_cpu + orphan_cpu + ru.ru_utime + ru.ru_stime)
        tree.kill()
        try:
            os.killpg(p.pid, signal.SIGKILL)
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
    tree_cpu = max(root_cpu + orphan_cpu, peak_cpu)
    dec = lambda b: b"".join(b).decode("utf-8", "replace")
    err_text = dec(bufs["err"])
    if cause:
        status = cause
    elif tree_cpu > cpu_s:
        status = "TIMEOUT_CPU"  # finished, but the tree used more than the budget between two polls
    elif sig:
        status = "TIMEOUT_CPU" if sig == "SIGXCPU" else "KILLED"
    elif rc == 0:
        status = "OK"
    elif any(m in err_text for m in ("MemoryError", "out of memory", "bad_alloc", "Cannot allocate")):
        status = "OOM"
    else:
        status = "ERROR"
    return Run(rc, sig, status, round(tree_cpu, 3), round(root_cpu, 3), round(peak_cpu, 3), cpu_s,
               round(max(0.0, tree_cpu - cpu_s), 3), round(wall, 3), round(max(ru.ru_maxrss / 1024, peak_rss), 1),
               tree.seen + 1, dec(bufs["out"]), err_text, polls, round(poll_cost / max(1, polls) * 1000, 3))
