"""Reproducible synthetic transactions with persistent per-user behavior."""
from datetime import datetime, timedelta, timezone
import numpy as np

TYPES=('subscription','workout','coaching')

def generate(count=1200, fraud_rate=.12, seed=27):
    rng=np.random.default_rng(seed); now=datetime.now(timezone.utc).replace(minute=0,second=0,microsecond=0)
    user_count=max(40,min(120,count//12)); users=[]
    for index in range(user_count):
        users.append({'id':f'USR-{1000+index:04d}',
            'amount':float(rng.choice([199,399,499,799,999,1499,2499]))*rng.uniform(.92,1.08),
            'gap':int(rng.choice([1,2,3,5,7,10,14],p=[.08,.12,.15,.2,.2,.15,.1])),
            'category':str(rng.choice(TYPES,p=[.62,.28,.10]))})
    events=[]
    for i in range(count):
        user=users[i % user_count]
        # Each user has a stable cadence with modest jitter; hour is encoded in timestamp.
        day_offset=int((i//user_count)*max(1,user['gap']) + rng.integers(0,2))
        hour=int(np.clip(rng.normal(14,3),0,23))
        if hour > now.hour: day_offset += 1
        stamp=(now.replace(hour=hour)-timedelta(days=day_offset)).replace(minute=int(rng.integers(0,60)))
        amount=round(user['amount']*rng.uniform(.88,1.12),2)
        purchase_type=user['category'] if rng.random()<.82 else str(rng.choice(TYPES))
        fraud=bool(rng.random()<fraud_rate)
        if fraud:
            attack=int(rng.integers(0,3))
            if attack==0: amount=round(user['amount']*rng.uniform(4,12),2)
            elif attack==1: purchase_type=str(rng.choice([x for x in TYPES if x!=user['category']]))
            else: amount=round(float(rng.uniform(8000,30000)),2)
        events.append({'id':f'TXN-{seed:02d}-{i+1:05d}','user_id':user['id'],
            'timestamp':stamp.isoformat(timespec='seconds'),'amount':amount,
            'hour':stamp.hour,'account_age_days':int(rng.integers(30,1400)),
            # Legacy columns remain for API/database compatibility; these are not model features.
            'purchases_24h':0,'failed_attempts_24h':int(rng.choice([0,0,0,1])),
            'payment_methods_7d':1,'device_changes_7d':0,'country_mismatch':int(rng.random()<.01),
            'purchase_type':purchase_type,'anomaly_score':None,'risk_level':'unscored',
            'status':'pending','is_synthetic_fraud':int(fraud),'source':'demo'})
    events.sort(key=lambda row:(row['timestamp'],row['id']))
    return events
