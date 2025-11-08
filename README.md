QueueCTL – CLI-Based Background Job Queue System

Author: Yannakula Harshith
GitHub Repository: https://github.com/harshayannakula/queuectl-project

Demo Video: (https://drive.google.com/file/d/1tzc2JZ5Vu0ljiLcYPP7hy97K8Az4KPMd/view?usp=sharing)


Objective<br>

    QueueCTL is a CLI-based background job queue system that allows you to:<br>

    Enqueue background jobs.<br>

    Run one or more worker processes to execute them.<br>

    Retry failed jobs automatically using exponential backoff.<br>

    Move permanently failed jobs to a Dead Letter Queue (DLQ).<br>

    Store jobs persistently in a SQLite database so no data is lost on restart.<br>

    Manage configuration dynamically (max retries, backoff base, job timeout).<br>


Tech Stack<br>

Language: Python 3.8+<br>

Database: SQLite (persistent job storage)<br>

CLI Framework: argparse<br>

Concurrency: multiprocessing<br>

Testing: pytest<br>

OS Compatibility: macOS / Linux / Windows (WSL)<br>


<br>

#Setup Instructions:
<br>
#1. Clone & Setup Virtual Environment<br>
<br>

git clone https://github.com/harshayannakula/queuectl-project.git <br>
cd queuectl-project<br>
python3 -m venv .venv<br>
source .venv/bin/activate      # (use .venv\Scripts\activate on Windows)<br>
pip install -U pip pytest<br>

<br>
#2. Verify Installation<br>
<br>
./bin/queuectl --help<br>

<br>
#Usage Examples:<br>

#Enqueue a Job<br>
./bin/queuectl enqueue '{"id":"job1","command":"echo Hello-QueueCTL","max_retries":2}'<br>
<br>
#Start Workers<br>
./bin/queuectl worker start --count 2 &<br>
<br>
#Check Queue Status<br>
./bin/queuectl status<br>
<br>
#List Jobs<br>
./bin/queuectl list<br>
./bin/queuectl list --state completed<br>
<br>
#Manage DLQ<br>
./bin/queuectl dlq list<br>
./bin/queuectl dlq retry job1<br>
<br>
#Update Configuration<br>
./bin/queuectl config set backoff_base 1.5<br>
./bin/queuectl config set job_timeout 5<br>
./bin/queuectl config get backoff_base<br>
<br>

#Stop Workers Gracefully<br>
./bin/queuectl worker stop<br>

<br>
#Testing Instructions:<br>
<br>
#Run Automated Tests<br>
pytest -q<br>

#Run Demo Script Automatically<br>
chmod +x tests/run_demo.sh<br>
./tests/run_demo.sh<br>
<br>
#Manual Demo:<br>
<br>
#Terminal A (worker logs)<br>
python3 -m queuectl.cli worker start --count 1<br>
<br>
#Terminal B (CLI actions)<br>
./bin/queuectl enqueue '{"id":"demo1","command":"echo Hello","max_retries":2}'<br>
./bin/queuectl enqueue '{"id":"demo2","command":"nonexistent-cmd","max_retries":2}'<br>
sleep 3<br>
./bin/queuectl status<br>
./bin/queuectl list<br>
./bin/queuectl dlq list<br>
./bin/queuectl dlq retry demo2<br>
./bin/queuectl worker stop<br>
<br>

Sample Job Record (from DB)<br>
{
  "id": "demo1",<br>
  "command": "echo Hello",<br>
  "state": "completed",<br>
  "attempts": 1,<br>
  "max_retries": 3,<br>
  "stdout": "Hello\n",<br>
  "stderr": "",<br>
  "duration": 0.01,<br>
  "timed_out": 0,<br>
  "timeout": 10,<br>
  "created_at": "2025-11-08T16:12:48.385Z",<br>
  "updated_at": "2025-11-08T16:12:49.012Z"<br>
}<br>

