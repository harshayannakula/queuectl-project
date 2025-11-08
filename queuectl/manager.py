import os
import json
import signal
from multiprocessing import Process
from .worker import worker_loop

PID_FILE = os.path.join(os.getcwd(), 'queuectl_workers.pid')

class WorkerManager:
    def __init__(self):
        self.procs = []

    def start(self, count):
        for i in range(count):
            # do NOT pass multiprocessing.Event here; child creates its own stop flag
            p = Process(target=worker_loop, args=(i+1,))
            p.start()
            self.procs.append(p)
        with open(PID_FILE, 'w') as f:
            f.write(json.dumps([p.pid for p in self.procs]))
        print(f"Started {len(self.procs)} worker(s). PIDs written to {PID_FILE}")

    def stop(self):
        if not os.path.exists(PID_FILE):
            print('No PID file found; no workers appear to be running')
            return
        try:
            with open(PID_FILE, 'r') as f:
                pids = json.loads(f.read())
        except Exception:
            pids = []
        print(f"Will attempt graceful shutdown of {len(pids)} worker(s)")
        for pid in pids:
            try:
                os.kill(pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
        try:
            os.remove(PID_FILE)
        except Exception:
            pass
