"""Unsupervised VAE: train on synthetic normal behavior and calibrate anomaly thresholds.

Security/interpretability note: VAE reconstruction error signals atypicality, not proof of fraud.
"""
from pathlib import Path
from tempfile import NamedTemporaryFile
import numpy as np
import torch
from torch import nn
from sklearn.preprocessing import StandardScaler
from .db import DATA_DIR

FEATURE_NAMES = ['log_amount','hour_sin','hour_cos','log_account_age', 'log_purchases_24h',
                 'failed_attempts_24h', 'payment_methods_7d', 'device_changes_7d','country_mismatch',
                 'is_subscription', 'is_coaching']

def features(tx):
    hour = int(tx['hour'])
    return np.array([
        np.log1p(float(tx['amount'])), np.sin(2*np.pi*hour/24), np.cos(2*np.pi*hour/24),
        np.log1p(int(tx['account_age_days'])), np.log1p(int(tx['purchases_24h'])),
        int(tx['failed_attempts_24h']), int(tx['payment_methods_7d']),
        int(tx['device_changes_7d']), int(tx['country_mismatch']),
        int(tx['purchase_type']=='subscription'), int(tx['purchase_type']=='coaching')
    ], dtype=np.float32)

class VAE(nn.Module):
    def __init__(self, input_dim=len(FEATURE_NAMES)):
        super().__init__()
        self.encoder = nn.Sequential(nn.Linear(input_dim, 32), nn.ReLU(), nn.Linear(32, 16), nn.ReLU())
        self.mu = nn.Linear(16, 5)
        self.logvar = nn.Linear(16, 5)
        self.decoder = nn.Sequential(nn.Linear(5, 16), nn.ReLU(), nn.Linear(16, 32),
                                     nn.ReLU(), nn.Linear(32, input_dim))
    def forward(self, x):
        h = self.encoder(x)
        mu, logvar = self.mu(h), self.logvar(h)
        if self.training:
            z = mu + torch.randn_like(mu) * torch.exp(0.5 * logvar)
        else:
            z = mu  # deterministic inference
        return self.decoder(z), mu, logvar

class Detector:
    def __init__(self, *, load_existing=True):
        self.network = VAE()
        self.scaler = StandardScaler()
        self.thresholds = None
        self.training_info = {}
        self.model_file = DATA_DIR / 'vae.pt'
        if load_existing:
            self.load()

    @property
    def ready(self): return self.thresholds is not None

    def train(self, normal_transactions, epochs=28, seed=42):
        if len(normal_transactions) < 100:
            raise ValueError('At least 100 normal transactions required')
        torch.set_num_threads(2)
        torch.manual_seed(seed)
        matrix = np.stack([features(x) for x in normal_transactions])
        generator = np.random.default_rng(seed)
        indices = generator.permutation(len(matrix))
        split = int(len(matrix)*0.8)
        fit_data, calibration = matrix[indices[:split]], matrix[indices[split:]]
        # Do not fit standardization on calibration records.
        self.scaler = StandardScaler().fit(fit_data)
        train_x = torch.tensor(self.scaler.transform(fit_data), dtype=torch.float32)
        self.network = VAE()
        self.network.train()
        optimizer = torch.optim.Adam(self.network.parameters(), lr=0.002)
        batch_size = 128
        for epoch in range(epochs):
            for idx in torch.randperm(len(train_x)).split(batch_size):
                batch = train_x[idx]
                reconstructed, mu, logvar = self.network(batch)
                reconstruction = torch.mean((reconstructed-batch)**2)
                kl = -0.5 * torch.mean(torch.sum(1 + logvar - mu.square() - logvar.exp(), dim=1))
                loss = reconstruction + 0.03 * kl
                optimizer.zero_grad(); loss.backward(); optimizer.step()
        self.network.eval()
        calibration_scores = self.raw_scores(calibration)
        low, high = np.quantile(calibration_scores, [0.95, 0.99])
        self.thresholds = {'medium':float(low), 'high':float(high)}
        self.training_info = {'normal_training_records':int(len(fit_data)),
                              'calibration_records':int(len(calibration)),
                              'epochs':epochs, 'features':FEATURE_NAMES,
                              'threshold_strategy':'95th and 99th percentiles of held-out normal data',
                              'seed':seed}
        return self.training_info

    def raw_scores(self, feature_matrix):
        data = torch.tensor(self.scaler.transform(feature_matrix), dtype=torch.float32)
        with torch.no_grad():
            recovered, _, _ = self.network(data)
            scores = (recovered-data).square().mean(dim=1).numpy()
        return scores

    def score(self, tx):
        if not self.ready: raise RuntimeError('Detector must be trained first')
        # Feature-level residuals are indicative, not causal explanations.
        input_data = torch.tensor(self.scaler.transform(features(tx).reshape(1,-1)), dtype=torch.float32)
        with torch.no_grad():
            reconstructed, _, _ = self.network(input_data)
            errors = (reconstructed-input_data).square()
            score = errors.mean(dim=1).item()
            residual = errors[0].numpy()
        risk = 'high' if score >= self.thresholds['high'] else ('medium' if score >= self.thresholds['medium'] else 'low')
        ranked = sorted(zip(FEATURE_NAMES, residual), key=lambda x:x[1], reverse=True)
        return {'anomaly_score':round(score,5), 'risk_level':risk,
                'top_deviations':[{'feature':name,'contribution':round(float(value),4)} for name,value in ranked[:3]],
                'thresholds':self.thresholds}

    def save(self):
        DATA_DIR.mkdir(parents=True,exist_ok=True)
        with NamedTemporaryFile(dir=DATA_DIR, delete=False) as checkpoint:
            temporary_path = Path(checkpoint.name)
            try:
                torch.save({'weights':self.network.state_dict(),'mean':torch.tensor(self.scaler.mean_),
                            'scale':torch.tensor(self.scaler.scale_),'var':torch.tensor(self.scaler.var_),
                            'n_samples_seen':int(self.scaler.n_samples_seen_),
                            'thresholds':self.thresholds,'training_info':self.training_info},checkpoint)
                checkpoint.close()
                temporary_path.replace(self.model_file)
            finally:
                checkpoint.close()
                temporary_path.unlink(missing_ok=True)

    def load(self):
        if not self.model_file.exists(): return
        # Only load this locally generated trusted model file. Avoid untrusted .pt files.
        payload = torch.load(self.model_file,map_location='cpu',weights_only=True)
        self.network.load_state_dict(payload['weights']); self.network.eval()
        self.scaler.mean_ = payload['mean'].numpy();self.scaler.scale_ = payload['scale'].numpy()
        self.scaler.var_ = payload['var'].numpy();self.scaler.n_features_in_ = len(FEATURE_NAMES)
        self.scaler.n_samples_seen_ = payload['n_samples_seen']
        self.thresholds = payload['thresholds'];self.training_info = payload['training_info']
