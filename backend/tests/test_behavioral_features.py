from datetime import datetime, timedelta, timezone
import sqlite3
import numpy as np
from app.model import FEATURE_NAMES, Detector, feature_matrix, features
from app.main import chronological_partitions, rescore_all
from app.synthetic import generate

BASE=datetime(2025,1,1,tzinfo=timezone.utc)
def tx(identifier, minutes, *, user='U1', amount=100, category='subscription', label=0):
    stamp=BASE+timedelta(minutes=minutes)
    return {'id':identifier,'user_id':user,'timestamp':stamp.isoformat(),'hour':stamp.hour,
        'amount':amount,'account_age_days':100,'purchases_24h':999,'failed_attempts_24h':0,
        'payment_methods_7d':1,'device_changes_7d':0,'country_mismatch':0,
        'purchase_type':category,'is_synthetic_fraud':label}

def test_history_math_windows_and_category():
    history=[tx('a',-10080,amount=100),tx('b',-60,amount=300,category='workout'),tx('c',-30,amount=200)]
    target=tx('target',0,amount=400,category='subscription')
    vector=features(target,history); values=dict(zip(FEATURE_NAMES,vector))
    assert np.isclose(values['log_prior_transaction_count'],np.log1p(3))
    assert np.isclose(values['log_historical_average_amount'],np.log1p(200))
    assert np.isclose(values['log_historical_amount_std'],np.log1p(np.std([100,300,200],ddof=0)))
    assert np.isclose(values['relative_amount_deviation'],1.0)
    assert np.isclose(values['log_seconds_since_previous'],np.log1p(1800))
    assert np.isclose(values['log_prior_count_1h'],np.log1p(2))
    assert np.isclose(values['log_prior_count_24h'],np.log1p(2))
    assert np.isclose(values['log_prior_count_7d'],np.log1p(3))
    assert values['category_differs_from_history']==0  # subscription wins the tie-break

def test_cold_start_zero_variance_and_finite():
    target=tx('now',1,user='new',amount=250)
    result=features(target,[]); v=dict(zip(FEATURE_NAMES,result))
    assert np.isfinite(result).all()
    assert v['log_prior_transaction_count']==0 and v['log_historical_amount_std']==0
    assert v['relative_amount_deviation']==0 and v['log_seconds_since_previous']==0
    prior=[tx('old',0,amount=100)]
    same=dict(zip(FEATURE_NAMES,features(tx('next',1,amount=150),prior)))
    assert same['log_historical_amount_std']==0
    assert same['relative_amount_deviation']==.5

def test_equal_timestamps_future_and_self_excluded():
    target=tx('m',10,amount=200)
    history=[tx('a',9,amount=100),tx('same',10,amount=999),tx('future',11,amount=888),target]
    v=dict(zip(FEATURE_NAMES,features(target,history)))
    assert np.isclose(v['log_prior_transaction_count'],np.log1p(1))
    assert np.isclose(v['log_historical_average_amount'],np.log1p(100))

def test_feature_matrix_is_chronological_and_labels_are_not_features():
    rows=[tx('later',2,amount=200,label=1),tx('early',1,amount=100,label=0)]
    matrix=feature_matrix(rows)
    assert matrix.shape==(2,len(FEATURE_NAMES))
    assert matrix[0,FEATURE_NAMES.index('log_prior_transaction_count')]==0
    # Flipping labels alone cannot alter engineered features.
    flipped=[dict(row,is_synthetic_fraud=1-row['is_synthetic_fraud']) for row in rows]
    assert np.array_equal(matrix,feature_matrix(flipped))

def test_training_uses_normal_fit_and_calibration_rows_and_api_feature_parity(monkeypatch):
    train=[tx(f't{i}',i*60,amount=100+i%5) for i in range(120)]
    train.append(tx('train-fraud',120*60,label=1))
    calibration=[tx(f'c{i}',(121+i)*60,amount=101+i%5,label=int(i%7==0)) for i in range(35)]
    expected_fit=feature_matrix(train)[:120]
    expected_calibration=feature_matrix(calibration,history=train)[
        [i for i,row in enumerate(calibration) if not row['is_synthetic_fraud']]]
    detector=Detector(load_existing=False)
    calibration_score_inputs=[]; original_raw_scores=detector.raw_scores
    def capture_calibration(matrix):
        calibration_score_inputs.append(matrix.copy())
        return original_raw_scores(matrix)
    monkeypatch.setattr(detector,'raw_scores',capture_calibration)
    info=detector.train(train,calibration,epochs=1)
    assert info['normal_training_records']==120
    assert info['calibration_records']==30
    assert detector.scaler.n_samples_seen_==120
    assert np.allclose(detector.scaler.mean_,expected_fit.mean(axis=0))
    assert len(calibration_score_inputs)==1
    assert np.array_equal(calibration_score_inputs[0],expected_calibration)
    assert info['split_strategy']=='chronological train/calibration/test periods'
    target=tx('api',1000*60,amount=250)
    history=train+calibration
    expected=feature_matrix([target],history)[0]
    assert np.array_equal(expected,features(target,history))

def test_production_partitioner_assigns_chronological_70_15_15():
    records=generate(count=1200,fraud_rate=.12,seed=81)
    training,calibration,testing=chronological_partitions(records)
    assert (len(training),len(calibration),len(testing))==(840,180,180)
    key=lambda row:(datetime.fromisoformat(row['timestamp']),row['id'])
    assert training==sorted(training,key=key)
    assert calibration==sorted(calibration,key=key)
    assert testing==sorted(testing,key=key)
    assert key(training[-1])<key(calibration[0])<key(testing[0])

def test_stored_rescoring_replays_history_chronologically_without_future_leakage():
    rows=[tx('late',180,user='U1'),tx('first',60,user='U1'),
          tx('other',120,user='U2'),tx('middle',120,user='U1')]
    conn=sqlite3.connect(':memory:'); conn.row_factory=sqlite3.Row
    conn.execute('''CREATE TABLE transactions (
        id TEXT,user_id TEXT,timestamp TEXT,amount REAL,hour INTEGER,account_age_days INTEGER,
        purchases_24h INTEGER,failed_attempts_24h INTEGER,payment_methods_7d INTEGER,
        device_changes_7d INTEGER,country_mismatch INTEGER,purchase_type TEXT,
        anomaly_score REAL,risk_level TEXT)''')
    conn.executemany('''INSERT INTO transactions VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',[
        (r['id'],r['user_id'],r['timestamp'],r['amount'],r['hour'],r['account_age_days'],
         r['purchases_24h'],r['failed_attempts_24h'],r['payment_methods_7d'],
         r['device_changes_7d'],r['country_mismatch'],r['purchase_type'],None,'unscored') for r in rows])
    scored=[]
    class SpyDetector:
        def score(self,target,history):
            vector=features(target,history)
            scored.append((target['id'],float(vector[FEATURE_NAMES.index('log_prior_transaction_count')])))
            return {'anomaly_score':1.0,'risk_level':'low'}
    try:
        assert rescore_all(conn,SpyDetector())==4
        assert [item[0] for item in scored]==['first','middle','other','late']
        assert dict(scored)['first']==0
        assert np.isclose(dict(scored)['middle'],np.log1p(1))
        assert np.isclose(dict(scored)['late'],np.log1p(2))
        assert conn.execute("SELECT anomaly_score FROM transactions WHERE id='late'").fetchone()[0]==1
    finally:
        conn.close()

def test_old_checkpoint_is_explicitly_rejected(tmp_path):
    import torch
    detector=Detector(load_existing=False); detector.model_file=tmp_path/'old.pt'
    torch.save({'weights':{},'mean':torch.zeros(11),'scale':torch.ones(11),'var':torch.ones(11),
                'n_samples_seen':10,'thresholds':{'medium':1.,'high':2.},'training_info':{}},detector.model_file)
    detector.load()
    assert not detector.ready
    assert 'Incompatible model checkpoint' in detector.checkpoint_error

def test_synthetic_rows_replay_as_user_histories():
    rows=generate(count=300,fraud_rate=.12,seed=12)
    assert rows==sorted(rows,key=lambda row:(row['timestamp'],row['id']))
    assert len({row['user_id'] for row in rows}) < len(rows)
    assert all(row['hour']==datetime.fromisoformat(row['timestamp']).hour for row in rows)
    assert all(row['purchases_24h']==0 for row in rows)

