# CX Reply Assistant

React and FastAPI demo for customer support across Nike and Adidas, using fictional brand policies, PostgreSQL, and Gemini.

## Features

- Brand-specific conversations, customer messages, and order context.
- Policy CRUD and retrieval of relevant policies for AI drafts.
- Generate, edit, regenerate, and approve replies with saved generation history.
- Review fallbacks for missing context and expired policy windows.
- Admin and customer login, Argon2 password hashes, and server-side session and ownership checks.

## Local setup (Windows CMD)

Install Python 3.12, Node.js, and PostgreSQL. Create a PostgreSQL database named `cx_reply_assistant` first.

From the repository root:

```bat
cd backend
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
copy .env.example .env
```

Edit `backend/.env` with your PostgreSQL credentials and Gemini API key. Never commit this file.

```bat
.venv\Scripts\python.exe -m alembic upgrade head
.venv\Scripts\python.exe -m app.seed
.venv\Scripts\python.exe -m app.seed_scenarios
.venv\Scripts\python.exe -m app.seed_admin
.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

In a second CMD terminal, from the repository root:

```bat
cd frontend
npm ci
npm run dev
```

Open http://localhost:5173. API documentation: http://127.0.0.1:8000/docs.

The local demo admin credentials in `.env.example` are `admin` / `admin`. Register a customer to create a separate customer profile and conversation for the selected brand. Existing seeded customer profiles do not automatically have login accounts. New registrations do not create orders.

For reviewer access to the fictional Meera Patel profile, run `python -m app.seed_demo_login` after the original seed. Hosted startup does this automatically. Choose Customer and log in with username `meera.demo` and password `MeeraDemo2026!`. This intentionally shared demo login can access only Meera's Adidas conversation and order. It must contain only fictional data. Meera's original 20-day-old order demonstrates the expired-refund review fallback; use a shipping question to demonstrate generation that does not require refund eligibility.

## Verification

From `backend`:

```bat
.venv\Scripts\python.exe -m alembic check
.venv\Scripts\python.exe -m app.check_auth
.venv\Scripts\python.exe -m app.check_retrieval
```

From `frontend`:

```bat
npm run lint
npm run build
```

## Structure and schema

`backend/app/models.py` defines brands, customers, orders, conversations, messages, knowledge entries, and reply generations. `backend/app/auth_models.py` defines admin accounts, customer accounts, and login sessions. Alembic migrations are in `backend/migrations/versions`. React UI code is in `frontend/src`; study notes and schema diagrams are in `docs`.

## Deployment and limitations

This repository is configured for local development. Before public deployment, configure HTTPS, secure cookies, permitted origins, and strong admin credentials. The admin seed preserves an existing account's password; changing the environment variable alone does not reset it. Customer access is limited to one brand/profile; the demo admin can access both brands. Conversations require refresh to see messages sent from another browser. Sending stores an agent message inside the app; it does not deliver email or WhatsApp messages.

Policy retrieval uses keywords and can fall back to agent review. Seeded policies and orders are fictional, including those labelled Nike and Adidas.

## AI assistance disclosure

Built with AI assistance for code, explanations, debugging, and verification. Review the implementation and describe your own understanding and contributions in the assessment submission.
