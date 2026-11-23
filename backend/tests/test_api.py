import os
import tempfile

os.environ['IAPGUARD_DATA_DIR'] = tempfile.mkdtemp(prefix='iapguard-test-')
from fastapi.testclient import TestClient
from app.main import app

def test_end_to_end():
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
        assert client.post('/api/demo/reset').json()['count'] == 1200
        assert client.get(transaction_url).json()['review'] is None
    with TestClient(app) as client:
        assert client.get('/api/health').json()['model_ready']
        assert client.get('/api/overview').json()['total_transactions'] == 1200
