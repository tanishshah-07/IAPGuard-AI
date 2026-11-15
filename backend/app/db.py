"""SQLite persistence with parameterized queries and local project data directory."""
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

DATA_DIR = Path(os.getenv('IAPGUARD_DATA_DIR', str(Path(__file__).resolve().parents[1] / 'data')))
DB_PATH = DATA_DIR / 'iapguard.sqlite3'

@contextmanager
def connect():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def initialize():
    with connect() as db:
        db.executescript('''
        CREATE TABLE IF NOT EXISTS transactions (
          id TEXT PRIMARY KEY, user_id TEXT NOT NULL, timestamp TEXT NOT NULL,
          amount REAL NOT NULL, hour INTEGER NOT NULL, account_age_days INTEGER NOT NULL,
          purchases_24h INTEGER NOT NULL, failed_attempts_24h INTEGER NOT NULL,
          payment_methods_7d INTEGER NOT NULL, device_changes_7d INTEGER NOT NULL,
          country_mismatch INTEGER NOT NULL, purchase_type TEXT NOT NULL,
          anomaly_score REAL, risk_level TEXT NOT NULL DEFAULT 'unscored',
          status TEXT NOT NULL DEFAULT 'pending', is_synthetic_fraud INTEGER,
          source TEXT NOT NULL DEFAULT 'demo'
        );
        CREATE INDEX IF NOT EXISTS idx_transactions_timestamp ON transactions(timestamp DESC);
        CREATE INDEX IF NOT EXISTS idx_transactions_risk ON transactions(risk_level);
        CREATE TABLE IF NOT EXISTS reviews (
          transaction_id TEXT PRIMARY KEY REFERENCES transactions(id),
          resolution TEXT NOT NULL, note TEXT NOT NULL DEFAULT '', reviewed_at TEXT NOT NULL
        );
        ''')

COLUMNS = ('id','user_id','timestamp','amount','hour','account_age_days','purchases_24h',
           'failed_attempts_24h','payment_methods_7d','device_changes_7d','country_mismatch',
           'purchase_type','anomaly_score','risk_level','status','is_synthetic_fraud','source')

def insert_many(records):
    if not records: return
    query = f"INSERT INTO transactions ({','.join(COLUMNS)}) VALUES ({','.join(['?']*len(COLUMNS))})"
    with connect() as db:
        db.executemany(query, [tuple(rec.get(k) for k in COLUMNS) for rec in records])

def row_to_dict(row):
    return dict(row) if row is not None else None
