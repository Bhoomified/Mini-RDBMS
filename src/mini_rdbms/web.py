"""Localhost web interface for the Mini RDBMS."""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from mini_rdbms.integration.database import Database
from mini_rdbms.integration.session import Session


PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Mini RDBMS</title>
<style>
:root{--ink:#403b52;--muted:#7d7890;--paper:#fffaf7;--lav:#e9e2ff;--mint:#dff5e8;--peach:#ffe6d8;--blue:#dceeff;--line:#e4dfe8}
*{box-sizing:border-box}body{margin:0;background:linear-gradient(135deg,#fff1ed,#eef7ff);color:var(--ink);font:15px system-ui,-apple-system,sans-serif}
main{max-width:1180px;margin:0 auto;padding:28px}.hero{display:flex;justify-content:space-between;align-items:end;margin-bottom:20px}
h1{margin:0;font-size:30px}.subtitle{color:var(--muted);margin:6px 0 0}.badge{background:var(--lav);padding:9px 14px;border-radius:999px;font-weight:600}
.grid{display:grid;grid-template-columns:1.35fr .65fr;gap:18px}.card{background:rgba(255,250,247,.88);border:1px solid var(--line);border-radius:18px;padding:18px;box-shadow:0 8px 24px #8f829018}
textarea{width:100%;height:220px;border:1px solid var(--line);border-radius:12px;padding:14px;background:#fff;color:var(--ink);font:14px ui-monospace,SFMono-Regular,monospace;resize:vertical}
button{border:0;border-radius:10px;padding:10px 15px;color:var(--ink);font-weight:700;cursor:pointer;background:var(--mint);margin:8px 6px 0 0}
button.secondary{background:var(--blue)}button.warning{background:var(--peach)}button:hover{filter:brightness(.97)}
.toolbar{display:flex;flex-wrap:wrap;align-items:center}.status{color:var(--muted);margin-left:8px}.result{margin-top:14px;overflow:auto;max-height:360px}
table{border-collapse:collapse;width:100%;background:#fff}th,td{text-align:left;padding:9px 10px;border-bottom:1px solid var(--line);white-space:nowrap}th{background:var(--lav)}
pre{white-space:pre-wrap;background:#f8f5ff;border-radius:10px;padding:12px;overflow:auto}.schema-item{padding:10px 0;border-bottom:1px solid var(--line)}
.schema-item strong{display:block}.small{font-size:13px;color:var(--muted)}@media(max-width:800px){.grid{grid-template-columns:1fr}.hero{display:block}.badge{display:inline-block;margin-top:12px}}
</style></head>
<body><main>
<section class="hero"><div><h1>Mini RDBMS</h1><p class="subtitle">A small, inspectable database engine running locally.</p></div><div class="badge" id="connection">local database</div></section>
<section class="grid">
<div class="card"><h2>SQL workspace</h2>
<textarea id="sql">SELECT * FROM students;</textarea>
<div class="toolbar"><button onclick="runSql()">Run SQL</button><button class="secondary" onclick="explainSql()">Explain</button><button class="secondary" onclick="runSql('BEGIN;')">Begin</button><button class="secondary" onclick="runSql('COMMIT;')">Commit</button><button class="warning" onclick="runSql('ROLLBACK;')">Rollback</button><span class="status" id="status">Ready</span></div>
<div class="result" id="result"><p class="small">Run a statement to see its result.</p></div></div>
<aside class="card"><h2>Database</h2><div id="schema"><p class="small">Loading schema…</p></div></aside>
</section>
<section class="card" style="margin-top:18px"><h2>Engine walkthrough</h2>
<div class="grid" style="grid-template-columns:repeat(4,1fr);gap:10px">
<div class="schema-item" style="background:var(--lav)"><strong>E1 · Parsing</strong><span class="small">Lexer, parser, AST, semantic checks</span></div>
<div class="schema-item" style="background:var(--blue)"><strong>E2 · Optimizer</strong><span class="small">Full scan, HASH, or B+Tree plan</span></div>
<div class="schema-item" style="background:var(--peach)"><strong>E3 · Transactions</strong><span class="small">Locks, undo, commit, rollback</span></div>
<div class="schema-item" style="background:var(--mint)"><strong>E4 · Storage</strong><span class="small">Records, pages, indexes, WAL</span></div>
</div><h3>Last execution trace</h3><div id="trace"><p class="small">Run SQL to see E1 → E2 → E3 → E4.</p></div></section>
<section class="card" style="margin-top:18px"><h2>Working examples</h2>
<p class="small">These buttons execute immediately against the connected database.</p>
<div class="toolbar"><button onclick="setupDemo()">Create demo data</button><button onclick="runSql(\"INSERT INTO students VALUES (1, 'Alice', 20);\")">Insert row</button><button onclick="runSql('SELECT * FROM students WHERE age >= 18;')">Select adults</button><button onclick="runSql('EXPLAIN SELECT * FROM students WHERE id = 1;')">Explain query</button></div></section>
</main>
<script>
const $=id=>document.getElementById(id);
function setSql(value){$('sql').value=value;$('sql').focus()}
function render(value){
 if(Array.isArray(value)){if(!value.length)return '<p class="small">0 rows</p>';const cols=[...new Set(value.flatMap(x=>Object.keys(x)))];return '<table><thead><tr>'+cols.map(c=>'<th>'+esc(c)+'</th>').join('')+'</tr></thead><tbody>'+value.map(row=>'<tr>'+cols.map(c=>'<td>'+esc(row[c])+'</td>').join('')+'</tr>').join('')+'</tbody></table>'}
 if(value&&typeof value==='object')return '<pre>'+esc(JSON.stringify(value,null,2))+'</pre>';return '<pre>'+esc(value)+'</pre>'
}
function esc(value){return String(value??'NULL').replace(/[&<>\"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',\"'\":'&#39;'}[c]))}
function renderTrace(trace){$('trace').innerHTML=trace.map(item=>'<div class="schema-item"><strong>'+esc(item.engine)+' · '+esc(item.stage)+'</strong><span class="small">'+esc(item.detail)+'</span></div>').join('')}
async function runSql(sql=$('sql').value){$('sql').value=sql;$('status').textContent='Running…';const response=await fetch('/api/query',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({sql})});const data=await response.json();$('status').textContent=data.ok?'Success':'Error';$('result').innerHTML=data.ok?render(data.value):'<pre class="error">'+esc(data.error)+'</pre>';if(data.trace)renderTrace(data.trace);loadSchema();loadStatus()}
async function setupDemo(){const response=await fetch('/api/demo',{method:'POST'});const data=await response.json();$('status').textContent=data.ok?'Demo ready':'Error';$('result').innerHTML=data.ok?render(data.value):'<pre>'+esc(data.error)+'</pre>';if(data.trace)renderTrace(data.trace);loadSchema();loadStatus()}
function explainSql(){const sql=$('sql').value.trim();runSql(/^EXPLAIN\\b/i.test(sql)?sql:'EXPLAIN '+sql)}
async function loadSchema(){const response=await fetch('/api/schema');const data=await response.json();$('schema').innerHTML=data.tables.length?data.tables.map(t=>'<div class="schema-item"><strong>'+esc(t.name)+'</strong><span class="small">'+t.columns.map(c=>esc(c.name+' '+c.type+(c.primary_key?' PK':''))).join(' · ')+'</span>'+(t.indexes.length?'<br><span class="small">Indexes: '+t.indexes.map(esc).join(', ')+'</span>':'')+'</div>').join(''):'<p class="small">No tables yet.</p>'}
async function loadStatus(){const response=await fetch('/api/status');const data=await response.json();$('connection').textContent=(data.transaction?'transaction active':'connected')+' · '+data.database}
loadSchema();loadStatus();
</script></body></html>"""


class WebState:
    """Share one database session safely across HTTP requests."""

    def __init__(self, database_path: str) -> None:
        self.session = Session(Database(database_path))
        self.lock = threading.RLock()


def make_handler(state: WebState):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            return

        def do_GET(self):
            path = urlparse(self.path).path
            if path == "/":
                self._send(200, PAGE.encode("utf-8"), "text/html; charset=utf-8")
            elif path == "/api/schema":
                with state.lock:
                    tables = []
                    for table in state.session.database.catalog.list_tables():
                        indexes = [
                            index.name
                            for index in state.session.database.catalog.indexes()
                            if index.table_name == table.name
                        ]
                        tables.append({
                            "name": table.name,
                            "indexes": indexes,
                            "columns": [
                                {"name": column.name, "type": column.data_type.value,
                                 "primary_key": column.primary_key, "nullable": column.nullable}
                                for column in table.columns
                            ],
                        })
                self._json({"tables": tables})
            elif path == "/api/status":
                with state.lock:
                    self._json({
                        "database": state.session.database.path or "memory",
                        "transaction": state.session.executor.transaction is not None,
                    })
            else:
                self._json({"error": "not found"}, 404)

        def do_POST(self):
            path = urlparse(self.path).path
            if path == "/api/demo":
                with state.lock:
                    table = state.session.database.catalog.get_table("students")
                    trace = []
                    if table is None:
                        result = state.session.execute(
                            "CREATE TABLE students (id INT PRIMARY KEY, name TEXT, age INT)"
                        )
                        trace.extend(state.session.executor.last_trace)
                        if not result.is_ok:
                            self._json({"ok": False, "error": str(result.error), "trace": trace}, 400)
                            return
                    existing = list(state.session.database.storage.scan("students"))
                    if not existing:
                        result = state.session.execute(
                            "INSERT INTO students VALUES (1, 'Alice', 20), (2, 'Bob', 17)"
                        )
                        trace.extend(state.session.executor.last_trace)
                    else:
                        result = type("Result", (), {"is_ok": True, "value": {"rows": len(existing)}})()
                    self._json({"ok": True, "value": result.value, "trace": trace})
                return
            if path != "/api/query":
                self._json({"error": "not found"}, 404)
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length))
                sql = payload.get("sql", "")
                with state.lock:
                    result = state.session.execute(sql)
                if result.is_ok:
                    self._json({"ok": True, "value": result.value, "trace": state.session.executor.last_trace})
                else:
                    self._json({"ok": False, "error": str(result.error), "trace": state.session.executor.last_trace}, 400)
            except (ValueError, json.JSONDecodeError) as error:
                self._json({"ok": False, "error": str(error)}, 400)

        def _json(self, value, status=200):
            self._send(status, json.dumps(value, default=str).encode("utf-8"), "application/json")

        def _send(self, status, body, content_type):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return Handler


def serve(host: str = "127.0.0.1", port: int = 8000, database_path: str | None = None) -> None:
    """Serve the local GUI until interrupted."""
    if database_path is None:
        database_path = str(Path(__file__).resolve().parents[2] / "data" / "minirdb.db")
    state = WebState(database_path)
    server = ThreadingHTTPServer((host, port), make_handler(state))
    print(f"Mini RDBMS GUI: http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        state.session.close()
        state.session.database.close()
        server.server_close()


if __name__ == "__main__":
    serve()
