import json, os, subprocess, sys, time, typer
from typing import Optional
from rich import print, box
from rich.table import Table
from .util import (
    connect, insert_job, list_jobs, counts,
    get_config, set_config,
    pids_load, pids_save, kill_pids, pid_alive,
)
from .worker import run_worker

app = typer.Typer(help="QueueCTL — Background job queue CLI.", add_completion=False)

# ---------------- Enqueue ----------------

@app.command()
def enqueue(job_json: str):
    """
    Add a new job.
    Example:
      queuectl enqueue '{"id":"job1","command":"sleep 2"}'
    """
    conn = connect()
    try:
        payload = json.loads(job_json)
    except json.JSONDecodeError as e:
        print(f"[red]Invalid JSON:[/red] {e}")
        raise typer.Exit(1)
    try:
        jid = insert_job(conn, payload)
    except Exception as e:
        print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
    print(f"[green]Enqueued[/green] id=[bold]{jid}[/bold]")

# ---------------- Workers ----------------

worker = typer.Typer(help="Worker management")
app.add_typer(worker, name="worker")

@worker.command("start")
def worker_start(count: int = typer.Option(1, "--count", min=1, help="Number of workers to start")):
    """Start one or more workers (background)."""
    p = pids_load()
    # keep only live
    p["workers"] = [pid for pid in p.get("workers", []) if pid_alive(pid)]
    spawned = []
    for _ in range(count):
        pid = subprocess.Popen([sys.executable, "-c", "from queuectl.worker import run_worker; run_worker()"]).pid
        spawned.append(pid)
    p["workers"].extend(spawned)
    pids_save(p)
    print(f"[green]Started[/green] {len(spawned)} worker(s): {', '.join(map(str, spawned))}")

@worker.command("stop")
def worker_stop():
    """Stop running workers gracefully."""
    p = pids_load()
    workers = p.get("workers", [])
    if not workers:
        print("[yellow]No workers to stop.[/yellow]")
        return
    print(f"Stopping {len(workers)} worker(s)...")
    kill_pids(workers)
    time.sleep(0.5)
    alive = [pid for pid in workers if pid_alive(pid)]
    if alive:
        print("[yellow]Some workers still shutting down…[/yellow]")
    p["workers"] = alive
    pids_save(p)
    print("[green]Stop signal sent.[/green]")

# ---------------- Status ----------------

@app.command()
def status():
    """Show summary of all job states & active workers."""
    conn = connect()
    c = counts(conn)
    table = Table(title="QueueCTL Status", box=box.SIMPLE)
    table.add_column("State")
    table.add_column("Count", justify="right")
    for s in ["pending", "processing", "completed", "dead"]:
        table.add_row(s, str(c[s]))
    print(table)

    p = pids_load()
    live = [pid for pid in p.get("workers", []) if pid_alive(pid)]
    print(f"[cyan]Workers active:[/cyan] {len(live)}")
    if live:
        print(", ".join(map(str, live)))

# ---------------- List Jobs ----------------

@app.command("list")
def list_command(state: Optional[str] = typer.Option(None, "--state", help="Filter by job state")):
    """List jobs by state."""
    conn = connect()
    rows = list_jobs(conn, state)
    table = Table(title=f"Jobs ({state or 'all'})", box=box.SIMPLE)
    table.add_column("id")
    table.add_column("state")
    table.add_column("cmd")
    table.add_column("attempts", justify="right")
    table.add_column("run_at", justify="right")
    for r in rows:
        table.add_row(r["id"], r["state"], r["command"], str(r["attempts"]),
                      time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(r["run_at"])))
    print(table)

# ---------------- DLQ ----------------

dlq = typer.Typer(help="Dead Letter Queue")
app.add_typer(dlq, name="dlq")

@dlq.command("list")
def dlq_list():
    """View DLQ jobs (state=dead)."""
    conn = connect()
    rows = list_jobs(conn, "dead")
    table = Table(title="DLQ", box=box.SIMPLE)
    table.add_column("id")
    table.add_column("cmd")
    table.add_column("attempts", justify="right")
    for r in rows:
        table.add_row(r["id"], r["command"], str(r["attempts"]))
    print(table)

@dlq.command("retry")
def dlq_retry(job_id: str):
    """Retry a DLQ job (resets attempts to 0, moves to pending)."""
    conn = connect()
    with conn:
        row = conn.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
        if not row or row["state"] != "dead":
            print(f"[red]Not in DLQ:[/red] {job_id}")
            raise typer.Exit(1)
        conn.execute(
            "UPDATE jobs SET state='pending', attempts=0, run_at=strftime('%s','now'), updated_at=strftime('%Y-%m-%dT%H:%M:%SZ','now') WHERE id=?",
            (job_id,),
        )
    print(f"[green]Requeued[/green] {job_id}")

# ---------------- Config ----------------

config = typer.Typer(help="Configuration")
app.add_typer(config, name="config")

@config.command("get")
def config_get():
    """Show current configuration."""
    conn = connect()
    cfg = get_config(conn)
    table = Table(title="Config", box=box.SIMPLE)
    table.add_column("Key")
    table.add_column("Value")
    for k, v in cfg.items():
        table.add_row(k, v)
    print(table)

@config.command("set")
def config_set(key: str, value: str):
    """Set a config value (max_retries, backoff_base, timeout_seconds)."""
    conn = connect()
    set_config(conn, key, value)
    print(f"[green]Set[/green] {key} = {value}")
