# Feature Completion Checklist

Status values are restricted to **COMPLETED**, **PARTIALLY COMPLETED**, **NOT IMPLEMENTED**, and **NOT VERIFIED**. Prototype and synthetic-only limits belong in the implementation/evidence columns, not the status field.

| Requirement | Status | Actual implementation | Source file and function | Evidence or test | Missing work | Priority |
|---|---|---|---|---|---|---|
| Purchase dataset generated | COMPLETED | 1,200 demo rows generated from reproducible seed | `backend/app/synthetic.py:generate()` | One passing end-to-end test seed reset | Real source, provenance and batch import | Medium |
| Synthetic dataset label | COMPLETED | `is_synthetic_fraud` and `source='demo'` | `generate()`, `db.py:initialize()` | Persisted DB contains 155 fraud labels | Real verified labels | High |
| Transaction schema | COMPLETED | 16 database fields plus review table | `db.py:initialize()` | Schema inspected | Payment-token-safe integration and audit fields | Medium |
| Missing-value validation | PARTIALLY COMPLETED | Pydantic validates API fields | `main.py:TransactionInput` | Test posted valid/invalid conditions partly | Dataset missingness and invalid stored-row validation | High |
| Per-user history | COMPLETED | Prototype builder derives strict earlier-only count, amount baseline/deviation, elapsed time, windows and category change | `model.py:features()`, `feature_matrix()` | Tests cover history math, equal-time/future exclusion, API same-user lookup and cold start | Authentication, tenant isolation and real traffic validation remain future work | High |
| Amount features | COMPLETED | `log1p(amount)` plus historical average, population SD and signed relative deviation | `model.py:features()` | Present in the 19-input matrix and history tests | Median baseline and robust z-score remain future options | Medium |
| Cyclic hour features | COMPLETED | Sine/cosine hour | `model.py:features()` | In model input matrix | Weekday, weekend and seasonal features | Medium |
| Account-age feature | COMPLETED | `log1p(account_age_days)` | `model.py:features()` | In model input matrix | Account-age trend/history | Low |
| Purchase-frequency feature | COMPLETED | Prior 1h/24h/7d counts derived from same-user history; legacy count remains in API/DB | `model.py:features()` | Window and replay tests | Real traffic validation | High |
| Failed-payment feature | COMPLETED | 24h failure count | `features()` | In model input matrix | Failure rate/consecutive failures | Medium |
| Payment-method feature | COMPLETED | 7d method count | `features()` | In model input matrix | Known/unknown method history | Medium |
| Device-change feature | COMPLETED | 7d device-change count | `features()` | In model input matrix | Known-device ratio and recency | Medium |
| Country mismatch | COMPLETED | Boolean/int encoding | `features()` | API and synthetic data | Geo consistency history | Medium |
| Purchase category | COMPLETED | Subscription and coaching indicators | `features()` | 19 input dimensions; workout implicit as zeros | Complete explicit workout indicator | Low |
| Normal-only VAE training | COMPLETED | Fit uses normal rows from earliest 70% period of a synthetic timeline | `main.py:update_demo()`, `model.py:train()` | Test asserts scaler sample count equals normal training count | Independent real-data evaluation and cross-validation remain future work | High |
| Chronological train/calibration/test | COMPLETED | 70/15/15 chronological synthetic periods; normal fit/calibration and later mixed test | `main.py:chronological_partitions()`, `Detector.train()` | Tests assert production partition sizes/order and chronological stored-row replay | Multi-seed and real-data validation remain future work | High |
| Reconstruction loss | COMPLETED | Mean squared residual | `model.py:train()` | Source inspected | Weighted loss experiment | Low |
| KL divergence | COMPLETED | Closed-form KL regularizer | `model.py:train()` | Source inspected | Annealing/sensitivity test | Medium |
| Reparameterization | COMPLETED | epsilon-sampled latent during training | `VAE.forward()` | Source inspected | Monte-Carlo uncertainty scoring | Low |
| Deterministic inference | COMPLETED | Uses latent mean, not random sampling | `VAE.forward()` | README/source consistent | Intentionally stochastic uncertainty mode | Low |
| Checkpoint persistence | COMPLETED | Atomic save/load with feature schema version 2 | `Detector.save/load()` | Old schema rejection tested | Hash/signature and registry versioning | Medium |
| 95th/99th thresholds | COMPLETED | Normal-only calibration on the chronological calibration period | `Detector.train()` | Test captures the calibration score input and asserts it equals the normal calibration matrix | Cost-based threshold tuning | Medium |
| Low/medium/high classification | COMPLETED | Threshold comparator | `Detector.score()` | API and UI | Separate medium+high policy | Low |
| Top-3 feature deviations | COMPLETED | Squared standardized residual ranking | `Detector.score()` | API detail test | Causal/explainable interpretation | Medium |
| Precision/recall/F1/FPR | COMPLETED | Synthetic label confusion counts | `main.py:evaluation()` | Live persisted metrics | Real evaluation | High |
| Confusion matrix | COMPLETED | TP/FP/TN/FN | `evaluation()` | Counts inspected | Confusion visualization/export | Medium |
| FastAPI health | COMPLETED | Readiness endpoint | `main.py:health()` | Live and TestClient pass | Dependency/database readiness detail | Low |
| FastAPI overview | COMPLETED | KPIs/trends/categories/recent | `main.py:overview()` | Live and test pass | Date range and cache | Low |
| Transaction pagination/filter | COMPLETED | SQL pagination/search/risk | `main.py:transactions()` | Test API pass | Sorts, cursor, transaction count | Low |
| Transaction detail | COMPLETED | Stored row plus live analysis/review | `main.py:transaction_detail()` | 404 test pass | Review history/audit | Medium |
| Stateless analysis | COMPLETED | New unsaved Lab purchase; only strictly earlier same-user history is passed to the VAE; response says `saved:false` | `main.py:analyze()` | Focused API test checks history isolation, response fields and unchanged row count | Batch scoring/import | Medium |
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

