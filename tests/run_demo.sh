#!/usr/bin/env bash
# quick demo: enqueue jobs, start worker, show status, then stop
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CLI="${ROOT}/bin/queuectl"

echo "1) Enqueue success job"
$CLI enqueue '{"id":"job1","command":"echo hello from job1","max_retries":2}'

echo "2) Enqueue fail job"
$CLI enqueue '{"id":"bad1","command":"/bin/false","max_retries":2}'

echo "3) Start 2 workers (run in foreground; open another terminal to run status/stop)"
$CLI worker start --count 2 &
WORKER_PID=$!
echo "workers started (pid $WORKER_PID). waiting 6s for processing..."
sleep 6

echo "4) Status:"
$CLI status

echo "5) List all:"
$CLI list

echo "6) List DLQ:"
$CLI dlq list

echo "7) If bad1 is dead, retry it (if present)"
$CLI dlq retry bad1 || true

echo "8) Stop workers"
$CLI worker stop || true

echo "Demo finished."
