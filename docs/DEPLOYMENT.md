# Assessment deployment on Render

Deploy React and FastAPI as one native Python web service, without Docker. PostgreSQL is a separate managed database. The browser calls `/api` on the same HTTPS origin; session cookies remain HttpOnly and Secure.

1. Sign in to Render with GitHub.
2. Create a PostgreSQL database named `cx-reply-assistant-db`. Choose a region and plan. The free database expires after 30 days.
3. Create a Web Service from `eddytiya/cx-reply-assistant`, branch `main`. Choose **Python 3** as the language/runtime. Leave Root Directory blank so both frontend and backend files are available. Choose the same region as the database. Set these commands:

   Build command: `pip install -r backend/requirements.txt && python scripts/build_render.py`

   Start command: `cd backend && python -m app.start_deployed`

   These commands run on Render's Linux server. Your local terminal can remain Windows CMD.
4. Add these service environment variables using the database connection details. Use the database's internal hostname when both services are on Render in the same region.

| Variable | Value |
| --- | --- |
| PYTHON_VERSION | 3.12.12 |
| NODE_VERSION | 24.11.0 |
| DB_HOST | Hosted database hostname |
| DB_PORT | 5432 |
| DB_NAME | Hosted database name |
| DB_USER | Hosted database username |
| DB_PASSWORD | Hosted database password |
| GEMINI_API_KEY | Your existing key, entered privately in Render |
| GEMINI_MODEL | gemini-3.5-flash-lite |
| ADMIN_USERNAME | admin |
| ADMIN_PASSWORD | A strong demo password, different from admin |
| AUTH_COOKIE_SECURE | true |
| AUTH_SESSION_HOURS | 8 |
| AUTH_ALLOWED_ORIGINS | Exact public HTTPS web-service URL, without a trailing slash |

5. Set health check path to `/api/health`. Deploy. If the URL is assigned during creation, update `AUTH_ALLOWED_ORIGINS` to that exact URL and redeploy before testing writes.
6. Startup runs Alembic and repeatable demo seeds before serving the app. It preserves existing accounts and conversations. Use a fresh hosted database; it does not copy your local database or reset existing admin passwords.
7. Verify `/api/health/db`, login, customer registration, customer message creation, admin access to both brands, policy CRUD, Gemini generation, draft editing, approval, and conversation refresh. Test logged-out access and customer ownership restrictions too.

Do not mark deployment complete until the public URL passes these checks. The API docs are at `/api/docs`. The database and Gemini credentials stay on the backend. Never add real secrets to GitHub.

The free web service may sleep when idle, causing a slow first request. Share the URL and demo admin credentials privately with the assessor; do not publish the password in the repository.

This startup sequence targets one demo service instance. Scaling to multiple instances requires running migrations separately rather than concurrently at every instance startup.
