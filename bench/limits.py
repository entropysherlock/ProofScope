"""Run one process under a hard CPU-time and address-space limit and account for its resources.

The limit is applied from outside (`prlimit`), so it binds every tool the same way whether or not the
tool has its own budget flag. A process killed by SIGXCPU/SIGKILL at the limit is a TIMEOUT, never an
abstention. CPU time and peak RSS come from `wait4` for that child (its own rusage, including its
descendants that it waited for), not from the parent's cumulative counters.
"""
from __future__ import annotations

import os
import shutil
import signal
import subprocess
import threading
import time
from dataclasses import asdict, dataclass


@dataclass
class Run:
    exit_code: int | None
    signal: str | None
    status: str            # OK | TIMEOUT_CPU | TIMEOUT_WALL | OOM_OR_KILLED | ERROR
    cpu_user_s: float
    cpu_sys_s: float
    wall_s: float
    max_rss_mb: float
    stdout: str
    stderr: str

    def as_dict(self) -> dict:
        d = asdict(self)
        d["cpu_s"] = round(self.cpu_user_s + self.cpu_sys_s, 3)
        return d


def run_limited(cmd: list[str], cpu_s: float, mem_mb: int, wall_s: float, cwd: str | None = None,
                env: dict | None = None) -> Run:
    if shutil.which("prlimit") is None:
        raise RuntimeError("prlimit not found: the CPU limit cannot be enforced (INFRASTRUCTURE)")
    soft = max(1, int(round(cpu_s)))
    # CPU: hard kernel limit. Memory: a resident-set watchdog over the whole process group (an
    # address-space rlimit is unusable for Lean, which reserves large virtual ranges for its threads).
    full = ["prlimit", f"--cpu={soft}:{soft + 1}", "--"] + cmd
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
    wall_hit, mem_hit, status_word, ru, peak_group_mb = False, False, 0, None, 0.0
    while True:
        pid, status_word, ru = os.wait4(p.pid, os.WNOHANG)
        if pid == p.pid:
            break
        g = _group_rss_mb(p.pid)
        peak_group_mb = max(peak_group_mb, g)
        if g > mem_mb:
            mem_hit = True
            os.killpg(p.pid, signal.SIGKILL)
            pid, status_word, ru = os.wait4(p.pid, 0)
            break
        if time.monotonic() - t0 > wall_s:
            wall_hit = True
            os.killpg(p.pid, signal.SIGKILL)
            pid, status_word, ru = os.wait4(p.pid, 0)
            break
        time.sleep(0.05)
    for t in ts:
        t.join(timeout=5)
    p.returncode = os.waitstatus_to_exitcode(status_word)
    wall = time.monotonic() - t0
    rc = p.returncode
    sig = signal.Signals(-rc).name if rc is not None and rc < 0 else None
    cpu = ru.ru_utime + ru.ru_stime
    if mem_hit:
        status = "OOM"
    elif wall_hit:
        status = "TIMEOUT_WALL"
    elif sig == "SIGXCPU" or (sig == "SIGKILL" and cpu >= soft - 0.5):
        status = "TIMEOUT_CPU"
    elif sig in ("SIGKILL", "SIGSEGV", "SIGABRT"):
        status = "OOM_OR_KILLED"
    elif rc == 0:
        status = "OK"
    else:
        status = "ERROR"
    dec = lambda b: b"".join(b).decode("utf-8", "replace")
    if status == "ERROR" and any(m in dec(bufs["err"]) for m in ("MemoryError", "out of memory", "bad_alloc", "Cannot allocate")):
        status = "OOM"
    return Run(rc, sig, status, round(ru.ru_utime, 3), round(ru.ru_stime, 3), round(wall, 3),
               round(max(ru.ru_maxrss / 1024, peak_group_mb), 1), dec(bufs["out"]), dec(bufs["err"]))


def _group_rss_mb(pgid: int) -> float:
    """Sum of VmRSS over all processes in the session/process group `pgid` (Linux /proc)."""
    total = 0
    for d in os.listdir("/proc"):
        if not d.isdigit():
            continue
        try:
            if os.getpgid(int(d)) != pgid:
                continue
            with open(f"/proc/{d}/status") as f:
                for line in f:
                    if line.startswith("VmRSS:"):
                        total += int(line.split()[1])
                        break
        except (OSError, ProcessLookupError):
            continue
    return total / 1024
