# Working with this repository in Codex

This is an executable full-stack educational fraud anomaly-detection prototype, not a standalone prompt. Open the project root in Codex / VS Code.

- Python API: `backend/app/main.py` (FastAPI routes), `backend/app/model.py` (PyTorch VAE), `backend/app/synthetic.py` (synthetic data), `backend/app/db.py` (SQLite).
- React UI: `frontend/src/main.jsx` and `frontend/src/style.css`.
- Keep dataset synthetic; do not introduce real customer/payment secrets or assert anomaly equals fraud.
- Start backend with `cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload`.
- Start frontend with `cd frontend && npm install && npm run dev`.
- Run `cd backend && pytest -q` after backend changes; run `cd frontend && npm run build` after frontend changes.
- The frontend expects `/api` via the Vite proxy. Schema is defined in `TransactionInput`.
- API docs at `http://localhost:8000/docs`.

Suggested next Codex prompts:
1. "Add authentication and an RBAC-aware investigator account flow, with tests and no hardcoded passwords."
2. "Add a reproducible batch CSV import pipeline with strict data validation and an opt-in privacy-safe mapping interface."
3. "Split the React dashboard into modular components and add React Testing Library UI tests."
