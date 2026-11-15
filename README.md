# IAPGuard AI — In-App Purchase Anomaly Detection

A full-stack **educational prototype** for the **Sports & Fitness Tech** domain. It learns purchase patterns with an **unsupervised PyTorch Variational Autoencoder (VAE)**, scores unusual activity, and presents investigations in a React dashboard.

> **Demo only.** All seeded data and labels are synthetic. Anomaly scores are *not* fraud probabilities or evidence of wrongdoing. This app has **no authentication, payment processor connection, or production fraud-blocking behavior**. Do not expose its administrative endpoints publicly or feed real personal/payment data into this prototype.

## Features

- Modern responsive dark dashboard with transaction trends, risk breakdown and recent activity
- 1,200 generated sample in-app purchases, with separate synthetic training and evaluation data
- VAE model trained on normal-only transactions; 95th/99th percentile calibration from held-out normals
- Live inference form with reconstructed-feature deviations
- Filterable/paginated transaction explorer, export current page to CSV
- High-risk investigation queue; persist review decisions and notes in SQLite
- Synthetic precision, recall, F1, false-positive rate and confusion counts
- Retrain VAE / reset data via UI; persisted model weights in `backend/data/vae.pt`
- OpenAPI reference at `/docs`; backend API integration test

## Stack

| Layer | Technology |
| --- | --- |
| UI | React 18, Vite 6, Lucide icons, Recharts, CSS |
| API | Python 3.10+, FastAPI, Pydantic |
| ML | PyTorch, NumPy, scikit-learn |
| Database | SQLite (Python standard library) |

## Run locally

**Terminal 1 — Python API**

```bash
cd backend
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# Windows cmd: .venv\Scripts\activate.bat
# macOS / Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

On first startup, synthetic data generation and VAE training run automatically (typically seconds to a minute, depending on CPU). API: http://localhost:8000/docs

**Terminal 2 — React dashboard**

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173**. Vite proxies `/api` to the Python server.

For a production build of the frontend only: `cd frontend && npm run build`. You must serve the API separately and set `VITE_API_URL` appropriately before building.

## Backend tests

```bash
cd backend
pytest -q
```

The test uses a temporary database/model directory and does not overwrite your normal demo.

## Architecture / pipeline

```text
Fitness app transaction or simulated demo event
                |
       FastAPI REST endpoints
                |
   feature conversion and scaling
    (11 engineered input dimensions)
                |
  PyTorch VAE encoder -> latent z -> decoder
                |
    mean squared reconstruction error
                |
    95% normal cutoff: MEDIUM
    99% normal cutoff: HIGH
                |
       scored transaction in SQLite
                |
       React overview, alerts, review
```

During training, random mini-batch sampling and a KL loss term regularize the VAE. At inference the model uses `z = mu` instead of random sampling to make scores deterministic. The scaler is fit only on the normal training split. Thresholds are calibrated on a held-out normal split (not the dashboard evaluation records).

### VAE features

- Log purchase amount
- Sine and cosine hour of day
- Log account age in days
- Log purchase count over 24 hours
- Failed payment attempts over 24 hours
- Distinct payment methods over seven days
- Device changes over seven days
- Billing country mismatch
- Subscription category indicator
- Coaching category indicator

### Scoring and evaluation

A higher reconstruction error indicates that the purchase differs more from synthetic normal patterns. A transaction is `high` at or above the 99th-percentile threshold; `medium` at or above the 95th-percentile threshold; otherwise `low`. Percentile calibration is not a guarantee of a given false-positive rate on real data. Evaluation uses synthetic scenario labels and counts **high-risk** signals as positive predictions. The demo's inflated/separable scenarios may make metrics optimistic.

## REST endpoints

| Verb | Endpoint | Function |
| --- | --- | --- |
| GET | `/api/health` | Server / model readiness |
| GET | `/api/overview` | KPI, trend and recent transactions |
| GET | `/api/transactions?page=1&risk=all&search=` | Paginated list |
| GET | `/api/transactions/{id}` | Details, reconstruction deviations, prior review |
| POST | `/api/analyze` | Score manually supplied features; does not persist |
| POST | `/api/transactions/{id}/review` | Record review outcome and note |
| GET | `/api/model` | Architecture feature list + calibration thresholds |
| POST | `/api/model/retrain` | Retrain on synthetic normals and rescore saved dataset |
| GET | `/api/evaluation` | Metrics on injected synthetic anomalies |
| POST | `/api/demo/reset` | Delete all demo transactions/reviews and reseed |

## Example scoring request

```bash
curl -X POST http://localhost:8000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"user_id":"USR-TEST","amount":12499,"hour":2,"account_age_days":2,"purchases_24h":24,"failed_attempts_24h":8,"payment_methods_7d":6,"device_changes_7d":4,"country_mismatch":true,"purchase_type":"subscription"}'
```

## Suggested viva / presentation demonstration

1. Open **Overview** and describe the KPI cards, daily trend, and risk chart.
2. Show **Transactions** and filter high-risk records. Open one to inspect reconstructed-feature deviations.
3. Mark a record as **Needs further review** to demonstrate database writes.
4. Open **AI Detection Lab** and compare a normal purchase to an unusual rapid-purchase scenario.
5. Open **Model insights** and explain the VAE's encoder, latent distribution, decoder, KL term, reconstruction error, calibration, and limitations.
6. Show `http://localhost:8000/docs` and explain the frontend -> backend -> model -> SQLite data flow.

## Production next steps

Proper authentication and role permissions, rate limiting, audit trails, real PSP integration with PCI-conscious data boundaries, privacy controls, fraud-confirmation workflows, model versioning, drift monitoring, independent real-data evaluation, and staged deployment. **Do not treat this prototype as safe for processing real transactions.**
