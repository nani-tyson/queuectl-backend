# QueueCTL — CLI Job Queue (Python + SQLite)

A CLI-based background job queue system built in Python.  
It supports multiple workers, exponential backoff retries, and a Dead Letter Queue (DLQ) —  
all persisted using SQLite for durability and easy recovery.

---

## Overview

QueueCTL allows you to manage background jobs efficiently from the command line.  
You can enqueue jobs, run them with multiple workers, handle failures with retries,  
and track progress, metrics, and configurations — all from a simple CLI.

---

## Quickstart

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate    # or .venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt

# Enqueue a simple job
python -m queuectl enqueue '{"id":"job1","command":"echo Hello"}'

# Start a worker
python -m queuectl worker start --count 1

# Check status
python -m queuectl status

# Stop all workers
python -m queuectl worker stop


---

## CLI Commands

| Command | Description |
| -------- | ------------ |
| `python -m queuectl enqueue '{"id":"job1","command":"sleep 2"}'` | Add a new job to the queue |
| `python -m queuectl worker start --count 3` | Start one or more workers |
| `python -m queuectl worker stop` | Stop running workers gracefully |
| `python -m queuectl status` | Show summary of job states and active workers |
| `python -m queuectl list --state pending` | List jobs filtered by state |
| `python -m queuectl dlq list` | View jobs in the Dead Letter Queue |
| `python -m queuectl dlq retry job1` | Retry a DLQ job |
| `python -m queuectl config set max_retries 5` | Update retry configuration |
| `python -m queuectl config get` | View current configuration |
| `python -m queuectl metrics` | Display success rate, failures, and averages |

---

## Features

### Core
- Persistent job storage using SQLite  
- Multiple worker processes running concurrently  
- Exponential backoff retry mechanism  
- Dead Letter Queue (DLQ) for permanently failed jobs  
- Graceful shutdown — workers complete current jobs before stopping  
- Simple CLI interface using Typer and Rich  

### Advanced (Bonus)
- Scheduled jobs via `run_at` timestamp  
- Priority queueing (higher `priority` runs earlier)  
- Timeout handling for slow commands  
- Job output logging in `.queuectl/logs/<job_id>.log`  
- Configurable retry, backoff, and timeout values  
- Metrics view for success rate and average attempts  

---

## Configuration

You can modify system behavior using configuration commands.

| Key | Description | Example |
|-----|--------------|----------|
| `max_retries` | Maximum number of retries for a job | `queuectl config set max_retries 3` |
| `backoff_base` | Base value for exponential backoff | `queuectl config set backoff_base 2` |
| `timeout_seconds` | Job execution timeout in seconds | `queuectl config set timeout_seconds 10` |

All configurations persist in SQLite.

---

## Example Flow

# Set configurations
python -m queuectl config set max_retries 2
python -m queuectl config set backoff_base 2

# Enqueue jobs
python -m queuectl enqueue '{"id":"ok1","command":"echo done"}'
python -m queuectl enqueue '{"id":"bad1","command":"invalid_cmd"}'

# Start workers
python -m queuectl worker start --count 2

# Wait for jobs to complete
sleep 4

# Check DLQ
python -m queuectl dlq list

# Retry failed jobs
python -m queuectl dlq retry bad1

# View metrics
python -m queuectl metrics


## Metrics Example

Total jobs: 5
Completed: 3
Dead: 2
Success rate: 60.0%
Average attempts/job: 1.4


---

## Project Structure

```
queuectl/
├── queuectl/
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli.py           # CLI commands and routing
│   ├── util.py          # SQLite handling, job logic, configuration
│   └── worker.py        # Worker implementation with retries and timeouts
├── scripts/
│   └── demo.sh          # Full end-to-end demonstration script
├── tests/
│   └── test_basic.py    # Basic smoke tests
├── requirements.txt
└── README.md
```

---

## Demo Script

Run the included demo to see the complete flow:

```bash
bash scripts/demo.sh
```

This script:
1. Configures retry and timeout settings  
2. Enqueues valid and invalid jobs  
3. Starts multiple workers  
4. Processes jobs with exponential backoff  
5. Moves failed jobs to DLQ  
6. Retries DLQ jobs  
7. Displays metrics  
8. Stops workers gracefully  

---
---

## Demo Video

You can watch the full CLI demonstration here:  
[QueueCTL Demo Video](https://drive.google.com/file/d/1v-54uzKd3b2tOXAHQIMW-HXi-DjERJs-/view?usp=sharing)

---


## Architecture Overview

Each job goes through the following states:

```
pending → processing → completed / failed → dead (DLQ)
```

If a job fails, it is retried using **exponential backoff**:

```
delay = backoff_base ^ attempts
```

Once a job exceeds its retry limit, it is moved to the **Dead Letter Queue (DLQ)**.  
All state transitions, logs, and configurations are stored in SQLite, allowing safe restarts.

---

## Tech Stack

- **Language:** Python 3.10+  
- **Libraries:** Typer, Rich, SQLite3  
- **Storage:** Local SQLite database (`.queuectl/queue.db`)  
- **OS Support:** Works seamlessly on Linux, macOS, and WSL  

---


A basic smoke test ensures enqueueing, worker execution, and DLQ behavior are functional.

---
