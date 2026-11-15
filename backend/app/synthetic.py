"""Reproducible illustrative synthetic fitness-app transaction behavior."""
from datetime import datetime, timedelta, timezone
import numpy as np

TYPES = ('subscription','workout','coaching')

def generate(count=1200, fraud_rate=0.12, seed=27):
    rng = np.random.default_rng(seed)
    now = datetime.now(timezone.utc)
    records = []
    for i in range(count):
        fraud = bool(rng.random() < fraud_rate)
        purchase_type = str(rng.choice(TYPES, p=[0.56,0.31,0.13]))
        amount = round(float(rng.choice([199,399,499,799,999,1499,2499]) * rng.uniform(.85,1.15)),2)
        account_age = int(rng.integers(30,1400))
        purchases = int(rng.choice([1,2,3,4,5],p=[.40,.35,.15,.07,.03]))
        failures = int(rng.choice([0,1,2],p=[.87,.11,.02]))
        methods = int(rng.choice([1,2,3],p=[.76,.21,.03]))
        devices = int(rng.choice([0,1,2],p=[.85,.13,.02]))
        mismatch = int(rng.random()<.025)
        hour = int(np.clip(rng.normal(15,5),0,23))
        if fraud:
            attack = int(rng.integers(0,4))
            if attack == 0:
                purchases=int(rng.integers(15,60));failures=int(rng.integers(4,18))
            elif attack == 1:
                amount=round(float(rng.uniform(8000,55000)),2);account_age=int(rng.integers(0,10))
            elif attack == 2:
                methods=int(rng.integers(5,12));devices=int(rng.integers(4,10));mismatch=1
            else:
                hour=int(rng.integers(0,5));purchases=int(rng.integers(9,24));account_age=int(rng.integers(0,20))
        stamp = now - timedelta(minutes=int(rng.integers(0,60*24*28)))
        records.append({'id':f'TXN-{seed:02d}-{i+1:05d}', 'user_id':f'USR-{int(rng.integers(1000,1600)):04d}',
            'timestamp':stamp.isoformat(timespec='seconds'), 'amount':amount,'hour':hour,
            'account_age_days':account_age,'purchases_24h':purchases,
            'failed_attempts_24h':failures,'payment_methods_7d':methods,'device_changes_7d':devices,
            'country_mismatch':mismatch,'purchase_type':purchase_type,'anomaly_score':None,
            'risk_level':'unscored','status':'pending','is_synthetic_fraud':int(fraud),'source':'demo'})
    return records
