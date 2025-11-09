#!/usr/bin/env bash
set -euo pipefail

echo ""
echo "=============================================="
echo "           QueueCTL — Demo Script"
echo "=============================================="
sleep 1

echo ""
echo "→ Step 1: Setting configuration values"
python -m queuectl config set max_retries 2
python -m queuectl config set backoff_base 2
python -m queuectl config set timeout_seconds 2
sleep 1

echo ""
echo "→ Step 2: Enqueuing jobs (2 valid + 1 invalid + 1 slow)"
python -m queuectl enqueue '{"id":"ok1","command":"echo Hello from QueueCTL"}'
python -m queuectl enqueue '{"id":"ok2","command":"sleep 1"}'
python -m queuectl enqueue '{"id":"bad1","command":"nonexistent_cmd"}'
python -m queuectl enqueue '{"id":"slow1","command":"sleep 5"}'
sleep 1

echo ""
echo "→ Step 3: Starting 2 worker processes"
python -m queuectl worker start --count 2
sleep 5

echo ""
echo "→ Step 4: Checking current job status"
python -m queuectl status
sleep 1

echo ""
echo "→ Step 5: Listing completed jobs"
python -m queuectl list --state completed
sleep 1

echo ""
echo "→ Step 6: Checking the Dead Letter Queue (DLQ)"
python -m queuectl dlq list
sleep 1

echo ""
echo "→ Step 7: Retrying one job from the DLQ"
python -m queuectl dlq retry bad1
sleep 3

echo ""
echo "→ Step 8: Viewing metrics summary"
python -m queuectl metrics
sleep 1

echo ""
echo "→ Step 9: Stopping all workers gracefully"
python -m queuectl worker stop
sleep 1

echo ""
echo "→ Step 10: Displaying job logs for 'ok1'"
cat .queuectl/logs/ok1.log
sleep 1

echo ""
echo "=============================================="
echo "          Demo Completed Successfully"
echo "=============================================="
