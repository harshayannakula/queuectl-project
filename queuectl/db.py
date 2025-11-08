# queuectl/db.py
import sqlite3
import os
import json
import time
import uuid
from datetime import datetime, timezone

# DEFAULT_CONFIG stays module-level
DEFAULT_CONFIG = {'max_retries': 3, 'backoff_base': 2, 'job_timeout': 10}

def now_iso():
    return datetime.now(timezone.utc).isoformat()

class DB:
    def __init__(self, path: str = None):
        """
        If `path` is None, create a DB file named 'queuectl.db' in the current working directory.
        This avoids binding the DB path at import time so tests that change cwd work correctly.
        """
        if path:
            self.path = path
        else:
            self.path = os.path.join(os.getcwd(), 'queuectl.db')
        self._ensure_db()

    def _conn(self):
        c = sqlite3.connect(self.path, timeout=30, isolation_level=None)
        c.row_factory = sqlite3.Row
        return c

    def _ensure_db(self):
        c = self._conn()
        cur = c.cursor()
        cur.executescript('''
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            command TEXT NOT NULL,
            state TEXT NOT NULL,
            attempts INTEGER NOT NULL DEFAULT 0,
            max_retries INTEGER NOT NULL DEFAULT 3,
            created_at TEXT,
            updated_at TEXT,
            available_at REAL DEFAULT 0,
            last_error TEXT,
            stdout TEXT,
            stderr TEXT,
            duration REAL,
            timed_out INTEGER DEFAULT 0,
            timeout INTEGER DEFAULT 0
        );
        CREATE INDEX IF NOT EXISTS idx_state_available ON jobs(state, available_at);
        CREATE TABLE IF NOT EXISTS config (
            key TEXT PRIMARY KEY,
            value TEXT
        );
        ''')

        # Migrate older DB by adding missing columns if necessary
        add_cols = {
            'stdout': 'TEXT',
            'stderr': 'TEXT',
            'duration': 'REAL',
            'timed_out': 'INTEGER DEFAULT 0',
            'timeout': 'INTEGER DEFAULT 0'
        }
        cur.execute("PRAGMA table_info(jobs)")
        existing = {r['name'] for r in cur.fetchall()}
        for col, typ in add_cols.items():
            if col not in existing:
                try:
                    cur.execute(f'ALTER TABLE jobs ADD COLUMN {col} {typ}')
                except Exception:
                    # ignore migration errors (best-effort)
                    pass

        for k, v in DEFAULT_CONFIG.items():
            cur.execute('INSERT OR IGNORE INTO config(key,value) VALUES(?,?)', (k, json.dumps(v)))
        c.commit()
        c.close()

    def enqueue(self, job):
        c = self._conn()
        cur = c.cursor()
        job_id = job.get('id') or str(uuid.uuid4())
        command = job['command']
        max_retries = job.get('max_retries', DEFAULT_CONFIG['max_retries'])
        created_at = job.get('created_at', now_iso())
        updated_at = created_at
        state = 'pending'
        available_at = 0
        timeout = job.get('timeout', 0)
        cur.execute('''INSERT INTO jobs(id,command,state,attempts,max_retries,created_at,updated_at,available_at,timeout) VALUES(?,?,?,?,?,?,?,?,?)''',
                    (job_id, command, state, 0, max_retries, created_at, updated_at, available_at, timeout))
        c.commit()
        c.close()
        return job_id

    def fetch_and_claim_job(self):
        c = self._conn()
        cur = c.cursor()
        now_ts = time.time()
        try:
            cur.execute('BEGIN IMMEDIATE')
            cur.execute('SELECT * FROM jobs WHERE state = ? AND available_at <= ? ORDER BY created_at LIMIT 1', ('pending', now_ts))
            row = cur.fetchone()
            if not row:
                cur.execute('COMMIT')
                return None
            job_id = row['id']
            cur.execute('UPDATE jobs SET state = ?, updated_at = ? WHERE id = ? AND state = ?', ('processing', now_iso(), job_id, 'pending'))
            if cur.rowcount == 0:
                cur.execute('COMMIT')
                return None
            cur.execute('SELECT * FROM jobs WHERE id = ?', (job_id,))
            job = cur.fetchone()
            cur.execute('COMMIT')
            return dict(job)
        except sqlite3.OperationalError:
            try:
                cur.execute('ROLLBACK')
            except Exception:
                pass
            return None
        finally:
            c.close()

    def update_job_after_run(self, job_id, success, attempts, max_retries, error_msg=None, next_available_delay=0, stdout=None, stderr=None, duration=None, timed_out=False):
        c = self._conn()
        cur = c.cursor()
        updated = now_iso()
        if success:
            cur.execute('UPDATE jobs SET state = ?, attempts = ?, updated_at = ?, last_error = NULL, stdout = ?, stderr = ?, duration = ?, timed_out = ? WHERE id = ?', ('completed', attempts, updated, stdout, stderr, duration, int(bool(timed_out)), job_id))
        else:
            if attempts >= max_retries:
                cur.execute('UPDATE jobs SET state = ?, attempts = ?, updated_at = ?, last_error = ?, stdout = ?, stderr = ?, duration = ?, timed_out = ? WHERE id = ?', ('dead', attempts, updated, error_msg, stdout, stderr, duration, int(bool(timed_out)), job_id))
            else:
                next_avail = time.time() + next_available_delay
                cur.execute('UPDATE jobs SET state = ?, attempts = ?, updated_at = ?, available_at = ?, last_error = ?, stdout = ?, stderr = ?, duration = ?, timed_out = ? WHERE id = ?', ('pending', attempts, updated, next_avail, error_msg, stdout, stderr, duration, int(bool(timed_out)), job_id))
        c.commit()
        c.close()

    def get_status_counts(self):
        c = self._conn()
        cur = c.cursor()
        cur.execute("SELECT state, COUNT(*) as cnt FROM jobs GROUP BY state")
        rows = cur.fetchall()
        c.close()
        return {r['state']: r['cnt'] for r in rows}

    def list_jobs(self, state=None):
        c = self._conn()
        cur = c.cursor()
        if state:
            cur.execute('SELECT * FROM jobs WHERE state = ? ORDER BY created_at', (state,))
        else:
            cur.execute('SELECT * FROM jobs ORDER BY created_at')
        rows = cur.fetchall()
        c.close()
        return [dict(r) for r in rows]

    def dlq_retry(self, job_id):
        c = self._conn()
        cur = c.cursor()
        cur.execute('SELECT * FROM jobs WHERE id = ? AND state = ?', (job_id, 'dead'))
        row = cur.fetchone()
        if not row:
            c.close()
            return False, 'not found or not dead'
        cur.execute('UPDATE jobs SET state = ?, attempts = ?, available_at = ?, updated_at = ?, last_error = NULL WHERE id = ?', ('pending', 0, 0, now_iso(), job_id))
        c.commit()
        c.close()
        return True, None

    def set_config(self, key, value):
        c = self._conn()
        cur = c.cursor()
        cur.execute('INSERT OR REPLACE INTO config(key,value) VALUES(?,?)', (key, json.dumps(value)))
        c.commit()
        c.close()

    def get_config(self, key):
        c = self._conn()
        cur = c.cursor()
        cur.execute('SELECT value FROM config WHERE key = ?', (key,))
        row = cur.fetchone()
        c.close()
        if not row:
            return None
        return json.loads(row['value'])
