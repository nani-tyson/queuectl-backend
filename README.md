```markdown
# QueueCTL — CLI Job Queue (Python + SQLite)

A CLI-based background job queue with workers, exponential backoff retries, and a Dead Letter Queue (DLQ).  
Everything persists in a local SQLite database for durability across restarts.

---

## ⚙️ Quickstart

```bash
# create & activate venv
python -m venv .venv && source .venv/bin/activate

# install dependencies
pip install -r requirements.txt

# enqueue a job
python -m queuectl enqueue '{"id":"job1","command":"echo Hello"}'

# start 2 workers
python -m queuectl worker start --count 2

# check queue status
python -m queuectl status

# stop all workers
python -m queuectl worker stop
```

---

## 🧩 Commands Overview

| Command                                                          | Description                                     |
| ---------------------------------------------------------------- | ----------------------------------------------- |
| `python -m queuectl enqueue '{"id":"job1","command":"sleep 2"}'` | Add a new job to the queue                      |
| `python -m queuectl worker start --count 3`                      | Start one or more workers                       |
| `python -m queuectl worker stop`                                 | Stop running workers gracefully                 |
| `python -m queuectl status`                                      | Show summary of all job states & active workers |
| `python -m queuectl list --state pending`                        | List jobs filtered by state                     |
| `python -m queuectl dlq list`                                    | View all jobs in the Dead Letter Queue          |
| `python -m queuectl dlq retry job1`                              | Retry a DLQ job                                 |
| `python -m queuectl config set max_retries 5`                    | Update retry configuration                      |
| `python -m queuectl config get`                                  | Display current configuration                   |

---

## 🧠 Key Features

- ✅ Persistent job storage with SQLite  
- ✅ Multiple worker processes with parallel execution  
- ✅ Exponential backoff retry mechanism (`delay = base ^ attempts`)  
- ✅ Dead Letter Queue (DLQ) for permanently failed jobs  
- ✅ Configurable retry, backoff, and timeout via CLI  
- ✅ Graceful worker shutdown (finish current job before exit)  
- ✅ Demonstration script (`scripts/demo.sh`)  
- ✅ Cross-platform (works perfectly on WSL/Linux/macOS)  

---

## 📂 Project Structure

```
queuectl/
├── queuectl/
│   ├── __main__.py      # CLI entrypoint
│   ├── cli.py           # Typer commands (enqueue, worker, status, dlq, etc.)
│   ├── util.py          # SQLite schema, config, job logic
│   └── worker.py        # Worker process implementation
├── scripts/
│   └── demo.sh          # End-to-end demo script
├── tests/
│   └── test_basic.py    # Smoke test
├── requirements.txt
└── README.md
```

---

## 🧪 Demo Script

Run the full example demo:

```bash
bash scripts/demo.sh
```

This will:
- Enqueue valid and invalid jobs  
- Start multiple workers  
- Process jobs with exponential backoff  
- Move failed jobs to DLQ  
- Retry DLQ jobs  
- Stop workers gracefully  

---

## 🧰 Tech Stack

- **Language:** Python 3.10+  
- **CLI Framework:** Typer + Rich  
- **Database:** SQLite (WAL mode enabled)  
- **Concurrency:** Multiprocessing (via subprocess workers)  
- **Persistence:** Automatic with `.queuectl/queue.db`  

---

## 🧾 Next Steps

- [ ] Add optional bonus features:
  - Job output logging
  - Scheduled jobs (`run_at`)
  - Job priority queues
  - Metrics or stats endpoint
- [ ] Create `design.md` (architecture & flow)
- [ ] Record CLI demo video for submission

---

**Author:** [Your Name]  
**License:** MIT  
**Repository:** https://github.com/<your-username>/queuectl
```

---