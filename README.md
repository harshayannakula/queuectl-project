QueueCTL – CLI-Based Background Job Queue System

Author: Yannakula Harshith
GitHub Repository: https://github.com/harshayannakula/queuectl-project

Demo Video: (https://drive.google.com/file/d/1tzc2JZ5Vu0ljiLcYPP7hy97K8Az4KPMd/view?usp=sharing)


Objective<br>

    QueueCTL is a CLI-based background job queue system that allows you to:

    Enqueue background jobs.

    Run one or more worker processes to execute them.

    Retry failed jobs automatically using exponential backoff.

    Move permanently failed jobs to a Dead Letter Queue (DLQ).

    Store jobs persistently in a SQLite database so no data is lost on restart.

    Manage configuration dynamically (max retries, backoff base, job timeout).


Tech Stack<br>

    Language: Python 3.8+

    Database: SQLite (persistent job storage)

    CLI Framework: argparse 

    Concurrency: multiprocessing

    Testing: pytest

    OS Compatibility: macOS / Linux / Windows (WSL)


<br>

#Setup Instructions:
<br>
#1. Clone & Setup Virtual Environment
<br>

    git clone https://github.com/harshayannakula/queuectl-project.git 
    cd queuectl-project
    python3 -m venv .venv
    source .venv/bin/activate      # (use .venv\Scripts\activate on Windows)
    pip install -U pip pytest

<br>
#2. Verify Installation<br>
<br>

    ./bin/queuectl --help

<br>
#Usage Examples:<br>

#Enqueue a Job<br>

    ./bin/queuectl enqueue '{"id":"job1","command":"echo Hello-QueueCTL","max_retries":2}'
<br>
#Start Workers<br>

    ./bin/queuectl worker start --count 2 &
    
<br>
#Check Queue Status<br>

    ./bin/queuectl status
<br>
#List Jobs<br>

    ./bin/queuectl list
    ./bin/queuectl list --state completed
<br>
#Manage DLQ<br>

    ./bin/queuectl dlq list
    ./bin/queuectl dlq retry job1
<br>

#Update Configuration<br>

    ./bin/queuectl config set backoff_base 1.5
    ./bin/queuectl config set job_timeout 5
    ./bin/queuectl config get backoff_base
<br>

#Stop Workers Gracefully<br>

    ./bin/queuectl worker stop

<br>
#Testing Instructions:<br>
<br>
#Run Automated Tests<br>

    pytest -q

#Run Demo Script Automatically<br>

    chmod +x tests/run_demo.sh
    ./tests/run_demo.sh
<br>
#Manual Demo:<br>
<br>
#Terminal A (worker logs)<br>

    python3 -m queuectl.cli worker start --count 1
<br>
#Terminal B (CLI actions)<br>

    ./bin/queuectl enqueue '{"id":"demo1","command":"echo Hello","max_retries":2}'
    ./bin/queuectl enqueue '{"id":"demo2","command":"nonexistent-cmd","max_retries":2}'
    sleep 3
    ./bin/queuectl status
    ./bin/queuectl list
    ./bin/queuectl dlq list
    ./bin/queuectl dlq retry demo2
    ./bin/queuectl worker stop
<br>

Sample Job Record (from DB)<br>

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

