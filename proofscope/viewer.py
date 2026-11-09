"""Self-contained HTML viewer for ProofScope dossiers and comparison results (v1.0 slice).

    python3 -m proofscope.viewer --dossiers DIR/dossiers [--bench bench_results.json] --out report.html

One offline HTML file: no external scripts, fonts or network requests. It shows exactly what is in the JSON and
repeats its limits; it adds no claims of its own.
"""

from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path

CSS = """
:root{--bg:#fbfbf9;--fg:#1d1d1b;--mute:#6b6b66;--line:#e2e1dc;--ok:#1f7a4d;--warn:#a86a00;--bad:#b3261e;--info:#3d5a99}
@media (prefers-color-scheme:dark){:root{--bg:#161615;--fg:#ecebe6;--mute:#9b9a94;--line:#2e2d2a;--ok:#5cc28f;--warn:#e0a84a;--bad:#ef7b72;--info:#8ea8e6}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 ui-sans-serif,system-ui,-apple-system,Segoe UI,sans-serif}
header{padding:28px 32px 12px;border-bottom:1px solid var(--line)}h1{margin:0;font-size:22px;font-weight:650}
.sub{color:var(--mute);font-size:13px}main{display:grid;grid-template-columns:300px 1fr;min-height:80vh}
nav{border-right:1px solid var(--line);padding:16px;overflow:auto;max-height:85vh}nav input{width:100%;padding:8px 10px;border:1px solid var(--line);border-radius:6px;background:transparent;color:inherit;margin-bottom:10px}
nav a{display:block;padding:5px 8px;border-radius:5px;color:inherit;text-decoration:none;font-family:ui-monospace,Menlo,monospace;font-size:12.5px;word-break:break-all}
nav a:hover,nav a.on{background:var(--line)}section{padding:20px 32px;max-width:980px}
.tag{display:inline-block;font-size:11.5px;font-weight:600;padding:2px 8px;border-radius:99px;border:1px solid currentColor;margin-right:6px}
.ok{color:var(--ok)}.warn{color:var(--warn)}.bad{color:var(--bad)}.info{color:var(--info)}
pre{background:transparent;border:1px solid var(--line);border-radius:8px;padding:12px 14px;overflow:auto;font-size:13px;white-space:pre-wrap}
table{border-collapse:collapse;width:100%;font-size:13.5px;margin:6px 0 16px}th,td{text-align:left;padding:6px 8px;border-bottom:1px solid var(--line);vertical-align:top}
th{color:var(--mute);font-weight:600}code{font-family:ui-monospace,Menlo,monospace;font-size:12.5px}h2{font-size:17px;margin:22px 0 8px}h3{font-size:14.5px;margin:18px 0 6px;color:var(--mute)}
.note{color:var(--mute);font-size:13px;border-left:3px solid var(--line);padding-left:10px}
.stats{display:flex;gap:28px;flex-wrap:wrap;margin:10px 0 4px}.stat b{display:block;font-size:22px;font-variant-numeric:tabular-nums}
"""

JS = """
const data=JSON.parse(document.getElementById('d').textContent);
const nav=document.getElementById('list'),view=document.getElementById('view'),q=document.getElementById('q');
const esc=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const cls=s=>({REPLAYED:'ok',NONE:'ok',STANDARD:'ok',TOOLCHAIN_LIBRARY:'info',NOT_RUN:'warn',NONSTANDARD:'warn',REPLAY_FAILED:'bad',SORRY:'bad'}[s]||'info');
function show(i){const d=data[i];[...nav.children].forEach((a,j)=>a.classList.toggle('on',j==i));
 const defs=d.statement_dependencies.filter(x=>x.role==='definition');
 view.innerHTML=`<h2><code>${esc(d.theorem_id)}</code></h2>
 <span class="tag ${cls(d.kernel_status)}">kernel: ${esc(d.kernel_status)}</span><span class="tag ${cls(d.axiom_status)}">axioms: ${esc(d.axiom_status)}</span><span class="tag info">${esc(d.kind)}</span>
 <p class="sub">Module <code>${esc(d.module)}</code>${d.source_locations?` · lines ${d.source_locations.start_line}–${d.source_locations.end_line}`:''} · commit <code>${esc(d.source_commit||'—')}</code></p>
 <h3>Elaborated statement</h3><pre>${esc(d.elaborated_type)}</pre><p class="sub">Conclusion shape: <code>${esc(d.conclusion_shape)}</code></p>
 <h3>Binders</h3><table><tr><th>Name</th><th>Binder</th><th>Role</th><th>Type</th></tr>${d.binders.map(b=>`<tr><td><code>${esc(b.name)}</code></td><td>${esc(b.binder)}</td><td>${esc(b.role)}</td><td><code>${esc(b.type)}</code></td></tr>`).join('')}</table>
 <h3>Definitions the statement depends on</h3>${defs.length?'<ul>'+defs.map(x=>`<li><code>${esc(x.name)}</code> <span class="sub">${esc(x.module)}</span></li>`).join('')+'</ul>':'<p class="sub">None beyond logic, types and notation.</p>'}
 <h3>Axioms</h3><p>${d.axioms.length?d.axioms.map(a=>`<code>${esc(a)}</code>`).join(', '):'none'}</p>
 <h3>Unresolved</h3><ul>${d.unresolved_items.map(u=>`<li>${esc(u)}</li>`).join('')}</ul>
 <p class="note">This dossier describes what Lean elaborated and which axioms it uses. It does not say the statement matches any paper.</p>`;}
function render(){const t=q.value.toLowerCase();nav.innerHTML='';data.forEach((d,i)=>{if(t&&!d.theorem_id.toLowerCase().includes(t))return;const a=document.createElement('a');a.href='#';a.textContent=d.theorem_id;a.onclick=e=>{e.preventDefault();show(i)};a.className=cls(d.axiom_status)==='bad'?'bad':'';nav.appendChild(a)});}
q.oninput=render;render();if(data.length)show(0);
"""


def build(dossier_dir: Path, bench: Path | None, out: Path, title: str) -> Path:
    ds = [json.loads(p.read_text()) for p in sorted(dossier_dir.glob("*.json"))]
    stat = lambda k, v: sum(1 for d in ds if d.get(k) == v)  # noqa: E731
    bench_html = ""
    if bench and bench.exists():
        rep = json.loads(bench.read_text())["report"]
        rows = []
        for sp, r in rep.get("splits", {}).items():
            e, b = r["engine_detection"], r["baseline_detection"]
            rows.append(f"<tr><td>{sp}</td><td>{r['cases']}</td><td>{r['exact_label_accuracy']}</td><td>{e['precision']}</td>"
                        f"<td>{e['recall']} {e.get('recall_ci95')}</td><td>{e['false_positive_rate']}</td><td>{e['coverage']}</td>"
                        f"<td>{b['precision']} / {b['false_positive_rate']}</td></tr>")
        adv = rep.get("adversarial_certificates")
        bench_html = ("<h2>Theorem-comparison benchmark</h2><table><tr><th>Split</th><th>Cases</th><th>Exact</th><th>Precision</th>"
                      "<th>Recall (95% CI)</th><th>FPR</th><th>Coverage</th><th>Baseline precision / FPR</th></tr>" + "".join(rows) + "</table>"
                      + (f"<p>Adversarial certificates: {adv['correct']}/{adv['cases']} handled correctly; "
                         f"false acceptances: {len(adv['false_acceptances'])}.</p>" if adv else "")
                      + f"<p class='note'>{html.escape(rep.get('competitors', ''))} Cases were written by the project; "
                        "held-out cases were written after the engine was frozen but by the same author.</p>")
    doc = f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title><style>{CSS}</style></head><body>
<header><h1>{html.escape(title)}</h1><div class="sub">ProofScope by Caleb J. Westfall · Verify the proof. Validate the claim.</div>
<div class="stats"><div class="stat"><b>{len(ds)}</b>dossiers</div><div class="stat"><b>{stat('kernel_status','REPLAYED')}</b>kernel-replayed</div>
<div class="stat"><b>{stat('axiom_status','SORRY')}</b>depend on sorry</div><div class="stat"><b>{stat('axiom_status','NONSTANDARD')}</b>non-standard axioms</div></div>
{bench_html}</header>
<main><nav><input id="q" placeholder="Filter theorems"><div id="list"></div></nav><section id="view"></section></main>
<script type="application/json" id="d">{json.dumps(ds, ensure_ascii=False).replace('</', '<\\/')}</script><script>{JS}</script></body></html>"""
    out.write_text(doc)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python3 -m proofscope.viewer")
    ap.add_argument("--dossiers", required=True)
    ap.add_argument("--bench", default=None)
    ap.add_argument("--title", default="ProofScope audit")
    ap.add_argument("--out", default="proofscope_report.html")
    a = ap.parse_args(argv)
    p = build(Path(a.dossiers), Path(a.bench) if a.bench else None, Path(a.out), a.title)
    print(f"wrote {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
