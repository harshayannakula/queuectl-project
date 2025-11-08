# queuectl/worker.py
import subprocess
import time
import signal
import threading
from multiprocessing import current_process
from .db import DB, DEFAULT_CONFIG

def worker_loop(worker_id: int):
    """
    Worker loop runs inside the child process.
    Create a local threading.Event here to watch for shutdown.
    """
    db = DB()
    proc = current_process()
    print(f"[worker {worker_id}] started (pid={proc.pid})")

    stop_event = threading.Event()

    def handle_sigterm(signum, frame):
        print(f"[worker {worker_id}] received shutdown signal; will exit after current job")
        stop_event.set()

    signal.signal(signal.SIGINT, handle_sigterm)
    signal.signal(signal.SIGTERM, handle_sigterm)

    backoff_base = db.get_config('backoff_base') or DEFAULT_CONFIG['backoff_base']
    global_timeout = db.get_config('job_timeout') or DEFAULT_CONFIG['job_timeout']

    while not stop_event.is_set():
        job = db.fetch_and_claim_job()
        if not job:
            time.sleep(0.5)
            continue
        job_id = job['id']
        command = job['command']
        attempts = job['attempts']
        max_retries = job['max_retries']
        job_timeout = job.get('timeout') or global_timeout
        print(f"[worker {worker_id}] picked job {job_id} (attempts={attempts}) -> {command} (timeout={job_timeout})")
        start = time.time()
        timed_out = False
        stdout = None
        stderr = None
        success = False
        exit_code = None
        try:
            completed = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=job_timeout)
            exit_code = completed.returncode
            stdout = completed.stdout
            stderr = completed.stderr
            success = (exit_code == 0)
            if success:
                print(f"[worker {worker_id}] job {job_id} completed (exit {exit_code}) in {time.time()-start:.2f}s")
            else:
                print(f"[worker {worker_id}] job {job_id} failed (exit {exit_code})")
        except subprocess.TimeoutExpired as e:
            timed_out = True
            stdout = getattr(e, 'output', '') or ''
            stderr = getattr(e, 'stderr', '') or ''
            exit_code = -1
            print(f"[worker {worker_id}] job {job_id} timed out after {job_timeout}s")
        except Exception as e:
            exit_code = -1
            stderr = str(e)
            print(f"[worker {worker_id}] job {job_id} raised exception: {e}")

        duration = time.time() - start
        attempts = attempts + 1
        if success:
            db.update_job_after_run(job_id, True, attempts, max_retries, stdout=stdout, stderr=stderr, duration=duration, timed_out=timed_out)
        else:
            try:
                base = float(backoff_base)
            except Exception:
                base = DEFAULT_CONFIG['backoff_base']
            delay = int(base ** attempts)
            err_msg = f"exit={exit_code}" + (", timeout" if timed_out else "")
            db.update_job_after_run(job_id, False, attempts, max_retries, error_msg=err_msg, next_available_delay=delay, stdout=stdout, stderr=stderr, duration=duration, timed_out=timed_out)
            if attempts >= max_retries:
                print(f"[worker {worker_id}] job {job_id} moved to DLQ after {attempts} attempts")
            else:
                print(f"[worker {worker_id}] will retry job {job_id} after {delay}s (attempt {attempts}/{max_retries})")

    print(f"[worker {worker_id}] exiting")
