"""VAE anomaly detector with point-in-time per-user purchase features."""
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
import numpy as np
import torch
from torch import nn
from sklearn.preprocessing import StandardScaler
from .db import DATA_DIR

FEATURE_SCHEMA_VERSION = 2
FEATURE_NAMES = [
    'log_amount','hour_sin','hour_cos','log_account_age','failed_attempts_24h',
    'payment_methods_7d','device_changes_7d','country_mismatch','is_subscription','is_coaching',
    'log_prior_transaction_count','log_historical_average_amount','log_historical_amount_std',
    'relative_amount_deviation','log_seconds_since_previous','log_prior_count_1h',
    'log_prior_count_24h','log_prior_count_7d','category_differs_from_history'
]
WINDOWS = {'1h': 3600, '24h': 86400, '7d': 604800}

def as_utc(value):
    """Parse ISO timestamps, treating naive values as UTC and normalizing offsets."""
    if isinstance(value, datetime):
        parsed = value
    else:
        parsed = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)

def _history_for(tx, history):
    tx = dict(tx)
    history = [dict(row) for row in history]
    target_time = as_utc(tx['timestamp'])
    eligible = [row for row in history
                if row.get('user_id') == tx.get('user_id')
                and row.get('id') != tx.get('id')
                and as_utc(row['timestamp']) < target_time]
    return sorted(eligible, key=lambda row: (as_utc(row['timestamp']), str(row.get('id', ''))))

def features(tx, history=()):
    """Build 19 finite inputs using only strictly earlier same-user transactions.

    Amount standard deviation is population SD (ddof=0); with fewer than one
    prior purchase it is zero. Relative amount deviation is (current-mean)/mean,
    with zero for cold starts or a zero mean. Window boundaries are inclusive at
    T-window and exclusive at T. Missing time-since-previous is zero.
    """
    tx = dict(tx)
    target_time = as_utc(tx['timestamp'])
    earlier = _history_for(tx, history)
    amounts = np.asarray([float(row['amount']) for row in earlier], dtype=np.float64)
    count = len(earlier)
    mean = float(amounts.mean()) if count else 0.0
    std = float(amounts.std(ddof=0)) if count else 0.0
    deviation = (float(tx['amount']) - mean) / mean if mean > 0 else 0.0
    elapsed = (target_time - as_utc(earlier[-1]['timestamp'])).total_seconds() if count else 0.0
    counts = {name: sum((target_time-as_utc(row['timestamp'])).total_seconds() <= seconds
                        for row in earlier) for name, seconds in WINDOWS.items()}
    category_counts = {}
    for row in earlier:
        category_counts[row.get('purchase_type', '')] = category_counts.get(row.get('purchase_type', ''), 0) + 1
    prior_category = (sorted(category_counts.items(), key=lambda pair: (-pair[1], pair[0]))[0][0]
                      if category_counts else None)
    hour = int(tx.get('hour', target_time.hour))
    values = [
        np.log1p(float(tx['amount'])), np.sin(2*np.pi*hour/24), np.cos(2*np.pi*hour/24),
        np.log1p(max(0, int(tx['account_age_days']))), int(tx.get('failed_attempts_24h', 0)),
        int(tx.get('payment_methods_7d', 1)), int(tx.get('device_changes_7d', 0)),
        int(bool(tx.get('country_mismatch', False))), int(tx.get('purchase_type') == 'subscription'),
        int(tx.get('purchase_type') == 'coaching'), np.log1p(count), np.log1p(mean),
        np.log1p(std), deviation, np.log1p(elapsed), np.log1p(counts['1h']),
        np.log1p(counts['24h']), np.log1p(counts['7d']),
        int(prior_category is not None and tx.get('purchase_type') != prior_category)
    ]
    result = np.asarray(values, dtype=np.float32)
    if not np.isfinite(result).all():
        raise ValueError('Feature engineering produced a non-finite value')
    return result

def feature_matrix(transactions, history=()):
    """Create features in deterministic chronological order with strict as-of history."""
    ordered = sorted(transactions, key=lambda row: (as_utc(row['timestamp']), str(row.get('id', ''))))
    prior = list(history)
    matrix = []
    i = 0
    while i < len(ordered):
        instant = as_utc(ordered[i]['timestamp'])
        j = i
        while j < len(ordered) and as_utc(ordered[j]['timestamp']) == instant:
            j += 1
        group = ordered[i:j]
        matrix.extend(features(row, prior) for row in group)
        prior.extend(group)  # equal-time rows become eligible only at later instants
        i = j
    return np.stack(matrix) if matrix else np.empty((0, len(FEATURE_NAMES)), dtype=np.float32)

class VAE(nn.Module):
    def __init__(self, input_dim=len(FEATURE_NAMES)):
        super().__init__()
        self.encoder = nn.Sequential(nn.Linear(input_dim,32),nn.ReLU(),nn.Linear(32,16),nn.ReLU())
        self.mu = nn.Linear(16,5); self.logvar = nn.Linear(16,5)
        self.decoder = nn.Sequential(nn.Linear(5,16),nn.ReLU(),nn.Linear(16,32),nn.ReLU(),nn.Linear(32,input_dim))
    def forward(self, x):
        h=self.encoder(x); mu,logvar=self.mu(h),self.logvar(h)
        z=mu+torch.randn_like(mu)*torch.exp(.5*logvar) if self.training else mu
        return self.decoder(z),mu,logvar

class Detector:
    def __init__(self, *, load_existing=True):
        self.network=VAE(); self.scaler=StandardScaler(); self.thresholds=None
        self.training_info={}; self.model_file=DATA_DIR/'vae.pt'; self.checkpoint_error=None
        if load_existing: self.load()
    @property
    def ready(self): return self.thresholds is not None

    def train(self, training_transactions, calibration_transactions, epochs=24, seed=42):
        training_normals=[i for i,row in enumerate(training_transactions) if not row.get('is_synthetic_fraud',0)]
        calibration_normals=[i for i,row in enumerate(calibration_transactions) if not row.get('is_synthetic_fraud',0)]
        if len(training_normals)<100 or len(calibration_normals)<20:
            raise ValueError('At least 100 normal training and 20 normal calibration transactions required')
        torch.set_num_threads(2); torch.manual_seed(seed)
        all_train_features=feature_matrix(training_transactions)
        fit_data=all_train_features[training_normals]
        calibration_all=feature_matrix(calibration_transactions, history=training_transactions)
        calibration=calibration_all[calibration_normals]
        self.scaler=StandardScaler().fit(fit_data)
        train_x=torch.tensor(self.scaler.transform(fit_data),dtype=torch.float32)
        self.network=VAE(); self.network.train(); optimizer=torch.optim.Adam(self.network.parameters(),lr=.002)
        for _ in range(epochs):
            for idx in torch.randperm(len(train_x)).split(128):
                batch=train_x[idx]; reconstructed,mu,logvar=self.network(batch)
                reconstruction=(reconstructed-batch).square().mean()
                kl=-.5*torch.mean(torch.sum(1+logvar-mu.square()-logvar.exp(),dim=1))
                loss=reconstruction+.03*kl; optimizer.zero_grad(); loss.backward(); optimizer.step()
        self.network.eval(); calibration_scores=self.raw_scores(calibration)
        low,high=np.quantile(calibration_scores,[.95,.99])
        self.thresholds={'medium':float(low),'high':float(high)}
        self.training_info={'normal_training_records':len(training_normals),
            'calibration_records':len(calibration_normals),'epochs':epochs,'features':FEATURE_NAMES,
            'feature_schema_version':FEATURE_SCHEMA_VERSION,
            'threshold_strategy':'95th and 99th percentiles of chronological normal calibration period',
            'split_strategy':'chronological train/calibration/test periods','seed':seed}
        self.checkpoint_error=None
        return self.training_info

    def raw_scores(self, matrix):
        data=torch.tensor(self.scaler.transform(matrix),dtype=torch.float32)
        with torch.no_grad(): recovered,_,_=self.network(data); return (recovered-data).square().mean(dim=1).numpy()

    def score(self, tx, history=()):
        if not self.ready: raise RuntimeError(self.checkpoint_error or 'Detector must be trained first')
        input_data=torch.tensor(self.scaler.transform(features(tx,history).reshape(1,-1)),dtype=torch.float32)
        with torch.no_grad():
            reconstructed,_,_=self.network(input_data); errors=(reconstructed-input_data).square()
            score=errors.mean(dim=1).item(); residual=errors[0].numpy()
        risk='high' if score>=self.thresholds['high'] else ('medium' if score>=self.thresholds['medium'] else 'low')
        ranked=sorted(zip(FEATURE_NAMES,residual),key=lambda item:item[1],reverse=True)
        return {'anomaly_score':round(score,5),'risk_level':risk,
            'top_deviations':[{'feature':name,'contribution':round(float(value),4)} for name,value in ranked[:3]],
            'thresholds':self.thresholds}

    def save(self):
        DATA_DIR.mkdir(parents=True,exist_ok=True)
        with NamedTemporaryFile(dir=DATA_DIR,delete=False) as checkpoint:
            path=Path(checkpoint.name)
            try:
                torch.save({'feature_schema_version':FEATURE_SCHEMA_VERSION,'feature_names':FEATURE_NAMES,
                    'weights':self.network.state_dict(),'mean':torch.tensor(self.scaler.mean_),
                    'scale':torch.tensor(self.scaler.scale_),'var':torch.tensor(self.scaler.var_),
                    'n_samples_seen':int(self.scaler.n_samples_seen_),'thresholds':self.thresholds,
                    'training_info':self.training_info},checkpoint)
                checkpoint.close(); path.replace(self.model_file)
            finally:
                checkpoint.close(); path.unlink(missing_ok=True)

    def load(self):
        if not self.model_file.exists(): return
        try:
            payload=torch.load(self.model_file,map_location='cpu',weights_only=True)
            if payload.get('feature_schema_version') != FEATURE_SCHEMA_VERSION or payload.get('feature_names') != FEATURE_NAMES:
                self.checkpoint_error='Incompatible model checkpoint feature schema; retraining required.'
                return
            if len(payload['mean']) != len(FEATURE_NAMES) or len(payload['scale']) != len(FEATURE_NAMES):
                self.checkpoint_error='Incompatible model checkpoint scaler dimensions; retraining required.'
                return
            self.network.load_state_dict(payload['weights']); self.network.eval()
            self.scaler.mean_=payload['mean'].numpy(); self.scaler.scale_=payload['scale'].numpy()
            self.scaler.var_=payload['var'].numpy(); self.scaler.n_features_in_=len(FEATURE_NAMES)
            self.scaler.n_samples_seen_=payload['n_samples_seen']
            self.thresholds=payload['thresholds']; self.training_info=payload['training_info']
        except (KeyError,RuntimeError,ValueError,TypeError) as exc:
            self.checkpoint_error=f'Invalid model checkpoint ({exc}); retraining required.'
