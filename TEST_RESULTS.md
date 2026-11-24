# Test and Audit Results

**Validation date:** 2026-11-24

**Checks run on 2026-11-24:** Backend pytest and frontend production build. Backend result: 11 passed, 1 warning; frontend build succeeded.

**Historical checks:** The live API smoke, SQLite consistency, and source/security observations below are from earlier audit snapshots; they were not rerun on 2026-11-24.
**Browser testing:** NOT PERFORMED. UI behavior was inspected statically only.

## Backend Test

Command:

```powershell
cd D:\important\IAPGuard_AI_Download_2026_11_12\iapguard-ai
.\backend\.venv\Scripts\python.exe -m pytest backend/tests -q
```

Result:

```text
11 passed
1 warning
```

Warnings:

1. FastAPI/Starlette test client deprecation notice involving `httpx2`.

Test coverage:

- Application startup and model readiness
- Overview transaction count
- High-risk transaction retrieval
- Transaction detail and top deviations
- Review save and reload
- Stateless live analysis
- Evaluation availability
- Model readiness
- Missing transaction 404
- Retrain and transaction rescore
- Reset and review deletion
- Readiness across a second TestClient lifecycle
- Historical math, boundary, cold-start and zero-variance behavior
- Equal-time exclusion, future/self exclusion, and chronological feature order
- Label-independent features, training/API feature parity, and old checkpoint rejection
- Backward-compatible SQLite migration and API response fields
- `/api/analyze` history lookup restricted to earlier rows for the requested user, ignores target IDs outside its schema, returns `saved:false`, and does not add a transaction
- Production 70/15/15 partition sizes and ordering
- Scaler sample count equals normal training rows; threshold score input contains only normal calibration rows
- Stored rescoring runs in chronological order and later records see only earlier same-user history

**Status:** PARTIALLY COMPLETED. Tests cover targeted behavior, API, partition, replay and migration paths, not full malformed-data, security or concurrency coverage.

## Frontend Production Build

Command:

```powershell
cd D:\important\IAPGuard_AI_Download_2026_11_12\iapguard-ai\frontend
npm.cmd run build
```

Result:

```text
vite v6.4.6
1993 modules transformed
dist/index.html, CSS and JS generated
build succeeded
```

Warning: the JavaScript bundle is 590.61 kB and exceeds Vite's 500 kB chunk warning threshold.

**Status:** COMPLETED for build; NOT VERIFIED for browser behavior.

## Historical Live API Smoke Snapshot (not rerun 2026-11-24)

Backend command:

```powershell
cd D:\important\IAPGuard_AI_Download_2026_11_12\iapguard-ai\backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Health check:

```powershell
curl.exe -sS http://127.0.0.1:8000/api/health
```

Observed:

```json
{"status":"ok","model_ready":true,"demo_mode":true}
```

Evaluation check:

```powershell
curl.exe -sS "http://127.0.0.1:8000/api/evaluation"
```

Observed synthetic metrics:

```json
{"available":true,"precision":0.9273,"recall":0.9871,"f1":0.9563,"false_positive_rate":0.0115,"confusion":{"tp":153,"fp":12,"tn":1033,"fn":2}}
```

These legacy metrics used all 1,200 rows and are not comparable to the chronological held-out result below.

## Milestone 1 Chronological Held-Out Metrics

The current pipeline reports metrics only for the later 15% test period (180 records in the seeded demo), after normal-only training and calibration on earlier periods. One seeded evaluation produced:

```json
{"available":true,"precision":0.7895,"recall":0.6,"f1":0.6818,"false_positive_rate":0.0258,"confusion":{"tp":15,"fp":4,"tn":151,"fn":10}}
```

This is synthetic-data evaluation only. The legacy result used all rows and is not an apples-to-apples baseline. Neither result demonstrates real fraud-detection performance.

## Historical SQLite Data Consistency Snapshot (not rerun 2026-11-24)

Observed persisted database:

- Tables: `transactions`, `reviews`, indexes and SQLite primary-key indexes
- Transaction rows: 1,200
- Chronological partitions: 840 train, 180 calibration, 180 test
- Null anomaly scores: 0
- Duplicate transaction IDs: 0
- Scored risk bands in one seeded validation run: 70 high, 32 medium, 1,098 low
- Review rows: 0

Behavioral features are derived at scoring time from raw transaction history; they are not stored as redundant columns. This snapshot reflects one seeded validation run.

## Historical Security and Generated-File Snapshot (not rerun 2026-11-24)

- No embedded AWS key, private key or obvious hardcoded secret pattern was found.
- `.env.example` contains variable names and no secret values.
- `.gitignore` ignores virtualenv, node_modules, dist, SQLite data and environment files.
- No authentication or authorization implementation exists.
- No automated dependency vulnerability, SAST or secrets scan was run.
- `backend/package-lock.json` is untracked and appears inconsistent with the Python backend structure.

## Browser Verification

**NOT VERIFIED / NOT IMPLEMENTED:** no browser automation or component test framework was available or configured.

## Exact Reproduction Commands

Backend tests:

```powershell
cd D:\important\IAPGuard_AI_Download_2026_11_12\iapguard-ai\backend
.\.venv\Scripts\python.exe -m pytest -q
```

Frontend build:

```powershell
cd D:\important\IAPGuard_AI_Download_2026_11_12\iapguard-ai\frontend
npm.cmd run build
```

Backend startup:

```powershell
cd D:\important\IAPGuard_AI_Download_2026_11_12\iapguard-ai\backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Frontend startup:

```powershell
cd D:\important\IAPGuard_AI_Download_2026_11_12\iapguard-ai\frontend
npm.cmd run dev
```

Health:

```powershell
curl.exe -sS http://127.0.0.1:8000/api/health
```

Evaluation:

```powershell
curl.exe -sS http://127.0.0.1:8000/api/evaluation
```

OpenAPI:

```text
http://127.0.0.1:8000/docs
```

Persisted database inspection:

```powershell
cd D:\important\IAPGuard_AI_Download_2026_11_12\iapguard-ai\backend
.\.venv\Scripts\python.exe -c "import sqlite3; c=sqlite3.connect('data/iapguard.sqlite3'); c.row_factory=sqlite3.Row; print(c.execute('SELECT COUNT(*) FROM transactions').fetchone()[0]); print([dict(r) for r in c.execute('SELECT risk_level,COUNT(*) n FROM transactions GROUP BY risk_level')])"
```

Synthetic confusion calculation:

```powershell
cd D:\important\IAPGuard_AI_Download_2026_11_12\iapguard-ai\backend
.\.venv\Scripts\python.exe -c "import sqlite3; c=sqlite3.connect('data/iapguard.sqlite3'); rows=c.execute('SELECT risk_level,is_synthetic_fraud FROM transactions').fetchall(); tp=sum(r=='high' and y==1 for r,y in rows); fp=sum(r=='high' and y==0 for r,y in rows); fn=sum(r!='high' and y==1 for r,y in rows); tn=sum(r!='high' and y==0 for r,y in rows); p=tp/(tp+fp) if tp+fp else 0; rr=tp/(tp+fn) if tp+fn else 0; f=2*p*rr/(p+rr) if p+rr else 0; fpr=fp/(fp+tn) if fp+tn else 0; print({'precision':round(p,4),'recall':round(rr,4),'f1':round(f,4),'false_positive_rate':round(fpr,4),'confusion':{'tp':tp,'fp':fp,'tn':tn,'fn':fn}})"
```
