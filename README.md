# Billing Web App

A full-stack billing application built with FastAPI and React.

Features:
- customer management
- invoice creation with line items
- payment tracking
- revenue dashboard
- SQLite database for local development

## Tech stack
- Backend: FastAPI + SQLAlchemy + SQLite
- Frontend: React + Vite

## Quick start

### 1. Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Frontend
```bash
cd frontend
npm install
npm run dev -- --host 0.0.0.0
```

Then open:
- frontend: http://localhost:5173
- backend API: http://localhost:8000/docs

## Default data flow
- Create customers from the UI
- Create invoices with customer selection and line items
- Record payments against invoices
- Monitor dashboard stats and outstanding balance

## Notes
The app uses SQLite so it works out of the box for local development without requiring PostgreSQL or MySQL.
