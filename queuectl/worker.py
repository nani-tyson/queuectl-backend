import os, subprocess, time, signal
from .util import connect, reserve_job, mark_done, schedule_retry_or_dlq, get_config

_stop = False
def _sigterm(signum, frame):
    global _stop
    _stop = True

def run_worker():
    signal.signal(signal.SIGTERM, _sigterm)
    signal.signal(signal.SIGINT, _sigterm)

    conn = connect()
    wid = f"w-{os.getpid()}"
    cfg = get_config(conn)
    base = int(cfg.get("backoff_base", "2"))
    timeout = int(cfg.get("timeout_seconds", "0")) or None

    while not _stop:
        job = reserve_job(conn, wid)
        if not job:
            time.sleep(0.5)
            continue

        cmd = job["command"]
        try:
            proc = subprocess.run(cmd, shell=True, timeout=timeout)
            ok = proc.returncode == 0
            mark_done(conn, job["id"], ok, None if ok else f"exit {proc.returncode}", proc.returncode)
            if not ok:
                schedule_retry_or_dlq(conn, job, base)
        except subprocess.TimeoutExpired:
            mark_done(conn, job["id"], False, "timeout", 124)
            schedule_retry_or_dlq(conn, job, base)
        except FileNotFoundError as e:
            mark_done(conn, job["id"], False, str(e), 127)
            schedule_retry_or_dlq(conn, job, base)
        except Exception as e:
            mark_done(conn, job["id"], False, str(e), 1)
            schedule_retry_or_dlq(conn, job, base)
