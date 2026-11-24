# Missing Features and Deficiencies

Status values are restricted to **COMPLETED**, **PARTIALLY COMPLETED**, **NOT IMPLEMENTED**, **NOT VERIFIED**.

## High-Priority Findings

| Requirement | Actual implementation | Source file and function | Evidence or test result | Missing work | Priority | Status |
|---|---|---|---|---|---|---|
| Real purchase dataset | Only in-process synthetic records | `backend/app/synthetic.py:generate()` | README explicitly says all seeded data is synthetic | Obtain approved real/benchmarked transactions or a documented public dataset | High | NOT IMPLEMENTED |
| Per-user rolling behavior | Shared point-in-time builder calculates earlier-only spend, counts, elapsed time and category shift | `model.py:features()`, `feature_matrix()` | Tests cover math, user-history API lookup, chronology, boundaries, ties and cold starts | Production identity isolation and real traffic validation | High | COMPLETED |
| Independent real-world evaluation | Evaluation uses injected synthetic labels and a chronological held-out synthetic period | `main.py:evaluation()` | Synthetic metrics only; see `TEST_RESULTS.md` | Real labels, genuinely independent real data, cost curve and baseline comparison | High | NOT IMPLEMENTED |
| Authentication/RBAC | None; endpoints public | `main.py` | CORS only; no auth dependency | Login, roles, API authorization and protected retrain/reset/review operations | High | NOT IMPLEMENTED |
| Lab submission contract | New, stateless purchase analysis; same-user rows strictly earlier than optional timestamp only | `main.py:analyze()`, `TransactionInput` | API test checks earlier-history filtering, no target-ID field, unchanged transaction count and `saved:false` | Persisted purchase ingestion and replay are not supported by this endpoint | Medium | COMPLETED |
| Browser end-to-end testing | Build only | `frontend/package.json` | No browser framework config/test | Playwright or Cypress flows for overview, filters, detail, lab and review | High | NOT IMPLEMENTED |
| Temporal model evaluation | Chronological 70/15/15 periods; normal-only fit/calibration and held-out mixed test | `main.py:chronological_partitions()`, `model.py:Detector.train()` | Tests assert production partition ordering, normal-only scaler fitting, normal-only calibration, and chronological stored-transaction rescoring; held-out evaluation replay is not directly tested | More seeds and real out-of-time evaluation | High | PARTIALLY COMPLETED |
| Experiment tracking | Fixed single training run | `main.py:update_demo()` | Training at 24 epochs | Seed sweeps, latent dimensions, beta/KL, threshold baselines | High | NOT IMPLEMENTED |
| Dataset cleaning pipeline | Minimal API Pydantic validation | `main.py:TransactionInput` | No CSV/import or missing-value scan | Schema validation, missingness, duplicates, range and consistency checks | High | NOT IMPLEMENTED |
| False-positive governance | Synthetic metrics only | `evaluation()`, `review_transaction()` | Current synthetic held-out result is documented in `TEST_RESULTS.md` | Cost threshold, reviewer feedback and performance drift monitoring | High | NOT IMPLEMENTED |

## Medium-Priority Findings

| Requirement | Actual implementation | Source file and function | Evidence or test result | Missing work | Priority | Status |
|---|---|---|---|---|---|---|
| Real amount baselines | Historical average, population SD and signed relative deviation are implemented | `model.py:features()` | Unit-tested against prior transactions | Median baseline and refund/chargeback ratios | Medium | PARTIALLY COMPLETED |
| Timing history | Hour encoding and elapsed time since prior purchase are implemented | `features()` | Window/history tests | Weekday, weekend and seasonal features | Medium | PARTIALLY COMPLETED |
| Per-user device/payment history | Raw counts only | `features()` | No normalized or historical known-item flags | Known-device and payment ratios | Medium | NOT IMPLEMENTED |
| Causal explanations | Top reconstruction residuals | `Detector.score()` | UI explicitly calls residuals descriptive | SHAP/feature attribution or causal baseline | Medium | PARTIALLY COMPLETED |
| Threshold analysis | Two fixed percentile thresholds | `Detector.train()` | 95/99 values in checkpoint/API | PR/ROC curves, sensitivity and operating-cost analysis | Medium | PARTIALLY COMPLETED |
| Evaluation visualizations | Metric cards/confusion cards | `main.jsx:ModelPage` | No plots for ROC/PR/training | ROC, PR, calibration and residual plots | Medium | NOT IMPLEMENTED |
| Model operations | Manual retrain/reset | `main.py:update_demo()` | UI action and test | Versioning, rollback, scheduled retraining and drift | Medium | NOT IMPLEMENTED |
| API audit history | Review upsert replaces prior review | `db.py:reviews`, `main.py:review_transaction()` | One active review per transaction | Immutable reviewer/audit log and timestamps | Medium | NOT IMPLEMENTED |
| Checkpoint validation | Weights-only load checks feature schema version/name and scaler dimensions | `model.py:load()` | Old 11-feature checkpoint rejection tested | Checksums/signatures, full payload validation and corrupt-checkpoint recovery tests | Medium | PARTIALLY COMPLETED |
| Frontend modularity | All components in one JSX file | `frontend/src/main.jsx` | 65-line source region includes entire UI | Component splitting and testable modules | Medium | NOT IMPLEMENTED |
| Frontend mutation UX | Loading and confirmation only for retrain/reset | `App`, `Detail`, `Lab` | General toast/error handling | Consistent pending disables and success/failure states | Medium | PARTIALLY COMPLETED |
| API/model test coverage | API integration plus focused feature, partition, replay and migration tests | `backend/tests/` | Exact current run recorded in `TEST_RESULTS.md` | More malformed-input, concurrency and security tests | Medium | PARTIALLY COMPLETED |
| Dependency reproducibility | Python ranges and npm lock | `backend/requirements.txt`, lockfiles | No backend package-lock should belong in Python project | Use requirements lock and remove untracked `backend/package-lock.json` | Medium | PARTIALLY COMPLETED |

## Low-Priority Findings

| Requirement | Actual implementation | Source file and function | Evidence or test result | Missing work | Priority | Status |
|---|---|---|---|---|---|---|
| Explicit category encoding | Workout is represented by both category indicators false | `model.py:features()` | No loss of two-category demonstrated | Three-column one-hot category or category embedding | Low | NOT IMPLEMENTED |
| Bundle optimization | Vite build emits 590.61 kB JS | `frontend/package.json` | 500 kB warning | Lazy-load heavy Recharts/dashboard sections | Low | PARTIALLY COMPLETED |
| Pytest cache warning | Cache directory permissions warning | `backend/pytest.ini` | Test passes with 2 warnings | Ensure cache directory permissions or disable cache | Low | PARTIALLY COMPLETED |

## Data/ML Clarifications

- "Fraud" in this project means an injected synthetic attack pattern. It is not confirmed fraudulent behavior.
- Medium-risk is a threshold band, but evaluation counts only high-risk predictions as positive.
- Review records do not update model labels or retraining data.
- No real payment processor, PCI boundary or personal financial data is integrated.

