#!/usr/bin/env bash
set -euo pipefail

python -m queuectl enqueue '{"id":"demo1","command":"echo demo"}'
python -m queuectl worker start --count 1
sleep 1
python -m queuectl status
python -m queuectl worker stop
