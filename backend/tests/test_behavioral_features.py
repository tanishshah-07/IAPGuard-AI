from datetime import datetime, timedelta, timezone
import numpy as np
from app.model import FEATURE_NAMES, Detector, feature_matrix, features
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

def test_training_uses_chronological_normal_partitions_and_api_feature_parity(tmp_path):
    train=[tx(f't{i}',i*60,amount=100+i%5) for i in range(120)]
    calibration=[tx(f'c{i}',(120+i)*60,amount=101+i%5,label=int(i%7==0)) for i in range(35)]
    detector=Detector(load_existing=False); info=detector.train(train,calibration,epochs=1)
    assert info['normal_training_records']==120
    assert info['calibration_records']==30
    assert info['split_strategy']=='chronological train/calibration/test periods'
    target=tx('api',1000*60,amount=250)
    history=train+calibration
    expected=feature_matrix([target],history)[0]
    assert np.array_equal(expected,features(target,history))

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

