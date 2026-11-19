import asyncio
import json
import sqlite3
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

# --- Data Models ---

class ToolExecution(BaseModel):
    tool_name: str
    input_args: Dict[str, Any]
    status: str = "pending"
    latency_ms: float = 0.0
    timestamp: str = ""

# --- Database Layer ---

class RuntimeDB:
    def __init__(self, db_path: str = "runtime.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS executions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tool_name TEXT,
                    input_args TEXT,
                    status TEXT,
                    latency_ms REAL,
                    timestamp TEXT
                )
            """)

    def log_execution(self, exec: ToolExecution):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO executions (tool_name, input_args, status, latency_ms, timestamp) VALUES (?, ?, ?, ?, ?)",
                (exec.tool_name, json.dumps(exec.input_args), exec.status, exec.latency_ms, exec.timestamp)
            )

    def get_history(self) -> List[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM executions ORDER BY id DESC LIMIT 50")
            return [dict(row) for row in cursor.fetchall()]

# --- Web Application ---

app = FastAPI(title="Speculative Agent Tool Runtime")
db = RuntimeDB()

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <script src="https://cdn.tailwindcss.com"></script>
    <script>tailwind.config = { darkMode: 'class' };</script>
    <style>
        body { background-color: #09090B; color: #FAFAFA; font-family: 'Inter', sans-serif; }
        .glass { background: #121214; border: 1px solid #27272A; }
        .mono { font-family: 'ui-monospace', 'SFMono-Regular', monospace; }
    </style>
</head>
<body class="p-8">
    <div class="max-w-5xl mx-auto">
        <header class="mb-10">
            <h1 class="text-2xl font-bold tracking-tight">Speculative Runtime</h1>
            <p class="text-zinc-500 text-sm">Real-time agent tool execution telemetry</p>
        </header>

        <div class="grid grid-cols-1 gap-6">
            <div class="glass p-6 rounded-xl">
                <h2 class="text-sm font-semibold mb-4 uppercase tracking-wider text-zinc-400">Execution Stream</h2>
                <div id="stream" class="space-y-2">
                    <!-- Dynamic Content -->
                </div>
            </div>
        </div>
    </div>

    <script>
        async function update() {
            const res = await fetch('/api/history');
            const data = await res.json();
            const container = document.getElementById('stream');
            container.innerHTML = data.map(item => `
                <div class="flex items-center justify-between p-3 border-b border-white/5 hover:bg-white/5 transition-colors">
                    <div class="flex items-center gap-4">
                        <span class="text-xs text-zinc-500 mono">${item.timestamp.split(' ')[1]}</span>
                        <span class="font-medium">${item.tool_name}</span>
                    </div>
                    <div class="flex items-center gap-6">
                        <span class="text-xs mono text-zinc-400">${item.latency_ms.toFixed(2)}ms</span>
                        <span class="px-2 py-0.5 rounded text-[10px] uppercase font-bold ${item.status === 'success' ? 'bg-emerald-500/10 text-emerald-500' : 'bg-rose-500/10 text-rose-500'}">${item.status}</span>
                    </div>
                </div>
            `).join('');
        }
        setInterval(update, 2000);
        update();
    </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def index():
    return HTML_TEMPLATE

@app.get("/api/history")
async def get_history():
    return db.get_history()

@app.post("/api/execute")
async def execute_tool(tool: ToolExecution):
    start = time.perf_counter()
    # Simulate execution logic
    await asyncio.sleep(0.1) 
    latency = (time.perf_counter() - start) * 1000
    
    tool.latency_ms = latency
    tool.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    db.log_execution(tool)
    return {"status": "ok", "latency": latency}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)