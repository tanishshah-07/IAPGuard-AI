import sqlite3
from app import db

def test_existing_transaction_table_migrates_backward_compatibly(tmp_path, monkeypatch):
    data_dir=tmp_path/'data'; data_dir.mkdir(); database=data_dir/'iapguard.sqlite3'
    conn=sqlite3.connect(database)
    conn.execute('''CREATE TABLE transactions (
        id TEXT PRIMARY KEY,user_id TEXT NOT NULL,timestamp TEXT NOT NULL,amount REAL NOT NULL,
        hour INTEGER NOT NULL,account_age_days INTEGER NOT NULL,purchases_24h INTEGER NOT NULL,
        failed_attempts_24h INTEGER NOT NULL,payment_methods_7d INTEGER NOT NULL,
        device_changes_7d INTEGER NOT NULL,country_mismatch INTEGER NOT NULL,purchase_type TEXT NOT NULL,
        anomaly_score REAL,risk_level TEXT NOT NULL DEFAULT 'unscored',status TEXT NOT NULL DEFAULT 'pending',
        is_synthetic_fraud INTEGER,source TEXT NOT NULL DEFAULT 'demo')''')
    conn.execute("INSERT INTO transactions(id,user_id,timestamp,amount,hour,account_age_days,purchases_24h,failed_attempts_24h,payment_methods_7d,device_changes_7d,country_mismatch,purchase_type) VALUES ('old','U','2025-01-01T00:00:00+00:00',100,0,1,2,0,1,0,0,'subscription')")
    conn.commit(); conn.close()
    monkeypatch.setattr(db,'DATA_DIR',data_dir); monkeypatch.setattr(db,'DB_PATH',database)
    db.initialize()
    with db.connect() as migrated:
        assert migrated.execute('SELECT evaluation_partition FROM transactions WHERE id="old"').fetchone()[0]=='legacy'
        indexes={row['name'] for row in migrated.execute('PRAGMA index_list(transactions)')}
        assert 'idx_transactions_user_history' in indexes
