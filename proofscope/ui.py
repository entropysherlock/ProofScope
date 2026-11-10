"""Minimal researcher UI for ProofScope audits (standard library only; local or Colab).

    python -m proofscope.ui --port 8765            # then open http://localhost:8765
    # Colab: from google.colab import output; output.serve_kernel_port_as_window(8765)

The page only renders the report produced by proofscope.auditor: it never computes or upgrades a verdict.
One audit runs at a time (Lean + Mathlib needs several GB).
"""
from __future__ import annotations

import argparse
import html
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .auditor import audit

LOCK = threading.Lock()
PAGE = """<!doctype html><html><head><meta charset="utf-8"><title>ProofScope</title><style>
body{font:15px/1.5 system-ui,sans-serif;max-width:980px;margin:24px auto;padding:0 16px;color:#1d1d1f}
textarea,input{width:100%;font:14px ui-monospace,monospace;box-sizing:border-box;padding:8px;border:1px solid #bbb;border-radius:6px}
textarea{height:70px}label{font-weight:600;display:block;margin-top:12px}button{margin-top:14px;padding:9px 18px;font-size:15px;border-radius:6px;border:0;background:#1d4ed8;color:#fff;cursor:pointer}
.st{display:inline-block;padding:4px 10px;border-radius:6px;font-weight:700;color:#fff}.PROVED_EQUIVALENT{background:#15803d}.PROVED_IMPLICATION{background:#0e7490}
.DISPROVED_EQUIVALENCE{background:#b91c1c}.UNKNOWN{background:#6b7280}.NOT_EVALUABLE{background:#a16207}.ERROR,.ENGINE_INCONSISTENT{background:#000}
pre{background:#f4f4f5;padding:10px;border-radius:6px;overflow:auto;font-size:12.5px}h3{margin-bottom:4px}.muted{color:#555;font-size:13px}
</style></head><body><h2>ProofScope — certified statement comparison</h2>
<p class="muted">Every “proved” line is a Lean declaration that passed a clean compile, an axiom audit and leanchecker replay. Unknown means no certificate was found; it is not evidence of a difference.</p>
<label>Reference statement R (Lean proposition)</label><textarea id="r">∀ (n : Nat), n / n = 1</textarea>
<label>Candidate statement C</label><textarea id="c">∀ (n : Nat), n ≠ 0 → n / n = 1</textarea>
<label>Source preamble (optional; only <code>open …</code>, <code>open scoped …</code>, <code>universe …</code> lines, verbatim from the source)</label><input id="p" placeholder="open Nat">
<button id="go" onclick="run()">Analyse</button> <span id="busy" class="muted"></span><div id="out"></div>
<script>
function esc(s){return String(s).replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]))}
async function run(){const b=document.getElementById('go');b.disabled=true;document.getElementById('busy').textContent='running (Lean)…';
const body={reference:r.value,candidate:c.value,preamble:p.value.split('\\n').map(x=>x.trim()).filter(x=>x)};
let rep;try{rep=await (await fetch('/audit',{method:'POST',body:JSON.stringify(body)})).json()}catch(e){rep={status:'ERROR',error:String(e)}}
b.disabled=false;document.getElementById('busy').textContent='';let h=`<h3>Status: <span class="st ${esc(rep.status)}">${esc(rep.status)}</span></h3>`;
if(rep.error)h+=`<pre>${esc(rep.error)}</pre>`;
if(rep.proved&&rep.proved.length)h+='<h3>Proved</h3><ul>'+rep.proved.map(x=>`<li>${esc(x.meaning)} — <code>${esc(x.declaration)}</code> <span class="muted">axioms: ${esc(JSON.stringify(x.axioms))}</span></li>`).join('')+'</ul>';
if(rep.counterexample)h+=`<p><b>Counterexample:</b> ${esc(JSON.stringify(rep.counterexample))}</p>`;
if(rep.unknown&&rep.unknown.length)h+='<h3>Unknown</h3><ul>'+rep.unknown.map(x=>`<li>${esc(x)}</li>`).join('')+'</ul>';
if(rep.not_established&&rep.not_established.length)h+='<h3>Not established</h3><ul>'+rep.not_established.map(x=>`<li>${esc(x)}</li>`).join('')+'</ul>';
if(rep.hints&&rep.hints.length)h+='<h3>Hints (not applied)</h3><ul>'+rep.hints.map(x=>`<li><code>${esc(x.unknown)}</code>: ${esc(x.suggestion)}</li>`).join('')+'</ul>';
if(rep.diagnostics&&rep.diagnostics.length)h+='<h3>Lean diagnostics</h3>'+rep.diagnostics.map(x=>`<pre>${esc(x)}</pre>`).join('');
if(rep.resources)h+=`<p class="muted">${esc(rep.resources.wall_s)} s wall · ${esc(rep.resources.child_cpu_s)} s CPU · engine ${esc(rep.environment.engine)} @ ${esc((rep.environment.engine_commit||'').slice(0,12))}</p>`;
if(rep.certificate_source)h+=`<details><summary>Certificate (Lean)</summary><pre>${esc(rep.certificate_source)}</pre></details>`;
const blob=new Blob([JSON.stringify(rep,null,1)],{type:'application/json'});h+=`<p><a download="proofscope_report.json" href="${URL.createObjectURL(blob)}">Export report (JSON)</a></p>`;
document.getElementById('out').innerHTML=h}
</script></body></html>"""


class Handler(BaseHTTPRequestHandler):
    out_dir = Path("proofscope_ui_runs")

    def _send(self, code, body, ctype):
        b = body.encode()
        self.send_response(code); self.send_header("Content-Type", ctype); self.send_header("Content-Length", str(len(b)))
        self.end_headers(); self.wfile.write(b)

    def do_GET(self):
        self._send(200, PAGE, "text/html; charset=utf-8")

    def do_POST(self):
        if self.path != "/audit":
            return self._send(404, "{}", "application/json")
        try:
            req = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
            if not LOCK.acquire(blocking=False):
                return self._send(429, json.dumps({"status": "ERROR", "error": "another audit is running"}), "application/json")
            try:
                rep = audit(req["reference"], req["candidate"], req.get("preamble") or [], self.out_dir / "last")
            finally:
                LOCK.release()
            rep.pop("engine_row", None)
            self._send(200, json.dumps(rep, ensure_ascii=False, default=str), "application/json")
        except Exception as e:                       # never a verdict: an error is shown as ERROR
            self._send(200, json.dumps({"status": "ERROR", "error": html.escape(str(e))[:2000]}), "application/json")

    def log_message(self, *a):
        pass


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m proofscope.ui")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--host", default="127.0.0.1")
    a = ap.parse_args(argv)
    srv = ThreadingHTTPServer((a.host, a.port), Handler)
    print(f"ProofScope UI on http://{a.host}:{a.port}", flush=True)
    srv.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
