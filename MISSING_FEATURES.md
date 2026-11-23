# Missing Features and Deficiencies

Status values are restricted to **COMPLETED**, **PARTIALLY COMPLETED**, **NOT IMPLEMENTED**, **NOT VERIFIED**.

## High-Priority Findings

| Requirement | Actual implementation | Source file and function | Evidence or test result | Missing work | Priority | Status |
|---|---|---|---|---|---|---|
| Real purchase dataset | Only in-process synthetic records | `backend/app/synthetic.py:generate()` | README explicitly says all seeded data is synthetic | Obtain approved real/benchmarked transactions or a documented public dataset | High | NOT IMPLEMENTED |
| Per-user rolling behavior | Shared point-in-time builder calculates earlier-only spend, counts, elapsed time and category shift | `model.py:features()`, `feature_matrix()` | Automated chronology, boundary, tie, cold-start and leakage tests | Production identity isolation and real traffic validation | High | COMPLETED (prototype) |
| Independent real-world evaluation | Evaluation uses injected synthetic labels | `main.py:evaluation()` | TP 153, FP 12, TN 1033, FN 2 | Real labels, held-out weeks, cost curve and baseline comparison | High | NOT IMPLEMENTED |
| Authentication/RBAC | None; endpoints public | `main.py` | CORS only; no auth dependency | Login, roles, API authorization and protected retrain/reset/review operations | High | NOT IMPLEMENTED |
| Browser end-to-end testing | Build only | `frontend/package.json` | No browser framework config/test | Playwright or Cypress flows for overview, filters, detail, lab and review | High | NOT IMPLEMENTED |
| Temporal model evaluation | Chronological 70/15/15 periods; normal-only fit/calibration and held-out mixed test | `main.py:update_demo()`, `model.py:Detector.train()` | Held-out synthetic test partition evaluated | More seeds and real out-of-time evaluation | High | PARTIALLY COMPLETED |
| Experiment tracking | Fixed single training run | `main.py:update_demo()` | Training at 24 epochs | Seed sweeps, latent dimensions, beta/KL, threshold baselines | High | NOT IMPLEMENTED |
| Dataset cleaning pipeline | Minimal API Pydantic validation | `main.py:TransactionInput` | No CSV/import or missing-value scan | Schema validation, missingness, duplicates, range and consistency checks | High | NOT IMPLEMENTED |
| False-positive governance | Synthetic metrics only | `evaluation()`, `review_transaction()` | FPR 0.0115 synthetic only | Cost threshold, reviewer feedback and performance drift monitoring | High | NOT IMPLEMENTED |

## Medium-Priority Findings

| Requirement | Actual implementation | Source file and function | Evidence or test result | Missing work | Priority | Status |
|---|---|---|---|---|---|---|
| Real amount baselines | Absolute log amount only | `model.py:features()` | No z-score or prior spend feature | Per-user average/median and deviation | Medium | NOT IMPLEMENTED |
| Timing history | Hour cyclic encoding | `features()` | Timestamp stored | Inter-purchase interval, weekday, weekend and burst features | Medium | NOT IMPLEMENTED |
| Per-user device/payment history | Raw counts only | `features()` | No normalized or historical known-item flags | Known-device and payment ratios | Medium | NOT IMPLEMENTED |
| Causal explanations | Top reconstruction residuals | `Detector.score()` | UI explicitly calls residuals descriptive | SHAP/feature attribution or causal baseline | Medium | PARTIALLY COMPLETED |
| Threshold analysis | Two fixed percentile thresholds | `Detector.train()` | 95/99 values in checkpoint/API | PR/ROC curves, sensitivity and operating-cost analysis | Medium | PARTIALLY COMPLETED |
| Evaluation visualizations | Metric cards/confusion cards | `main.jsx:ModelPage` | No plots for ROC/PR/training | ROC, PR, calibration and residual plots | Medium | NOT IMPLEMENTED |
| Model operations | Manual retrain/reset | `main.py:update_demo()` | UI action and test | Versioning, rollback, scheduled retraining and drift | Medium | NOT IMPLEMENTED |
| API audit history | Review upsert replaces prior review | `db.py:reviews`, `main.py:review_transaction()` | One active review per transaction | Immutable reviewer/audit log and timestamps | Medium | NOT IMPLEMENTED |
| Checkpoint validation | Local trusted torch load | `model.py:load()` | Weights-only load | Schema check, checksum and downgrade compatibility | Medium | PARTIALLY COMPLETED |
| Frontend modularity | All components in one JSX file | `frontend/src/main.jsx` | 65-line source region includes entire UI | Component splitting and testable modules | Medium | NOT IMPLEMENTED |
| Frontend mutation UX | Loading and confirmation only for retrain/reset | `App`, `Detail`, `Lab` | General toast/error handling | Consistent pending disables and success/failure states | Medium | PARTIALLY COMPLETED |
| API test coverage | 1 integration smoke test | `backend/tests/test_api.py` | 1 pass | Unit/model/DB/invalid-input/concurrency tests | Medium | PARTIALLY COMPLETED |
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

