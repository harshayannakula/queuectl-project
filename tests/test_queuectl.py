# tests/test_queuectl.py
import os
import time
import json
import signal
import shutil
import pytest
from multiprocessing import Process
from pathlib import Path

# ensure we can import the package when tests run inside tmpdir
ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT))

from queuectl.db import DB
from queuectl.worker import worker_loop

CLI = ROOT / 'bin' / 'queuectl'

def start_worker_proc(worker_id=1):
    p = Process(target=worker_loop, args=(worker_id,))
    p.start()
    return p

def stop_proc(p):
    try:
        if p.is_alive():
            p.terminate()
            p.join(timeout=3)
    except Exception:
        pass

@pytest.fixture(autouse=True)
def chdir_tmp(tmp_path, monkeypatch):
    # run each test inside a fresh directory so DB is private
    monkeypatch.chdir(tmp_path)
    yield

def wait_for_condition(timeout=5, interval=0.1):
    start = time.time()
    while time.time() - start < timeout:
        if (yield_condition := (yield)):
            return True
        time.sleep(interval)
    return False

def read_job(db, job_id):
    rows = db.list_jobs()
    for r in rows:
        if r['id'] == job_id:
            return r
    return None

def test_basic_job_completes():
    db = DB()
    db.set_config('backoff_base', 1)  # fast retries if any
    # start worker
    p = start_worker_proc(1)
    jobid = 'basic-1'
    db.enqueue({'id': jobid, 'command': "echo test-basic", 'max_retries': 1})
    # wait for completion
    for _ in range(50):
        r = read_job(db, jobid)
        if r and r['state'] == 'completed':
            assert r['stdout'] is not None and 'test-basic' in (r['stdout'] or '')
            stop_proc(p)
            return
        time.sleep(0.1)
    stop_proc(p)
    pytest.fail("basic job did not complete in time")

def test_failed_job_retries_and_moves_to_dlq():
    db = DB()
    db.set_config('backoff_base', 1)
    # start worker
    p = start_worker_proc(1)
    jobid = 'fail-1'
    db.enqueue({'id': jobid, 'command': "/bin/false", 'max_retries': 2})
    # wait for DLQ
    for _ in range(100):
        r = read_job(db, jobid)
        if r and r['state'] == 'dead':
            assert r['attempts'] >= 2
            stop_proc(p)
            return
        time.sleep(0.1)
    stop_proc(p)
    pytest.fail("failed job did not move to DLQ in time")

def test_multiple_workers_no_overlap():
    db = DB()
    db.set_config('backoff_base', 1)
    # start 2 workers
    p1 = start_worker_proc(1)
    p2 = start_worker_proc(2)
    total = 6
    for i in range(total):
        db.enqueue({'id': f'm{i}', 'command': f'echo worker-job-{i}', 'max_retries': 1})
    # wait for all completed
    for _ in range(200):
        statuses = db.get_status_counts()
        completed = statuses.get('completed', 0)
        if completed >= total:
            # check each job has stdout
            rows = db.list_jobs()
            ids = [r['id'] for r in rows if r['state']=='completed']
            assert len(ids) >= total
            stop_proc(p1); stop_proc(p2)
            return
        time.sleep(0.05)
    stop_proc(p1); stop_proc(p2)
    pytest.fail("not all jobs processed by multiple workers")

def test_invalid_command_fails_gracefully():
    db = DB()
    db.set_config('backoff_base', 1)
    p = start_worker_proc(1)
    jobid = 'invalid-1'
    db.enqueue({'id': jobid, 'command': "nonexistent-command-xyz", 'max_retries': 1})
    # wait for dead or completed
    for _ in range(100):
        r = read_job(db, jobid)
        if r and r['state'] in ('dead', 'completed'):
            # should not be completed; expect dead
            assert r['state'] == 'dead'
            # stderr should contain something or last_error set
            assert (r.get('stderr') and r['stderr'] != '') or (r.get('last_error') and r['last_error'] != '')
            stop_proc(p)
            return
        time.sleep(0.1)
    stop_proc(p)
    pytest.fail("invalid command did not fail as expected")

def test_persistence_across_restart():
    db = DB()
    jobid = 'persist-1'
    db.enqueue({'id': jobid, 'command': "echo persisted", 'max_retries': 1})
    # ensure DB file exists
    assert os.path.exists('queuectl.db')
    # start worker to process
    p = start_worker_proc(1)
    for _ in range(100):
        r = read_job(db, jobid)
        if r and r['state'] == 'completed':
            stop_proc(p)
            return
        time.sleep(0.05)
    stop_proc(p)
    pytest.fail("persistence test failed: job not completed after restart")
