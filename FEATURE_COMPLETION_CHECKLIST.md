# Feature Completion Checklist

Status values are restricted to **COMPLETED**, **PARTIALLY COMPLETED**, **NOT IMPLEMENTED**, and **NOT VERIFIED**.

| Requirement | Status | Actual implementation | Source file and function | Evidence or test | Missing work | Priority |
|---|---|---|---|---|---|---|
| Purchase dataset generated | COMPLETED | 1,200 demo rows generated from reproducible seed | `backend/app/synthetic.py:generate()` | One passing end-to-end test seed reset | Real source, provenance and batch import | Medium |
| Synthetic dataset label | COMPLETED | `is_synthetic_fraud` and `source='demo'` | `generate()`, `db.py:initialize()` | Persisted DB contains 155 fraud labels | Real verified labels | High |
| Transaction schema | COMPLETED | 16 database fields plus review table | `db.py:initialize()` | Schema inspected | Payment-token-safe integration and audit fields | Medium |
| Missing-value validation | PARTIALLY COMPLETED | Pydantic validates API fields | `main.py:TransactionInput` | Test posted valid/invalid conditions partly | Dataset missingness and invalid stored-row validation | High |
| Per-user history | COMPLETED (prototype) | Shared earlier-only builder derives count, amount baseline/deviation, elapsed time, windows and category change | `model.py:features()`, `feature_matrix()` | Backend tests cover calculations, ties, cold starts and leakage | Authentication and production isolation remain absent | High |
| Amount log feature | COMPLETED | `log1p(amount)` | `model.py:features()` | In model input matrix | Amount baseline/z-score | Medium |
| Cyclic hour features | COMPLETED | sine/cosine hour | `model.py:features()` | In model input matrix | Day/week/time-since features | Medium |
| Account-age feature | COMPLETED | `log1p(account_age_days)` | `model.py:features()` | In model input matrix | Account-age trend/history | Low |
| Purchase-frequency feature | COMPLETED (prototype) | Prior 1h/24h/7d counts derived from same-user history; legacy count remains in API/DB | `model.py:features()` | Boundary and chronology tests | Real traffic validation | High |
| Failed-payment feature | COMPLETED | 24h failure count | `features()` | In model input matrix | Failure rate/consecutive failures | Medium |
| Payment-method feature | COMPLETED | 7d method count | `features()` | In model input matrix | Known/unknown method history | Medium |
| Device-change feature | COMPLETED | 7d device-change count | `features()` | In model input matrix | Known-device ratio and recency | Medium |
| Country mismatch | COMPLETED | Boolean/int encoding | `features()` | API and synthetic data | Geo consistency history | Medium |
| Purchase category | COMPLETED | Subscription and coaching indicators | `features()` | 19 input dimensions; workout implicit as zeros | Complete explicit workout indicator | Low |
| Normal-only VAE training | COMPLETED (synthetic) | Normal rows from earliest 70% period | `main.py:update_demo()`, `model.py:train()` | Health and model readiness pass | Independent real-data evaluation and CV | High |
| Chronological train/calibration/test | COMPLETED (synthetic) | 70/15/15 chronological periods; normals fit/calibrate and later mixed period evaluated | `main.py:update_demo()`, `model.py:Detector.train()` | End-to-end tests and synthetic held-out metric run | Multi-seed and real-data validation | High |
| Reconstruction loss | COMPLETED | Mean squared residual | `model.py:train()` | Source inspected | Weighted loss experiment | Low |
| KL divergence | COMPLETED | Closed-form KL regularizer | `model.py:train()` | Source inspected | Annealing/sensitivity test | Medium |
| Reparameterization | COMPLETED | epsilon-sampled latent during training | `VAE.forward()` | Source inspected | Monte-Carlo uncertainty scoring | Low |
| Deterministic inference | COMPLETED | Uses latent mean, not random sampling | `VAE.forward()` | README/source consistent | Intentionally stochastic uncertainty mode | Low |
| Checkpoint persistence | COMPLETED | Atomic save/load with feature schema version 2 | `Detector.save/load()` | Old schema rejection tested | Hash/signature and registry versioning | Medium |
| 95th/99th thresholds | COMPLETED | Held-out normal percentile calibration | `Detector.train()` | Source and API model info | Cost-based threshold tuning | Medium |
| Low/medium/high classification | COMPLETED | Threshold comparator | `Detector.score()` | API and UI | Separate medium+high policy | Low |
| Top-3 feature deviations | COMPLETED | Squared standardized residual ranking | `Detector.score()` | API detail test | Causal/explainable interpretation | Medium |
| Precision/recall/F1/FPR | COMPLETED | Synthetic label confusion counts | `main.py:evaluation()` | Live persisted metrics | Real evaluation | High |
| Confusion matrix | COMPLETED | TP/FP/TN/FN | `evaluation()` | Counts inspected | Confusion visualization/export | Medium |
| FastAPI health | COMPLETED | Readiness endpoint | `main.py:health()` | Live and TestClient pass | Dependency/database readiness detail | Low |
| FastAPI overview | COMPLETED | KPIs/trends/categories/recent | `main.py:overview()` | Live and test pass | Date range and cache | Low |
| Transaction pagination/filter | COMPLETED | SQL pagination/search/risk | `main.py:transactions()` | Test API pass | Sorts, cursor, transaction count | Low |
| Transaction detail | COMPLETED | Stored row plus live analysis/review | `main.py:transaction_detail()` | 404 test pass | Review history/audit | Medium |
| Stateless analysis | COMPLETED | Pydantic input and VAE score | `main.py:analyze()` | Test pass | Batch scoring/import | Medium |
| Review persistence | COMPLETED | Upsert review and status update | `main.py:review_transaction()` | Test pass | Auth and audit trail | High |
| Retrain operation | COMPLETED | Normal retrain and rescore | `update_demo()`, `retrain()` | Test pass | Scheduled/versioned retraining | High |
| Reset operation | COMPLETED | Delete/seed/retrain | `reset_demo()` | Test pass | Preview/backup/role permission | High |
| React overview | COMPLETED | Live API KPIs/charts | `main.jsx:Overview()` | Build pass | Browser verification | Medium |
| React transaction explorer | COMPLETED | Search/filter/pagination/export | `main.jsx:Transactions()` | Build pass | Browser and component tests | Medium |
| React risk queue | COMPLETED | High-risk list | `main.jsx:Alerts()` | Build pass | SLA/assignment workflow | Medium |
| React detection lab | COMPLETED | Inference form/result/deviations | `main.jsx:Lab()` | Build/test pass | Batch upload/presets | Medium |
| React model insights | COMPLETED | Training, thresholds, synthetic metrics | `main.jsx:ModelPage()` | Build pass | Real ROC/PR/training curves | Medium |
| Authentication | NOT IMPLEMENTED | Demo-only public API | `main.py` | README/source evidence | Add authn/authz | High |
| Automated security scan | NOT VERIFIED | No security configuration | Repository scan | No secret patterns found | CI dependency/SAST/secrets scan | High |
| Browser testing | NOT IMPLEMENTED | No browser test framework | `frontend/package.json` | Not present | Playwright/Cypress tests | High |
| Assignment documentation | COMPLETED | README/CODEX plus these audit reports | Root Markdown | Audited | Formal presentation and rubric mapping | Medium |

