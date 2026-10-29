"""Local relay metadata: pairing lockouts and short-lived delivery receipts."""
import hashlib
import sqlite3
import time
from pathlib import Path


class RelayState:
    def __init__(self, path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.path = str(path)
        with self.connect() as db:
            db.execute('create table if not exists attempts (address text primary key, count integer, until real)')
            db.execute('create table if not exists receipts (id text primary key, owner text, expires real)')

    def connect(self):
        return sqlite3.connect(self.path, timeout=10)

    def ping(self):
        """Prove the state database is writable; leaves no residue."""
        with self.connect() as db:
            db.execute('insert into attempts values (?,?,?) on conflict(address) do nothing',
                       ('__ping__', 0, 0.0))
            db.execute('delete from attempts where address=?', ('__ping__',))

    def blocked(self, address):
        key = hashlib.sha256(address.encode()).hexdigest()
        with self.connect() as db:
            row = db.execute('select count, until from attempts where address=?', (key,)).fetchone()
            if row and row[1] <= time.time():
                db.execute('delete from attempts where address=?', (key,))
                return False
            return bool(row and row[0] >= 5)

    def attempt(self, address, success=False):
        key = hashlib.sha256(address.encode()).hexdigest()
        with self.connect() as db:
            if success:
                db.execute('delete from attempts where address=?', (key,))
            else:
                db.execute('insert into attempts values (?,1,?) on conflict(address) do update set count=count+1, until=excluded.until', (key, time.time()+600))

    def delivered(self, owner, id):
        with self.connect() as db:
            db.execute('delete from receipts where expires < ?', (time.time(),))
            db.execute('insert or replace into receipts values (?,?,?)', (id, owner, time.time()+86400))

    def received(self, owner, id):
        with self.connect() as db:
            return db.execute('select 1 from receipts where owner=? and id=? and expires>?', (owner, id, time.time())).fetchone() is not None
