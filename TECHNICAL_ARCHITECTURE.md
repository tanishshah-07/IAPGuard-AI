# Technical Architecture

## System Overview

```text
Synthetic generator
  backend/app/synthetic.py
        |
        v
SQLite transactions + reviews
  backend/app/db.py
        |
        v
FastAPI REST service
  backend/app/main.py
        |
        +--> Pydantic input validation
        +--> Feature conversion/scaling
        v
PyTorch VAE
  backend/app/model.py
        |
        +--> reconstruction residual score
        +--> 95th/99th normal percentiles
        +--> low/medium/high
        v
React dashboard
  frontend/src/main.jsx
  frontend/src/api.js
```

## Data Flow

1. Startup calls `initialize()` and creates SQLite tables.
2. If no transactions exist or no checkpoint is ready, `update_demo()` generates 1,500 normal records, trains the VAE, then generates and inserts 1,200 synthetic mixed records.
3. `Detector.score()` converts each row to 11 standardized features and calculates reconstruction error.
4. FastAPI returns overview, transaction, lab, review and evaluation data.
5. React fetches REST endpoints through Vite's `/api` proxy or `VITE_API_URL`.
6. Review decisions are persisted in SQLite without mutating model labels.

## Dataset and Storage

- Data source: `generate()` in `backend/app/synthetic.py`
- Default DB location: `backend/data/iapguard.sqlite3`
- Default checkpoint: `backend/data/vae.pt`
- Override DB location: `IAPGUARD_DATA_DIR`
- Tables: `transactions`, `reviews`
- All demo rows contain synthetic-fraud labels for evaluation
- No external dataset, CSV import or real payment processor exists

## Engineered Feature Pipeline

`backend/app/model.py:features()` produces:

1. `log_amount`
2. `hour_sin`
3. `hour_cos`
4. `log_account_age`
5. `log_purchases_24h`
6. `failed_attempts_24h`
7. `payment_methods_7d`
8. `device_changes_7d`
9. `country_mismatch`
10. `is_subscription`
11. `is_coaching`

The workout category is implicit because it is neither subscription nor coaching.

## VAE Architecture

```text
11 standardized input features
  -> Linear 11x32 -> ReLU
  -> Linear 32x16 -> ReLU
  -> Parallel Linear 16x5 mu
  -> Parallel Linear 16x5 logvar
  -> z (sampling during training; mu during inference)
  -> Linear 5x16 -> ReLU
  -> Linear 16x32 -> ReLU
  -> Linear 32x11 reconstruction
```

Loss:

```text
reconstruction = mean((decoded - standardized_input)^2)
KL = -0.5 * mean(sum(1 + logvar - mu^2 - exp(logvar)))
loss = reconstruction + 0.03 * KL
```

Training is performed on fraud-free synthetic records. The scaler is fit on 80% of those normals. The remaining 20% is used to calculate 95th/99th percentile thresholds.

## Anomaly Scoring

```text
mean over 11 standardized feature residual squares
  >= 99th percentile -> high
  >= 95th percentile -> medium
  otherwise -> low
```

The top three per-feature residuals are returned as descriptive deviations, not causal explanations.

## API Surface

All routes are in `backend/app/main.py`:

- `GET /api/health`
- `GET /api/overview`
- `GET /api/transactions`
- `GET /api/transactions/{transaction_id}`
- `POST /api/analyze`
- `POST /api/transactions/{transaction_id}/review`
- `GET /api/model`
- `POST /api/model/retrain`
- `GET /api/evaluation`
- `POST /api/demo/reset`

OpenAPI documentation is available at `/docs`.

## Frontend Architecture

- Entry: `frontend/src/main.jsx`
- API wrapper: `frontend/src/api.js`
- Styling: `frontend/src/style.css`
- State: React hooks in a single application file
- Pages: overview, transaction explorer, high-risk alerts, detection lab, model insights
- Detail: right-side modal drawer
- Charts: Recharts
- Icons: Lucide React

## Runtime Boundaries

- Backend origin: `http://127.0.0.1:8000`
- Frontend origin: `http://127.0.0.1:5173`
- Vite proxy: `/api` -> `IAPGUARD_PROXY_TARGET` or `http://127.0.0.1:8000`
- Separate frontend deployments: `VITE_API_URL`
- Separate CORS origins: `IAPGUARD_CORS_ORIGINS`

## Security and Production Gaps

- No authentication or RBAC
- No rate limiting
- No audit-log table
- Public retrain/reset endpoints
- No secrets or payment processing
- SQLite is local demo storage, not production scale storage
- No TLS, workload identity, encryption-at-rest policy or secrets manager
- No model signing, registry or deployment promotion

## Status Legend

- **COMPLETED:** implementation exists and evidence was inspected/tested
- **PARTIALLY COMPLETED:** useful implementation exists but important work remains
- **NOT IMPLEMENTED:** absent
- **NOT VERIFIED:** not demonstrated by an available test or artifact

