import os, subprocess, time, signal
from .util import connect, reserve_job, mark_done, schedule_retry_or_dlq, get_config, LOG_DIR

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

        jid = job["id"]
        cmd = job["command"]
        os.makedirs(LOG_DIR, exist_ok=True)
        log_path = os.path.join(LOG_DIR, f"{jid}.log")

        try:
            with open(log_path, "w") as lf:
                proc = subprocess.run(
                    cmd, shell=True, timeout=timeout,
                    stdout=lf, stderr=subprocess.STDOUT
                )
            ok = proc.returncode == 0
            mark_done(conn, jid, ok, None if ok else f"exit {proc.returncode}", proc.returncode)
            if not ok:
                schedule_retry_or_dlq(conn, job, base)
        except subprocess.TimeoutExpired:
            with open(log_path, "a") as lf:
                lf.write("\n[ERROR] Job timed out.\n")
            mark_done(conn, jid, False, "timeout", 124)
            schedule_retry_or_dlq(conn, job, base)
        except FileNotFoundError as e:
            with open(log_path, "a") as lf:
                lf.write(f"\n[ERROR] {e}\n")
            mark_done(conn, jid, False, str(e), 127)
            schedule_retry_or_dlq(conn, job, base)
        except Exception as e:
            with open(log_path, "a") as lf:
                lf.write(f"\n[EXCEPTION] {e}\n")
            mark_done(conn, jid, False, str(e), 1)
            schedule_retry_or_dlq(conn, job, base)
