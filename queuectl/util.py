import os, sqlite3, json, time, signal, contextlib, uuid
from typing import Optional, Dict, Any, List

DEFAULT_DIR = os.path.join(os.getcwd(), ".queuectl")
DEFAULT_DB = os.path.join(DEFAULT_DIR, "queue.db")
PID_FILE = os.path.join(DEFAULT_DIR, "pids.json")

SCHEMA = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS jobs(
  id TEXT PRIMARY KEY,
  command TEXT NOT NULL,
  state TEXT NOT NULL,                  -- pending|processing|completed|dead
  attempts INTEGER NOT NULL DEFAULT 0,
  max_retries INTEGER NOT NULL DEFAULT 3,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  run_at REAL NOT NULL,                 -- epoch seconds when eligible
  worker_id TEXT,
  last_error TEXT,
  last_exit_code INTEGER
);
CREATE INDEX IF NOT EXISTS idx_jobs_state_runat ON jobs(state, run_at);

CREATE TABLE IF NOT EXISTS config(
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
"""

DEFAULT_CONFIG = {
    "max_retries": "3",
    "backoff_base": "2",
    "timeout_seconds": "0",
}

def _iso_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time()))

def ensure_dirs():
    os.makedirs(DEFAULT_DIR, exist_ok=True)

def connect() -> sqlite3.Connection:
    ensure_dirs()
    conn = sqlite3.connect(DEFAULT_DB, timeout=30, isolation_level=None)
    conn.row_factory = sqlite3.Row
    with conn:
        for stmt in SCHEMA.strip().split(";"):
            s = stmt.strip()
            if s:
                conn.execute(s + ";")
        for k, v in DEFAULT_CONFIG.items():
            conn.execute(
                "INSERT OR IGNORE INTO config(key,value) VALUES(?,?)", (k, v)
            )
    return conn

@contextlib.contextmanager
def tx(conn: sqlite3.Connection):
    conn.execute("BEGIN IMMEDIATE;")
    try:
        yield
        conn.execute("COMMIT;")
    except:
        conn.execute("ROLLBACK;")
        raise

# ---------------------------- Jobs / Queue ----------------------------

def insert_job(conn: sqlite3.Connection, payload: Dict[str, Any]) -> str:
    jid = payload.get("id") or str(uuid.uuid4())
    if "command" not in payload or not str(payload["command"]).strip():
        raise ValueError("Job payload must include non-empty 'command'")
    cmd = payload["command"]
    now_epoch = time.time()
    t = _iso_now()
    mr = int(payload.get("max_retries") or DEFAULT_CONFIG["max_retries"])
    with tx(conn):
        conn.execute(
            """
            INSERT INTO jobs(id, command, state, attempts, max_retries, created_at, updated_at, run_at, worker_id, last_error, last_exit_code)
            VALUES(?,?,?,?,?,?,?,?,?,?,?)
            """,
            (jid, cmd, "pending", 0, mr, t, t, now_epoch, None, None, None),
        )
    return jid

def list_jobs(conn: sqlite3.Connection, state: Optional[str] = None) -> List[sqlite3.Row]:
    if state:
        return conn.execute(
            "SELECT * FROM jobs WHERE state=? ORDER BY run_at ASC, created_at ASC", (state,)
        ).fetchall()
    return conn.execute(
        "SELECT * FROM jobs ORDER BY run_at ASC, created_at ASC"
    ).fetchall()

def counts(conn: sqlite3.Connection) -> Dict[str, int]:
    out = {}
    for s in ["pending", "processing", "completed", "dead"]:
        out[s] = conn.execute(
            "SELECT COUNT(1) AS c FROM jobs WHERE state=?", (s,)
        ).fetchone()["c"]
    return out

def get_config(conn: sqlite3.Connection) -> Dict[str, str]:
    return {r["key"]: r["value"] for r in conn.execute("SELECT key,value FROM config")}

def set_config(conn: sqlite3.Connection, key: str, value: str):
    with tx(conn):
        conn.execute(
            "INSERT INTO config(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )

def reserve_job(conn: sqlite3.Connection, wid: str):
    """Atomically move one eligible job to processing and return it."""
    now_epoch = time.time()
    with tx(conn):
        row = conn.execute(
            "SELECT id FROM jobs WHERE state='pending' AND run_at<=? ORDER BY run_at ASC, created_at ASC LIMIT 1",
            (now_epoch,),
        ).fetchone()
        if not row:
            return None
        jid = row["id"]
        # Guard against races
        updated = conn.execute(
            "UPDATE jobs SET state='processing', worker_id=?, updated_at=? WHERE id=? AND state='pending'",
            (wid, _iso_now(), jid),
        )
        if updated.rowcount != 1:
            return None
    return conn.execute("SELECT * FROM jobs WHERE id=?", (jid,)).fetchone()

def mark_done(conn: sqlite3.Connection, job_id: str, success: bool, err: str | None, code: int):
    t = _iso_now()
    state = "completed" if success else "failed"
    with tx(conn):
        conn.execute(
            "UPDATE jobs SET state=?, last_error=?, last_exit_code=?, updated_at=?, worker_id=NULL WHERE id=?",
            (state, err, code, t, job_id),
        )

def schedule_retry_or_dlq(conn: sqlite3.Connection, job: sqlite3.Row, base: int):
    attempts = job["attempts"] + 1
    max_retries = job["max_retries"]
    delay = base ** attempts
    due = time.time() + delay
    t = _iso_now()
    with tx(conn):
        if attempts > max_retries:
            conn.execute(
                "UPDATE jobs SET state='dead', attempts=?, updated_at=?, worker_id=NULL WHERE id=?",
                (attempts, t, job["id"]),
            )
        else:
            conn.execute(
                "UPDATE jobs SET state='pending', attempts=?, run_at=?, updated_at=?, worker_id=NULL WHERE id=?",
                (attempts, due, t, job["id"]),
            )

# ---------------------------- Worker PIDs ----------------------------

def pids_load() -> Dict[str, Any]:
    ensure_dirs()
    if not os.path.exists(PID_FILE):
        return {"workers": []}
    try:
        return json.load(open(PID_FILE, "r"))
    except Exception:
        return {"workers": []}

def pids_save(data: Dict[str, Any]):
    ensure_dirs()
    with open(PID_FILE, "w") as f:
        json.dump(data, f, indent=2)

def kill_pids(pids: List[int]):
    for pid in pids:
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass

def pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
