import os
import tempfile

os.environ['IAPGUARD_DATA_DIR'] = tempfile.mkdtemp(prefix='iapguard-test-')
from fastapi.testclient import TestClient
from app.main import app
from app import main as main_module
from app.db import connect, insert_many
from app.model import FEATURE_NAMES, features

def test_end_to_end(monkeypatch):
    with TestClient(app) as client:
        assert client.get('/api/health').json()['model_ready']
        overview=client.get('/api/overview').json()
        assert overview['total_transactions']==1200
        txs=client.get('/api/transactions',params={'risk':'high','limit':5}).json()
        assert len(txs['items'])<=5
        sample=txs['items'][0]
        detail=client.get('/api/transactions/'+sample['id'])
        assert detail.status_code==200
        assert 'top_deviations' in detail.json()['analysis']
        response=client.post('/api/transactions/'+sample['id']+'/review',json={'resolution':'needs_review','note':'test'})
        assert response.status_code==200
        result=client.post('/api/analyze',json={'user_id':'USR-TEST','amount':12000,'hour':2,
            'account_age_days':1,'purchases_24h':27,'failed_attempts_24h':9,
            'payment_methods_7d':8,'device_changes_7d':5,'country_mismatch':True,
            'purchase_type':'subscription'})
        assert result.status_code==200
        assert set(('analysis','transaction','saved','notice')).issubset(result.json())
        assert result.json()['saved'] is False
        assert 'timestamp' in result.json()['transaction']
        assert result.json()['transaction']['hour'] == 2
        assert result.json()['analysis']['risk_level'] in ('low','medium','high')
        assert client.get('/api/evaluation').json()['available']
        assert client.get('/api/model').json()['ready']
        assert client.get('/api/transactions/DOES-NOT-EXIST').status_code==404

        transaction_url = '/api/transactions/' + sample['id']
        assert client.post('/api/model/retrain').json()['scored_transactions'] == 1200
        detail = client.get(transaction_url).json()
        assert detail['review']['note'] == 'test'
        assert detail['transaction']['anomaly_score'] == detail['analysis']['anomaly_score']

        history_rows=[]
        for tx_id,user_id,stamp in [
            ('TXN-API-PRIOR','USR-API-HISTORY-TEST','2030-01-01T10:00:00+00:00'),
            ('TXN-API-EQUAL','USR-API-HISTORY-TEST','2030-01-01T11:00:00+00:00'),
            ('TXN-API-FUTURE','USR-API-HISTORY-TEST','2030-01-01T12:00:00+00:00'),
            ('TXN-API-OTHER','USR-API-OTHER-TEST','2030-01-01T10:30:00+00:00')]:
            history_rows.append({'id':tx_id,'user_id':user_id,'timestamp':stamp,'amount':100.0,
                'hour':10,'account_age_days':100,'purchases_24h':0,'failed_attempts_24h':0,
                'payment_methods_7d':1,'device_changes_7d':0,'country_mismatch':0,
                'purchase_type':'subscription','anomaly_score':None,'risk_level':'low','status':'pending',
                'is_synthetic_fraud':None,'source':'test','evaluation_partition':'legacy'})
        with connect() as db:
            insert_many(db,history_rows)
            before=db.execute('SELECT COUNT(*) FROM transactions').fetchone()[0]

        observed={}; original_score=main_module.detector.score
        def capture_score(tx,history=()):
            if tx.get('user_id')=='USR-API-HISTORY-TEST':
                observed['tx']=dict(tx); observed['history']=[dict(row) for row in history]
                observed['features']=features(tx,history)
            return original_score(tx,history)
        monkeypatch.setattr(main_module.detector,'score',capture_score)
        analyze=client.post('/api/analyze',json={'user_id':'USR-API-HISTORY-TEST','amount':250,
            'hour':11,'account_age_days':100,'purchases_24h':55,'failed_attempts_24h':0,
            'payment_methods_7d':1,'device_changes_7d':0,'country_mismatch':False,
            'purchase_type':'subscription','timestamp':'2030-01-01T11:00:00+00:00',
            'id':'TXN-API-PRIOR'})
        assert analyze.status_code==200
        assert analyze.json()['saved'] is False
        assert set(('analysis','transaction','saved','notice')).issubset(analyze.json())
        assert 'id' not in analyze.json()['transaction']
        assert 'id' not in main_module.TransactionInput.model_fields
        assert observed['tx']['user_id']=='USR-API-HISTORY-TEST'
        assert {row['id'] for row in observed['history']}=={'TXN-API-PRIOR'}
        assert all(row['user_id']==observed['tx']['user_id'] for row in observed['history'])
        assert abs(float(observed['features'][FEATURE_NAMES.index('log_prior_transaction_count')])-0.69314718)<1e-6
        with connect() as db:
            after=db.execute('SELECT COUNT(*) FROM transactions').fetchone()[0]
            assert after==before
            assert db.execute('SELECT COUNT(*) FROM transactions WHERE id="TXN-API-UNSAVED"').fetchone()[0]==0
        assert client.post('/api/demo/reset').json()['count'] == 1200
        assert client.get(transaction_url).json()['review'] is None
    with TestClient(app) as client:
        assert client.get('/api/health').json()['model_ready']
        assert client.get('/api/overview').json()['total_transactions'] == 1200
