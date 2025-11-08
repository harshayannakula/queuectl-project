QueueCTL – CLI-Based Background Job Queue System

Author: Yannakula Harshith
GitHub Repository: https://github.com/harshayannakula/queuectl-project

Demo Video: (https://drive.google.com/file/d/1tzc2JZ5Vu0ljiLcYPP7hy97K8Az4KPMd/view?usp=sharing)

<!--
Objective

    QueueCTL is a CLI-based background job queue system that allows you to:

    Enqueue background jobs.

    Run one or more worker processes to execute them.

    Retry failed jobs automatically using exponential backoff.

    Move permanently failed jobs to a Dead Letter Queue (DLQ).

    Store jobs persistently in a SQLite database so no data is lost on restart.

    Manage configuration dynamically (max retries, backoff base, job timeout).


Tech Stack

Language: Python 3.8+

Database: SQLite (persistent job storage)

CLI Framework: argparse

Concurrency: multiprocessing

Testing: pytest

OS Compatibility: macOS / Linux / Windows (WSL)


-->

#Setup Instructions:

#1. Clone & Setup Virtual Environment


git clone https://github.com/harshayannakula/queuectl-project.git
cd queuectl-project
python3 -m venv .venv
source .venv/bin/activate      # (use .venv\Scripts\activate on Windows)
pip install -U pip pytest


#2. Verify Installation

./bin/queuectl --help


#Usage Examples:

#Enqueue a Job
./bin/queuectl enqueue '{"id":"job1","command":"echo Hello-QueueCTL","max_retries":2}'

#Start Workers
./bin/queuectl worker start --count 2 &

#Check Queue Status
./bin/queuectl status

#List Jobs
./bin/queuectl list
./bin/queuectl list --state completed

#Manage DLQ
./bin/queuectl dlq list
./bin/queuectl dlq retry job1

#Update Configuration
./bin/queuectl config set backoff_base 1.5
./bin/queuectl config set job_timeout 5
./bin/queuectl config get backoff_base


#Stop Workers Gracefully
./bin/queuectl worker stop


#Testing Instructions:

#Run Automated Tests
pytest -q

#Run Demo Script Automatically
chmod +x tests/run_demo.sh
./tests/run_demo.sh

#Manual Demo:

#Terminal A (worker logs)
python3 -m queuectl.cli worker start --count 1

#Terminal B (CLI actions)
./bin/queuectl enqueue '{"id":"demo1","command":"echo Hello","max_retries":2}'
./bin/queuectl enqueue '{"id":"demo2","command":"nonexistent-cmd","max_retries":2}'
sleep 3
./bin/queuectl status
./bin/queuectl list
./bin/queuectl dlq list
./bin/queuectl dlq retry demo2
./bin/queuectl worker stop

<!--
Sample Job Record (from DB)
{
  "id": "demo1",
  "command": "echo Hello",
  "state": "completed",
  "attempts": 1,
  "max_retries": 3,
  "stdout": "Hello\n",
  "stderr": "",
  "duration": 0.01,
  "timed_out": 0,
  "timeout": 10,
  "created_at": "2025-11-08T16:12:48.385Z",
  "updated_at": "2025-11-08T16:12:49.012Z"
}
-->

