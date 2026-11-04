"""Durable, conservative reservations for Pico's explicitly enabled model calls."""
import os
import sqlite3
import time
from pathlib import Path

class BudgetDenied(Exception): pass

def limit(name, default):
    # Owner-set ceilings. Defaults stay the original $1/day, $5 total, 2/minute.
    try:return max(0.0,float(os.environ.get(name,default)))
    except ValueError:return float(default)

class ModelBudget:
    # Each bounded text-only request reserves $0.10, including failed calls.
    # These reservations are deliberately higher than expected token charges.
    RESERVATION = 100000  # USD millionths
    def __init__(self, path, trial=False):
        self.trial=trial
        self.path=str(path)
        Path(path).parent.mkdir(parents=True,exist_ok=True)
        with self.connect() as db:
            db.execute('create table if not exists model_calls (id text primary key, owner text, at real, reserved integer)')
            db.execute('create table if not exists model_active (owner text primary key, id text, at real)')
    def connect(self):return sqlite3.connect(self.path,timeout=10)
    def reserve(self, owner, request_id):
        if os.environ.get('PICO_MODEL_ENABLED')!='1':raise BudgetDenied('AI planning is off.')
        now=time.time();day=int(now//86400)*86400
        with self.connect() as db:
            db.execute('begin immediate')
            if db.execute('select 1 from model_calls where id=?',(request_id,)).fetchone():raise BudgetDenied('This request was already submitted. No automatic retry.')
            if self.trial:
                db.execute('delete from model_active where at<?',(now-180,))
                if db.execute('select 1 from model_active where owner=?',(owner,)).fetchone():raise BudgetDenied('Your Muse request is still running. Please wait.')
                count=db.execute('select count(*) from model_calls where owner=?',(owner,)).fetchone()[0]
                if count >= 5:raise BudgetDenied('Your five-request Muse trial is used up. Basic commands still work.')
                if db.execute('select count(*) from model_calls where owner=? and at>?',(owner,now-60)).fetchone()[0]:
                    raise BudgetDenied('Please wait one minute between Muse trial requests.')
            total=db.execute('select coalesce(sum(reserved),0) from model_calls').fetchone()[0]
            daily=db.execute('select coalesce(sum(reserved),0) from model_calls where at>=?',(day,)).fetchone()[0]
            recent=db.execute('select count(*) from model_calls where at>?',(now-60,)).fetchone()[0]
            # Global lifetime / UTC-day ceiling across both enabled owner accounts.
            lifetime=int((min(5,limit('PICO_TRIAL_TOTAL_USD',5)) if self.trial else limit('PICO_MODEL_TOTAL_USD',5))*1000000);per_day=lifetime if self.trial else int(limit('PICO_MODEL_DAILY_USD',1)*1000000)
            if total+self.RESERVATION>lifetime:raise BudgetDenied('Pico’s AI test budget is reached: the overall allowance is used up. Basic commands still work.')
            if daily+self.RESERVATION>per_day:raise BudgetDenied('Pico’s AI test budget is reached for today. It resets at 00:00 UTC. Basic commands still work.')
            if recent>=(10 if self.trial else limit('PICO_MODEL_PER_MINUTE',2)):raise BudgetDenied('Wait a minute before another AI request.')
            db.execute('insert into model_calls values (?,?,?,?)',(request_id,owner,now,self.RESERVATION))
            if self.trial:db.execute('insert into model_active values (?,?,?)',(owner,request_id,now))

    def remaining(self, owner):
        with self.connect() as db:
            count=db.execute('select count(*) from model_calls where owner=?',(owner,)).fetchone()[0]
            total=db.execute('select coalesce(sum(reserved),0) from model_calls').fetchone()[0]
        cap=int(min(5,limit('PICO_TRIAL_TOTAL_USD',5))*1000000)
        return max(0,5-count), total+self.RESERVATION<=cap

    def release(self, request_id):
        with self.connect() as db:db.execute('delete from model_active where id=?',(request_id,))
