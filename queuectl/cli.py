import argparse
import json
import os
from .db import DB
from .manager import WorkerManager

PID_FILE = os.path.join(os.getcwd(), 'queuectl_workers.pid')

def cmd_enqueue(args):
    db = DB()
    try:
        job = json.loads(args.job_json)
    except Exception:
        print('Invalid JSON for job')
        return
    job_id = db.enqueue(job)
    print(f'enqueued {job_id}')

def cmd_worker_start(args):
    mgr = WorkerManager()
    mgr.start(args.count)
    print('Workers started in current process. To stop from another terminal: ./bin/queuectl worker stop')

def cmd_worker_stop(args):
    mgr = WorkerManager()
    mgr.stop()
    print('Stop signal sent to workers (they will exit after current job)')

def cmd_status(args):
    db = DB()
    counts = db.get_status_counts()
    print('Job counts by state:')
    for s in ('pending','processing','completed','failed','dead'):
        print(f'  {s}: {counts.get(s,0)}')
    if os.path.exists(PID_FILE):
        try:
            pids = json.loads(open(PID_FILE).read())
            live = []
            for pid in pids:
                try:
                    os.kill(pid, 0)
                    live.append(pid)
                except Exception:
                    pass
            print(f'Active worker pids: {live}')
        except Exception:
            print('Active worker pids: (error reading pid file)')
    else:
        print('Active worker pids: none')

def cmd_list(args):
    db = DB()
    rows = db.list_jobs(state=args.state)
    for r in rows:
        print(json.dumps(r))

def cmd_dlq_list(args):
    db = DB()
    rows = db.list_jobs(state='dead')
    for r in rows:
        print(json.dumps(r))

def cmd_dlq_retry(args):
    db = DB()
    ok, msg = db.dlq_retry(args.job_id)
    if ok:
        print('job moved back to pending')
    else:
        print('error:', msg)

def cmd_config_set(args):
    db = DB()
    key = args.key
    val = args.value
    try:
        parsed = json.loads(val)
    except Exception:
        parsed = val
    db.set_config(key, parsed)
    print('config set')

def cmd_config_get(args):
    db = DB()
    val = db.get_config(args.key)
    print(json.dumps(val, indent=2))

def main():
    parser = argparse.ArgumentParser(prog='queuectl')
    sub = parser.add_subparsers(dest='cmd')

    e = sub.add_parser('enqueue')
    e.add_argument('job_json')
    e.set_defaults(func=cmd_enqueue)

    w = sub.add_parser('worker')
    wsub = w.add_subparsers(dest='op')
    wstart = wsub.add_parser('start')
    wstart.add_argument('--count', type=int, default=1)
    wstart.set_defaults(func=cmd_worker_start)
    wstop = wsub.add_parser('stop')
    wstop.set_defaults(func=cmd_worker_stop)

    s = sub.add_parser('status')
    s.set_defaults(func=cmd_status)

    l = sub.add_parser('list')
    l.add_argument('--state', default=None)
    l.set_defaults(func=cmd_list)

    d = sub.add_parser('dlq')
    dsub = d.add_subparsers(dest='op')
    dlist = dsub.add_parser('list')
    dlist.set_defaults(func=cmd_dlq_list)
    dretry = dsub.add_parser('retry')
    dretry.add_argument('job_id')
    dretry.set_defaults(func=cmd_dlq_retry)

    c = sub.add_parser('config')
    csub = c.add_subparsers(dest='op')
    cset = csub.add_parser('set')
    cset.add_argument('key')
    cset.add_argument('value')
    cset.set_defaults(func=cmd_config_set)
    cget = csub.add_parser('get')
    cget.add_argument('key')
    cget.set_defaults(func=cmd_config_get)

    args = parser.parse_args()
    if not hasattr(args, 'func'):
        parser.print_help()
        return
    args.func(args)
