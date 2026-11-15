"""IAPGuard AI FastAPI service. Demo-only: no auth or payment integration."""
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from threading import Lock
import sqlite3
from typing import Literal
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from .db import connect, initialize, insert_many, row_to_dict
from .model import Detector
from .synthetic import generate

model_lock = Lock()
detector = None

class TransactionInput(BaseModel):
    user_id: str = Field(min_length=2,max_length=60)
    amount: float = Field(gt=0,le=10000000)
    hour: int = Field(ge=0,le=23)
    account_age_days: int = Field(ge=0,le=100000)
    purchases_24h: int = Field(ge=0,le=10000)
    failed_attempts_24h: int = Field(ge=0,le=10000)
    payment_methods_7d: int = Field(ge=1,le=10000)
    device_changes_7d: int = Field(ge=0,le=10000)
    country_mismatch: bool = False
    purchase_type: Literal['subscription','workout','coaching'] = 'subscription'

class ReviewInput(BaseModel):
    resolution: Literal['confirmed_fraud','legitimate','needs_review']
    note: str = Field(default='', max_length=500)

def rescore_all():
    with model_lock:
        with connect() as db:
            rows = db.execute('SELECT * FROM transactions').fetchall()
            updates = []
            for row in rows:
                prediction = detector.score(dict(row))
                updates.append((prediction['anomaly_score'],prediction['risk_level'],row['id']))
            db.executemany('UPDATE transactions SET anomaly_score=?,risk_level=? WHERE id=?',updates)
    return len(updates)

def seed_demo(reset=False):
    with connect() as db:
        count = db.execute('SELECT COUNT(*) FROM transactions').fetchone()[0]
        if count and not reset:
            return {'message':'Existing transactions preserved','count':count}
        if reset:
            db.execute('DELETE FROM reviews'); db.execute('DELETE FROM transactions')
    # Training uses a separate, independently seeded normal-only sample.
    # Evaluation uses a different synthetic sample containing labeled injected patterns.
    with model_lock:
        detector.train(generate(count=1500, fraud_rate=0, seed=101),epochs=24)
    insert_many(generate(count=1200, fraud_rate=.12, seed=27))
    scored = rescore_all()
    return {'message':'Synthetic demo data seeded and VAE trained', 'count':scored}

@asynccontextmanager
async def lifespan(app):
    global detector
    initialize()
    detector = Detector()
    with connect() as db:
        count = db.execute('SELECT COUNT(*) FROM transactions').fetchone()[0]
    if not count:
        seed_demo()
    elif not detector.ready:
        with model_lock: detector.train(generate(count=1500,fraud_rate=0,seed=101),epochs=24)
        rescore_all()
    yield

app = FastAPI(title='IAPGuard AI',version='1.0.0',lifespan=lifespan,
              description='Unsupervised VAE anomaly detection on synthetic fitness in-app purchases.')
app.add_middleware(CORSMiddleware, allow_origins=['http://localhost:5173','http://127.0.0.1:5173'],
                   allow_credentials=False,allow_methods=['GET','POST'],allow_headers=['*'])

@app.get('/api/health')
def health():
    return {'status':'ok','model_ready':bool(detector and detector.ready),'demo_mode':True}

@app.get('/api/overview')
def overview():
    with connect() as db:
        total=db.execute('SELECT COUNT(*) FROM transactions').fetchone()[0]
        high=db.execute("SELECT COUNT(*) FROM transactions WHERE risk_level='high'").fetchone()[0]
        medium=db.execute("SELECT COUNT(*) FROM transactions WHERE risk_level='medium'").fetchone()[0]
        revenue=db.execute('SELECT COALESCE(SUM(amount),0) FROM transactions').fetchone()[0]
        reviewed=db.execute('SELECT COUNT(*) FROM reviews').fetchone()[0]
        daily=db.execute('''SELECT substr(timestamp,1,10) AS day,COUNT(*) AS total,
                  SUM(CASE WHEN risk_level='high' THEN 1 ELSE 0 END) AS flagged
                  FROM transactions GROUP BY day ORDER BY day''').fetchall()
        categories=db.execute('''SELECT purchase_type, COUNT(*) AS total FROM transactions
                                 GROUP BY purchase_type ORDER BY total DESC''').fetchall()
        recent=db.execute('SELECT * FROM transactions ORDER BY timestamp DESC LIMIT 7').fetchall()
    return {'total_transactions':total,'high_risk':high,'medium_risk':medium,
            'low_risk':total-high-medium,'transaction_volume':round(revenue,2),'reviewed':reviewed,
            'daily':[dict(x) for x in daily], 'categories':[dict(x) for x in categories],
            'recent':[dict(x) for x in recent], 'demo_mode':True}

@app.get('/api/transactions')
def transactions(page:int=Query(1,ge=1),limit:int=Query(15,ge=1,le=100),
                 risk:Literal['all','low','medium','high']='all',search:str=Query('',max_length=80)):
    where=[];params=[]
    if risk!='all': where.append('risk_level=?');params.append(risk)
    if search:
        where.append('(id LIKE ? OR user_id LIKE ?)')
        params.extend([f'%{search}%',f'%{search}%'])
    clause='WHERE '+' AND '.join(where) if where else ''
    with connect() as db:
        total=db.execute(f'SELECT COUNT(*) FROM transactions {clause}',params).fetchone()[0]
        rows=db.execute(f'SELECT * FROM transactions {clause} ORDER BY timestamp DESC LIMIT ? OFFSET ?',
                        [*params,limit,(page-1)*limit]).fetchall()
    return {'items':[dict(r) for r in rows],'total':total,'page':page,'limit':limit}

@app.get('/api/transactions/{transaction_id}')
def transaction_detail(transaction_id:str):
    with connect() as db:
        row=db.execute('SELECT * FROM transactions WHERE id=?',(transaction_id,)).fetchone()
        review=db.execute('SELECT * FROM reviews WHERE transaction_id=?',(transaction_id,)).fetchone()
    if not row: raise HTTPException(404,'Transaction not found')
    with model_lock: prediction=detector.score(dict(row))
    return {'transaction':dict(row),'analysis':prediction,'review':row_to_dict(review)}

@app.post('/api/analyze')
def analyze(payload:TransactionInput):
    tx=payload.model_dump();tx['country_mismatch']=int(tx['country_mismatch'])
    with model_lock: prediction=detector.score(tx)
    return {'analysis':prediction,'transaction':tx,'saved':False,
            'notice':'Scoring does not charge a payment or save the transaction.'}

@app.post('/api/transactions/{transaction_id}/review')
def review_transaction(transaction_id:str,payload:ReviewInput):
    with connect() as db:
        row=db.execute('SELECT id FROM transactions WHERE id=?',(transaction_id,)).fetchone()
        if not row: raise HTTPException(404,'Transaction not found')
        now=datetime.now(timezone.utc).isoformat(timespec='seconds')
        db.execute('''INSERT INTO reviews (transaction_id,resolution,note,reviewed_at) VALUES (?,?,?,?)
           ON CONFLICT(transaction_id) DO UPDATE SET resolution=excluded.resolution,
           note=excluded.note,reviewed_at=excluded.reviewed_at''',
           (transaction_id,payload.resolution,payload.note,now))
        db.execute("UPDATE transactions SET status='reviewed' WHERE id=?",(transaction_id,))
    return {'message':'Review saved','transaction_id':transaction_id,'resolution':payload.resolution}

@app.get('/api/model')
def model_info():
    return {'name':'Variational Autoencoder','ready':detector.ready,
            'training':detector.training_info,'thresholds':detector.thresholds,
            'notes':['Scores indicate anomalies, not confirmed fraud.',
                     'Training and evaluation records are synthetic.',
                     'Feature deviations are descriptive, not causal explanations.']}

@app.post('/api/model/retrain')
def retrain():
    with model_lock: info=detector.train(generate(count=1500,fraud_rate=0,seed=101),epochs=24)
    total=rescore_all()
    return {'message':'Model retrained and transactions rescored','scored_transactions':total,'training':info}

@app.post('/api/demo/reset')
def reset_demo():
    return seed_demo(reset=True)

@app.get('/api/evaluation')
def evaluation():
    """Illustrative label-based metrics. Not real-world fraud efficacy."""
    with connect() as db:
        rows=db.execute('SELECT risk_level,is_synthetic_fraud FROM transactions WHERE is_synthetic_fraud IS NOT NULL').fetchall()
    if not rows: return {'available':False}
    tp=sum(r['risk_level']=='high' and r['is_synthetic_fraud']==1 for r in rows)
    fp=sum(r['risk_level']=='high' and r['is_synthetic_fraud']==0 for r in rows)
    fn=sum(r['risk_level']!='high' and r['is_synthetic_fraud']==1 for r in rows)
    tn=sum(r['risk_level']!='high' and r['is_synthetic_fraud']==0 for r in rows)
    precision=tp/(tp+fp) if tp+fp else 0
    recall=tp/(tp+fn) if tp+fn else 0
    return {'available':True,'precision':round(precision,4),'recall':round(recall,4),
            'f1':round(2*precision*recall/(precision+recall),4) if precision+recall else 0,
            'false_positive_rate':round(fp/(fp+tn),4) if fp+tn else 0,
            'confusion':{'tp':tp,'fp':fp,'tn':tn,'fn':fn},
            'note':'Synthetic injected anomalies only. These metrics do not establish production fraud-detection performance.'}
