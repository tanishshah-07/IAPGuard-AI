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
2. `update_demo()` generates one coherent 1,200-row repeated-user timeline, assigns 70/15/15 chronological train/calibration/test partitions, trains on normal training rows, and calibrates on normal calibration rows.
3. `Detector.score()` combines a transaction with strictly earlier same-user history, converts it to 19 standardized features, and calculates reconstruction error.
4. FastAPI returns overview, transaction, lab, review and evaluation data.
5. React fetches REST endpoints through Vite's `/api` proxy or `VITE_API_URL`.
6. Review decisions are persisted in SQLite without mutating model labels.

## Dataset and Storage

- Data source: `generate()` in `backend/app/synthetic.py`
- Default DB location: `backend/data/iapguard.sqlite3`
- Default checkpoint: `backend/data/vae.pt`
- Override DB location: `IAPGUARD_DATA_DIR`
- Tables: `transactions`, `reviews`
- `transactions` has an additive `evaluation_partition` column and `(user_id,timestamp,id)` history index; existing databases receive a backward-compatible migration.
- All demo rows contain synthetic-fraud labels for evaluation
- No external dataset, CSV import or real payment processor exists

## Engineered Feature Pipeline

`backend/app/model.py:features()` produces:

1. `log_amount`
2. `hour_sin`
3. `hour_cos`
4. `log_account_age`
5. `failed_attempts_24h`
6. `payment_methods_7d`
7. `device_changes_7d`
8. `country_mismatch`
9. `is_subscription`
10. `is_coaching`
11. `log_prior_transaction_count`
12. `log_historical_average_amount`
13. `log_historical_amount_std`
14. `relative_amount_deviation`
15. `log_seconds_since_previous`
16. `log_prior_count_1h`
17. `log_prior_count_24h`
18. `log_prior_count_7d`
19. `category_differs_from_history`

History is same-user only, UTC-normalized, strictly earlier than target time, and excludes equal timestamps and the target ID. Window lower bounds are inclusive. Amount spread uses population standard deviation (`ddof=0`); missing history and zero-mean relative deviation yield zero. The historical category is the most frequent category, with lexical tie-break. Legacy `purchases_24h` remains accepted/stored but is not a model input.

## VAE Architecture

```text
19 standardized input features
  -> Linear 19x32 -> ReLU
  -> Linear 32x16 -> ReLU
  -> Parallel Linear 16x5 mu
  -> Parallel Linear 16x5 logvar
  -> z (sampling during training; mu during inference)
  -> Linear 5x16 -> ReLU
  -> Linear 16x32 -> ReLU
  -> Linear 32x19 reconstruction
```

Loss:

```text
reconstruction = mean((decoded - standardized_input)^2)
KL = -0.5 * mean(sum(1 + logvar - mu^2 - exp(logvar)))
loss = reconstruction + 0.03 * KL
```

The scaler is fit only on normal rows in the earliest 70% period. The next 15% period supplies normal calibration rows for 95th/99th percentile thresholds. The final 15% mixed period is held out for synthetic metrics. Sequential histories can include only earlier rows, including earlier rows within calibration/test replay. Checkpoints carry feature schema version 2; prior 11-feature checkpoints are explicitly rejected and retrained at startup.

## Anomaly Scoring

```text
mean over 19 standardized feature residual squares
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

