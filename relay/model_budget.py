"""Durable, conservative reservations for Pico's explicitly enabled model calls."""
import os
import sqlite3
import time
from pathlib import Path

class BudgetDenied(Exception): pass

class ModelBudget:
    # Each bounded text-only request reserves $0.10, including failed calls.
    # These reservations are deliberately higher than expected token charges.
    RESERVATION = 100000  # USD millionths
    def __init__(self, path):
        self.path=str(path)
        Path(path).parent.mkdir(parents=True,exist_ok=True)
        with self.connect() as db:
            db.execute('create table if not exists model_calls (id text primary key, owner text, at real, reserved integer)')
    def connect(self):return sqlite3.connect(self.path,timeout=10)
    def reserve(self, owner, request_id):
        if os.environ.get('PICO_MODEL_ENABLED')!='1':raise BudgetDenied('AI planning is off.')
        now=time.time();day=int(now//86400)*86400
        with self.connect() as db:
            db.execute('begin immediate')
            if db.execute('select 1 from model_calls where id=?',(request_id,)).fetchone():raise BudgetDenied('This request was already submitted. No automatic retry.')
            total=db.execute('select coalesce(sum(reserved),0) from model_calls').fetchone()[0]
            daily=db.execute('select coalesce(sum(reserved),0) from model_calls where at>=?',(day,)).fetchone()[0]
            recent=db.execute('select count(*) from model_calls where at>?',(now-60,)).fetchone()[0]
            # Global $5 lifetime / $1 UTC-day ceiling across both enabled owner accounts.
            if total+self.RESERVATION>5000000 or daily+self.RESERVATION>1000000:raise BudgetDenied('Pico’s AI test budget is reached. Basic commands still work.')
            if recent>=2:raise BudgetDenied('Wait a minute before another AI request.')
            db.execute('insert into model_calls values (?,?,?,?)',(request_id,owner,now,self.RESERVATION))
