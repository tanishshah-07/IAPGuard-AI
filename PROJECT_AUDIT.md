# IAPGuard AI - Complete Technical Audit

## Milestone 1 implementation update (2026-11-24)

Per-user point-in-time behavioral features are now implemented in `backend/app/model.py`; synthetic records use repeated user histories; training/calibration/test periods are chronological; and `/api/analyze` consults stored history without persisting the request. See the updated architecture and test results for the feature schema, split definitions, migration, test run and synthetic held-out metrics. Remaining concerns include unauthenticated client-supplied user IDs, synthetic-only evaluation, and non-production deployment controls.

**Audit date:** 2026-11-23  
**Scope:** Initial read-only technical audit; no existing source files were modified.  
**Environment:** Windows, repository root `iapguard-ai`.

## Executive Summary

The project is a functional educational full-stack prototype. It has a synthetic data generator, SQLite persistence, a PyTorch VAE, FastAPI endpoints, and a React/Vite dashboard. The backend test passes and the frontend production build succeeds.

It is **not a production fraud detector** and should not be presented as one. Behavioral history is implemented for this prototype; major gaps remain real or independent dataset sourcing, broad validation, authentication and authorization, browser/UI tests, drift monitoring, model registry/version management, and real-world evaluation.

**Overall completion:** **PARTIALLY COMPLETED**

## A. Project Structure

| Area | Important files | Purpose |
|---|---|---|
| Documentation | `README.md`, `CODEX.md` | Project setup, architecture, demo behavior and limitations |
| Backend application | `backend/app/main.py` | FastAPI lifespan, Pydantic schemas, REST endpoints, retraining/reset orchestration |
| VAE | `backend/app/model.py` | Feature conversion, scaler, PyTorch VAE, score and checkpoint handling |
| Synthetic data | `backend/app/synthetic.py` | Reproducible synthetic normal/anomaly records |
| Persistence | `backend/app/db.py` | SQLite initialization, connection, transaction/review schemas |
| Backend test | `backend/tests/test_api.py` | Temporary-data end-to-end API smoke test |
| Frontend | `frontend/src/main.jsx` | Single-file React application for all dashboard pages/modals |
| Frontend API client | `frontend/src/api.js` | Fetch wrapper, API URL resolution and error parsing |
| Styling | `frontend/src/style.css` | Dashboard layout and components |
| Vite | `frontend/vite.config.js`, `frontend/package.json` | React build/dev configuration and dependencies |
| Runtime startup | `start-backend.bat/.sh`, `start-frontend.bat/.sh` | Local launcher scripts |
| Persistence assets | `backend/data/iapguard.sqlite3`, `backend/data/vae.pt` | Generated demo database and model checkpoint |
| Generated artifacts | `frontend/dist/`, `frontend/node_modules/`, `backend/.venv/`, logs | Build/dependency/runtime artifacts, excluded by `.gitignore` |

### Source and generated-file findings

| Requirement | Actual implementation | Source file and function | Evidence or test result | Missing work | Priority | Status |
|---|---|---|---|---|---|---|
| Backend source structure | Small, coherent Python package under `backend/app` | `backend/app/main.py`, `model.py`, `synthetic.py`, `db.py` | Five application modules; no duplicate model implementations found | Split large API/UI modules for maintainability | Low | COMPLETED |
| Frontend modularity | Entire UI is one large JSX file | `frontend/src/main.jsx:App()` and subsequent component functions | Every page/component is in one 65-line compressed source region, but one source region contains all UI | Split Overview, Transactions, Alerts, Lab, Model and Detail components | Low | PARTIALLY COMPLETED |
| Unused or duplicate code | No obvious duplicate implementation of the VAE or API client | Repository-wide source search | Main implementation count: one VAE, one synthetic generator, one SQLite module | Add automated unused-import/dead-code scan | Low | NOT VERIFIED |
| Generated dependencies/secrets | Virtualenv, node_modules and dist are local/generated and ignored | `.gitignore` | Git status showed backend/package-lock.json untracked and 11 tracked files modified before audit | Remove unnecessary untracked generated files and package-lock consistency review | Medium | PARTIALLY COMPLETED |
| Frontend/backend connection | Browser calls `/api`; Vite proxies it to FastAPI | `frontend/src/api.js:api()`, `frontend/vite.config.js` | `/api` proxy is configured | Production same-origin or CORS deployment is not run-tested | Medium | COMPLETED |
| Frontend/database connection | React never accesses SQLite directly; all data uses REST | `frontend/src/api.js`, `backend/app/db.py:connect()` | API is sole data boundary | No production-grade access control or audit log | High | COMPLETED |

## B. Dataset

**Source:** `backend/app/synthetic.py:generate()` only. No external CSV, real IAP records, acquisition code or data documentation exists in this repository.

**Nature:** 100% synthetic, explicitly seeded and documented as demo data.

| Requirement | Actual implementation | Source file and function | Evidence or test result | Missing work | Priority | Status |
|---|---|---|---|---|---|---|
| Dataset source | Reproducible in-process generator with user-specific spending and cadence | `backend/app/synthetic.py:generate()` | Seed 27 creates 1,200 chronologically ordered rows | Document and acquire real/approved dataset where applicable | High | COMPLETED |
| Synthetic/real distinction | Synthetic by default and labeled `source='demo'`, `is_synthetic_fraud` | `generate()`, `DB transactions` | Persisted database: 1,200 records; 155 synthetic-fraud labels | Real-data ingestion/privacy controls | High | COMPLETED |
| Transaction fields | id, user, timestamp, amount, hour, account age, 24h count, failed attempts, 7d methods/devices, mismatch, purchase type, score/risk/status/label/source | `backend/app/db.py:initialize()` | SQLite schema and data inspected | Real payment identifiers and timestamps at required granularity | Medium | COMPLETED |
| Cleaning/preprocessing | Direct numeric conversion, feature log transforms and `StandardScaler` | `backend/app/model.py:features()`, `train()` | No missing-value imputation or outlier-validation pipeline | Missing/invalid value handling, schema validation for stored records | High | PARTIALLY COMPLETED |
| Missing values | API Pydantic rejects omitted required fields; synthetic generator complete | `main.py:TransactionInput`, `synthetic.py:generate()` | Persisted database null score count was zero; score is not a raw input field | Dataset-wide missingness report and imputation policy | High | NOT VERIFIED |
| Data consistency | SQLite ID primary key, foreign-key review key, indexes | `db.py:initialize()` | 1,200 unique IDs; no duplicate IDs; 165 high, 35 medium, 1,000 low | Domain constraints and transaction integrity tests | Medium | COMPLETED |
| Per-user behavioral history | Prototype point-in-time builder computes counts, spend baseline, elapsed time, windows and category shift | `model.py:features()`, `feature_matrix()` | Unit tests cover math, chronology, equal timestamps, future/self exclusion and cold start | Broader real-world sequence validation and identity isolation | High | COMPLETED |
| Data leakage | Synthetic `is_synthetic_fraud` is not in features; behavioral features are strict earlier-only | `model.py:FEATURE_NAMES`, `features()`, `feature_matrix()` | Tests flip labels, exclude future/equal-time/self rows | More seeds and real chronological validation | Medium | COMPLETED |

**Current VAE inputs:** 19 ordered values are defined by `FEATURE_NAMES` in `backend/app/model.py`: the 10 retained amount/time/account/failure/payment/device/geo/category fields followed by prior transaction count, historical average amount, historical amount population SD, relative amount deviation, elapsed time since previous purchase, prior 1h/24h/7d counts, and category change from the historical mode. `purchases_24h` remains an API/database compatibility field but is not a VAE input.

**Leaky/unrealistic concern:** Fraud records are generated by choosing independent synthetic attack modes, so the evaluation may be highly separable and optimistic. The unsupervised model is trained only on `fraud_rate=0` records, while evaluation uses data with `fraud_rate=.12`.

## C. Feature Engineering

| Feature | Calculation | Implementation evidence | Status |
|---|---|---|---|
| Log purchase amount | `log1p(amount)` | `backend/app/model.py:features()` | COMPLETED |
| Purchase hour sine | `sin(2*pi*hour/24)` | `features()` | COMPLETED |
| Purchase hour cosine | `cos(2*pi*hour/24)` | `features()` | COMPLETED |
| Log account age | `log1p(account_age_days)` | `features()` | COMPLETED |
| Per-user history inputs | Strict earlier same-user values; counts and nonnegative amount/time values use `log1p`, relative amount deviation is signed and normalized by historical mean | `features()` / `_history_for()` | COMPLETED |
| 24h failed payments | Raw count | `features()` | COMPLETED |
| 7d payment methods | Raw distinct count | `features()` | COMPLETED |
| 7d device changes | Raw distinct count | `features()` | COMPLETED |
| Billing country mismatch | Boolean converted to 1/0 | `features()` | COMPLETED |
| Subscription category | 1 if subscription else 0 | `features()` | COMPLETED |
| Coaching category | 1 if coaching else 0 | `features()` | COMPLETED |

| Requirement | Actual implementation | Source file and function | Evidence or test result | Missing work | Priority | Status |
|---|---|---|---|---|---|---|
| Purchase frequency | Prior transaction count and rolling 1h/24h/7d counts are derived from ordered same-user history | `synthetic.py:generate()`, `model.py:features()` | Historical calculation and replay tests | Real traffic validation and additional frequency measures | High | COMPLETED |
| Transaction timing | Cyclic purchase hour and log seconds since previous same-user purchase | `features()`, `generate()` | Timestamp/hour consistency and chronological replay tests | Weekday, weekend and seasonality features | High | PARTIALLY COMPLETED |
| Amount behavior | Log amount, historical average, population SD and signed relative deviation | `features()` | Historical calculation tests | Median baseline, refund and chargeback ratios | High | COMPLETED |
| Failed payments | Count supplied per record | `features()` | Raw count only | Failure rate, consecutive failures and recency | Medium | COMPLETED |
| Device behavior | Count supplied per record | `features()` | Raw count only | Known-device ratio, new device, velocity and device reuse | High | COMPLETED |
| Payment behavior | Count supplied per record | `features()` | Raw count only | Known-payment ratio and payment-method changes over time | Medium | COMPLETED |
| Purchase category | Two one-hot-like indicators | `features()` | Workout is represented by zeros for both | Explicit workout indicator or complete one-hot encoding | Low | COMPLETED |
| User behavioral history | Shared point-in-time builder creates 9 behavioral inputs; generated users have persistent spend/cadence/category profiles | `model.py:features()`, `feature_matrix()`, `synthetic.py:generate()` | Unit/API tests cover as-of history and same-user filtering | Real traffic validation and authentication/tenant isolation | High | COMPLETED |

## D. PyTorch VAE

| Requirement | Actual implementation | Source file and function | Evidence or test result | Missing work | Priority | Status |
|---|---|---|---|---|---|---|
| PyTorch implementation | `nn.Linear` VAE | `backend/app/model.py:VAE` | Actual forward pass and checkpoint weights | Versioned architecture metadata | Medium | COMPLETED |
| Encoder | 19 -> 32 -> 16 -> latent parameters | `VAE.__init__/forward` | ReLU encoder | Encoder ablation or capacity tuning | Low | COMPLETED |
| Latent space | 5 dimensions with `mu` and `logvar` | `VAE` | Reparameterization in training and mean in inference | Latent visualization and interpretability | Medium | COMPLETED |
| Reparameterization | `z = mu + randn * exp(0.5*logvar)` | `VAE.forward()` | Training-only sampling | Not missing | Low | COMPLETED |
| Reconstruction loss | Mean squared standardized residual | `train()` | `mean((reconstructed-batch)^2)` | Per-feature weighted reconstruction where appropriate | Medium | COMPLETED |
| KL divergence | Closed-form diagonal Gaussian KL | `train()` | `-0.5 mean sum(1+logvar-mu^2-exp(logvar))` | Beta scheduling/annealing experiment | Medium | COMPLETED |
| Normal-only training | Normal rows from earliest 70% chronological period of the synthetic demo | `main.py:update_demo()`, `Detector.train()` | 70/15/15 train/calibration/test; only normal rows fit | Cross-validation and more seeds | High | COMPLETED |
| Train/calibration/test split | Chronological 70/15/15 split of synthetic data | `Detector.train()` | Scaler fit on train normals; thresholds on calibration normals; metrics on later mixed test | Real out-of-time validation | High | COMPLETED |
| Scaler fitting | Fit on normal training rows only | `train()` | Direct test compares scaler mean/sample count to expected normal train features | Checksum and transformer-version metadata | Medium | COMPLETED |
| Checkpoint save/load | Atomic temp replace; CPU weights-only load with feature schema/name and scaler dimension checks | `save()`, `load()` | Old 11-feature schema rejection test; health readiness | Checksum/signature and complete payload validation | Medium | COMPLETED |

## E. Anomaly Detection

| Requirement | Actual implementation | Source file and function | Evidence or test result | Missing work | Priority | Status |
|---|---|---|---|---|---|---|
| Anomaly score | Mean squared standardized reconstruction residual | `Detector.raw_scores()`, `score()` | Deterministic at inference using latent mean | Calibrated probability or uncertainty interval | High | COMPLETED |
| Threshold selection | 95th and 99th percentile on held-out normals | `Detector.train()` | Persisted thresholds in checkpoint/model info | Threshold sensitivity and operating-point selection | High | COMPLETED |
| Risk bands | high >= 99th; medium >= 95th; otherwise low | `Detector.score()` | API/UI/test coverage | Confirmed-fraud workflow is separate from score | Medium | COMPLETED |
| Feature deviations | Per-feature standardized squared residual, top 3 | `Detector.score()` | Returned in detail and lab UI | Partial dependence/SVDD/Shapley or correlated residual analysis | Medium | COMPLETED |
| False positives/negatives | Synthetic confusion metrics and human review records | `main.py:evaluation()`, `review_transaction()` | Synthetic result: TP 153, FP 12, TN 1033, FN 2 | Real labels, reviewer adjudication and cost-sensitive analysis | High | PARTIALLY COMPLETED |
| Review handling | Resolution and note persisted to SQLite | `review_transaction()` | Test wrote and reloaded a review | Authentication, review history, analyst and audit trail | High | COMPLETED |

## F. Model Evaluation

The legacy all-row result below is retained for historical comparison only; it is not the current chronological test metric:

- Precision 0.9273
- Recall 0.9871
- F1 0.9563
- False-positive rate 0.0115
- Confusion matrix: TP 153, FP 12, TN 1033, FN 2

It used all seeded demo rows and is not comparable to the later held-out metric documented in `TEST_RESULTS.md`. Neither result establishes real fraud efficacy.

| Requirement | Actual implementation | Source file and function | Evidence or test result | Missing work | Priority | Status |
|---|---|---|---|---|---|---|
| Precision/recall/F1/FPR | Calculated at high-risk operating point | `main.py:evaluation()` | Live API returned synthetic metrics | Medium/high/low multiclass or per-attack metrics | High | COMPLETED |
| Confusion matrix | Four counts | `evaluation()` | Live API counts listed above | Visual and downloadable confusion matrix | Medium | COMPLETED |
| Real/synthetic labels | Synthetic injected anomaly labels | `synthetic.py:generate()` | `is_synthetic_fraud` and demo warning | Real or expert-confirmed labels | High | PARTIALLY COMPLETED |
| Experiments | Fixed 24-epoch seeded synthetic demo training | `update_demo()` | Training seed and chronological split are recorded in model metadata | Hyperparameter sweeps, multiple seeds, baselines and ablations | High | NOT IMPLEMENTED |
| Visualizations | Dashboard charts and metric cards | `frontend/src/main.jsx:Overview`, `ModelPage` | No training curve, PR/ROC, residual or calibration plots | Training and threshold visualizations | Medium | PARTIALLY COMPLETED |

## G. FastAPI Backend

| Endpoint | Behavior | Validation/error handling | Status |
|---|---|---|---|
| `GET /api/health` | Health and model readiness | Returns demo status | COMPLETED |
| `GET /api/overview` | KPIs, daily trend, categories, recent rows | SQLite read; no explicit catch | COMPLETED |
| `GET /api/transactions` | Filter/search/pagination | Pydantic-like FastAPI query constraints | COMPLETED |
| `GET /api/transactions/{id}` | Detail plus live score and prior review | 404 for missing row | COMPLETED |
| `POST /api/analyze` | New unsaved Lab purchase; looks up only strictly earlier same-user rows | Request schema has no target ID; response retains `analysis`, `transaction`, `saved:false`, `notice` | COMPLETED |
| `POST /api/transactions/{id}/review` | Insert/update review | 404 for unknown tx; resolution/note constraints | COMPLETED |
| `GET /api/model` | Architecture/training/threshold metadata | Model-ready handling | COMPLETED |
| `POST /api/model/retrain` | Chronological normal-only fit/calibration and rescore stored rows using history | Lock protects model state | COMPLETED |
| `GET /api/evaluation` | Synthetic metrics/confusion | Available flag when no labels | COMPLETED |
| `POST /api/demo/reset` | Delete/seed and retrain | Lock plus transaction writes | COMPLETED |

`POST /api/analyze` is for a new, unsaved Lab purchase only. The request schema has no target ID; the endpoint queries same-user history, filters to timestamps strictly before the supplied/default UTC timestamp, returns the established response fields with `saved:false`, and does not insert the purchase. Stored-row rescoring/detail scoring pass the stored ID to the shared feature builder, which excludes the target.

SQLite operations use parameterized SQL and context-managed rollback. There is no authentication, role checking, rate limiting, immutable audit history or concurrent API integration test. CORS is explicitly allowlisted and credentials are disabled.

## H. React Frontend

The frontend implements:

- Overview: KPIs, area chart, risk distribution, recent transactions
- Transactions: search, risk filter, pagination and CSV export
- Alerts: high-risk queue
- AI Detection Lab: form, live API analysis and deviations
- Model insights: thresholds and synthetic evaluation
- Detail drawer: transaction data, deviations and review form

| Requirement | Actual implementation | Source file and function | Evidence or test result | Missing work | Priority | Status |
|---|---|---|---|---|---|---|
| Page/component coverage | Five routed-by-state pages plus detail drawer | `frontend/src/main.jsx` | All named pages render | Formal component tests and route URLs | Medium | COMPLETED |
| API integration | Shared fetch wrapper | `frontend/src/api.js:api()` | Live API and TestClient coverage | E2E browser run | Medium | COMPLETED |
| Nonfunctional buttons | No obvious placeholder buttons found | Source inspection | Buttons call implemented navigation/API/export actions | Browser verify all forms and buttons | Low | NOT VERIFIED |
| Loading/error states | Initial loading, per-Lab loading, page API errors and toast | `App`, `Lab`, `Transactions`, `Alerts` | Source present | Retry/pending consistency on every mutation | Medium | COMPLETED |
| Dashboard functionality | Live data and charts | `Overview`, `Transactions`, `Alerts` | Build passes | Real-time refresh, export all pages, date filters | Medium | PARTIALLY COMPLETED |

## I. Testing and Security

| Requirement | Actual implementation | Source file and function | Evidence or test result | Missing work | Priority | Status |
|---|---|---|---|---|---|---|
| Backend tests | API integration and focused model/history/database tests using temporary or in-memory data | `backend/tests/` | Current results in `TEST_RESULTS.md`; coverage includes API history isolation, production partitioning, normal-only scaling/calibration and chronological replay | More malformed-data, concurrency and security tests | High | PARTIALLY COMPLETED |
| Frontend build | Vite production build | `frontend/package.json:scripts.build` | Success: 1,993 modules; 590.61 kB main JS chunk; 500 kB warning | Bundle splitting and frontend tests | Medium | COMPLETED |
| Dependency configuration | Python requirements and npm lockfiles | `backend/requirements.txt`, `frontend/package-lock.json` | Backend ranges and frontend lock exist | Pin reproducible Python versions; backend package-lock untracked | Medium | COMPLETED |
| Secrets | No embedded credentials found | Repository search | `.env.example` contains no secret values | Secrets baseline and CI scanning | High | COMPLETED |
| Authentication/security | No auth | `main.py` | Explicit demo-only and no auth in README | Authentication, authorization, rate limiting, CSRF, audit logs | High | NOT IMPLEMENTED |
| Generated files | Data/checkpoints/logs, dependencies and dist | `.gitignore` | Backend/data, .venv, node_modules and dist ignored | Verify build artifacts and logs are not committed | Medium | COMPLETED |
| Browser testing | Not performed | N/A | No Playwright/Cypress/RTL configuration found | Perform browser E2E and component tests | High | NOT IMPLEMENTED |

## J. Assignment Compliance

The official project rubric was not present in the repository. Compliance below compares against the requirements in the user's assignment prompt.

| Requirement | Status | Auditor assessment |
|---|---|---|
| Purchase dataset preparation | PARTIALLY COMPLETED | Synthetic generator is complete; real acquisition, cleaning and audit pipeline are absent |
| Behavioral feature engineering | COMPLETED | Prototype provides 19 inputs including strict earlier-only per-user spending, frequency, recency and category history |
| PyTorch VAE | COMPLETED | Real PyTorch implementation and persisted checkpoint |
| Unsupervised anomaly detection | COMPLETED | Normal-only training and reconstruction anomaly score |
| Anomaly scoring and threshold | COMPLETED | 95th/99th percentile threshold bands |
| FastAPI integration | COMPLETED | Comprehensive demo API |
| Model evaluation and fraud analysis | PARTIALLY COMPLETED | Synthetic metrics/confusion exist; real evaluation absent |
| Final documentation and presentation | COMPLETED | README/CODEX provide documentation and viva guide; presentation artifact absent |

## Top-Level Findings

1. **High:** Behavioral history is now computed for the prototype; user IDs remain client-supplied and unauthenticated.
2. **High:** Dataset is entirely synthetic; no real-world or independent evaluation exists.
3. **High:** No authentication or authorization around the admin/retraining/reset APIs.
4. **High:** Evaluation metrics are optimistic synthetic results, not real fraud performance.
5. **High:** Browser and frontend test coverage is absent.
6. **High:** Evaluation is now chronological but remains synthetic and single-seed, not a real independent evaluation.
7. **Medium:** Feature residual explanations are reconstruction residuals, not causal evidence.
8. **Medium:** `main.py:update_demo()` hardcodes 24 epochs while README calls 28 in one architecture description; startup report controls actual behavior.
9. **Medium:** Checkpoint feature schema and scaler dimensions are checked; checksums, complete payload/threshold validation and model registry controls remain absent.
10. **Medium:** Generated SQLite/model data and logs can be stale across code changes without explicit migrations/versioning.

