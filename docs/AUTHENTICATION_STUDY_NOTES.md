# Authentication — Admin and Customer Login

## Phase 1 — Password hashing and configuration

(Installed: pwdlib with Argon2; Updated: backend/requirements.txt, backend/app/config.py, backend/.env, backend/.env.example)

We installed a Python password-hashing library and configured the local administrator credentials, session lifetime, cookie settings, and approved frontend origins. Local demo credentials are admin/admin. Password hashing is one-way: the database stores a salted Argon2id hash rather than the original password. Login verifies the entered password against that hash.

Tested configuration loading and verified that hashing accepts a correct password and rejects an incorrect password. Public deployment requires a stronger administrator password, HTTPS cookies, and the deployed frontend origin.

## Phase 2 — Authentication database tables

(Created: backend/app/auth_models.py, backend/migrations/versions/49e4ab87c1cf_add_admin_customer_accounts_and_login_.py; Updated: backend/migrations/env.py)

We added three tables and used Alembic to create them in PostgreSQL. The migration preserves the existing application tables and data.

| Table | What it does |
| --- | --- |
| admin_accounts | Stores administrator username, display name, password hash, active status, failed login attempts, and temporary lock expiry. The administrator can manage both demo brands. |
| customer_accounts | Stores a customer username and password hash and links the account to its existing customer-profile structure through customer_id. |
| login_sessions | Stores a session-token hash, expiry, and a reference to either an administrator or customer account. A database constraint requires exactly one account reference per session. |
| customers (existing) | Stores customer name, email, and brand. This remains separate from login credentials. |

Each registered customer currently belongs to the brand selected during registration. Registration creates a new profile and a new empty conversation. It does not connect the account to an existing customer's chats by matching an email address. No fictional purchase or order is created for a new registrant.

Tested migration application, account/profile relationships, session ownership, and preservation of existing records.

## Phase 3 — Authentication and authorization helpers

(Created: backend/app/auth.py)

We added password hashing/verification, random session-token hashing, current-account lookup, administrator permissions, conversation ownership checks, and checks rejecting browser writes from unapproved origins.

The browser stores a random token in an HttpOnly cookie. PostgreSQL stores only its SHA-256 digest. SHA-256 is used for the high-entropy session token; human passwords use Argon2id. React does not store password hashes or session tokens in localStorage.

Authentication identifies the signed-in account. Authorization determines what that account may access. Administrators can manage both brands. Customers can view only their own brand and conversations, send customer messages, and cannot access policy-management or AI-generation endpoints.

Tested wrong-brand access, access to another customer's conversation within the same brand, agent impersonation, and attempted policy/AI operations by a customer. The backend rejects each attempt.

## Phase 4 — Registration, login, session restoration, and logout APIs

(Created: backend/app/routes/auth.py)

| Endpoint | Purpose |
| --- | --- |
| GET /auth/brands | Public list of brand names and IDs for the registration form. It does not expose customer data. |
| POST /auth/register | Creates a customer account, new customer profile, and empty conversation in one transaction. Public registration cannot create administrators. |
| POST /auth/login | Verifies credentials for the selected account type and sets an HttpOnly session cookie. |
| GET /auth/me | Identifies the currently signed-in account. React uses it when the page opens or refreshes. |
| POST /auth/logout | Removes the current session from the database and clears its cookie. |

Customer passwords must contain 8–128 characters. Usernames are normalized to lowercase and accept letters, numbers, dots, underscores, and hyphens. Duplicate customer usernames are rejected. Five wrong passwords temporarily lock that account for five minutes. The configured local session lifetime is eight hours.

Tested valid registration, duplicate usernames, invalid inputs, attempted administrator registration, correct/incorrect passwords, account lockout, expiry, and logout. Simulated a database commit failure and confirmed registration rolled back without leaving an account/profile/conversation behind.

## Phase 5 — Protect the support APIs and seed the administrator

(Created: backend/app/seed_admin.py; Updated: backend/app/main.py, backend/app/routes/conversations.py)

We protected the conversation APIs with login and ownership checks. Customer brand/conversation lists are filtered by the logged-in account. Policy and AI reply routers require administrator access. Customers cannot submit a message with sender_role set to agent.

We seeded the local administrator using the configured credentials. Rerunning the seed preserves an existing account's password. The administrator may use the Customer/Agent switch as a demo simulation; actual customer accounts have only the customer view.

Tested anonymous access rejection, administrator access to both brands, customer message creation, and an administrator reply appearing in that customer's shared conversation. No Gemini call was needed for these authentication checks.

## Phase 6 — React login and registration pages

(Created: frontend/src/components/RegisterPage.jsx, frontend/src/components/AuthRoot.jsx; Updated: frontend/src/components/LoginPage.jsx, frontend/src/App.jsx, frontend/src/main.jsx, frontend/src/api.js, frontend/src/index.css)

The login page offers Customer and Administrator account types. Customer registration collects name, email, username, brand, password, and password confirmation. It rejects mismatched passwords before submission. Password fields support showing/hiding the text.

After successful registration, the user returns to customer login with their username filled in. Login opens the existing application using the server-confirmed account role. Customers receive their own conversation view; administrators receive the support workspace and policy tools. A logout button is shown while signed in.

AuthRoot checks the existing session when the page opens. A valid session restores the workspace after refresh. A logged-out user sees login and can select registration if they need an account. A protected API's 401 response returns the interface to login. Backend permissions remain authoritative even if someone modifies the frontend.

Tested frontend lint and production build, with no lint warnings/errors. Verified that the running Vite proxy forwards login cookies and authenticated requests successfully. Final interactive browser checking is available using the steps below; no claim is made that every browser interaction was automated.

## Phase 7 — Verification and manual testing

(Created: backend/app/check_auth.py)

The integration checker uses the real database and FastAPI endpoints inside a transaction. It creates temporary accounts and messages and rolls them back afterward. It verifies permissions, hashes, sessions, validation, lockout, failure rollback, and logout replay prevention. Existing demo customers, orders, policies, messages, and AI logs remain intact.

Commands executed:

```cmd
cd /d "D:\assessment new\cx-reply-assistant\backend"
.venv\Scripts\python.exe -m alembic revision --autogenerate -m "add admin customer accounts and login sessions"
.venv\Scripts\python.exe -m alembic upgrade head
.venv\Scripts\python.exe -m app.seed_admin
.venv\Scripts\python.exe -m app.check_auth
```

The revision command was already executed and should not be repeated unless another schema change is made.

```cmd
cd /d "D:\assessment new\cx-reply-assistant\frontend"
npm run lint
npm run build
```

All authentication integration assertions, frontend lint/build checks, and live backend/Vite login-cookie checks passed. The backend test client currently emits a third-party Starlette deprecation warning about its httpx adapter; it does not fail the tests.

### Manual browser test

1. Open http://localhost:5173 and select Administrator.
2. Log in using the local demo account admin/admin. Confirm Nike and Adidas are available.
3. Log out and confirm the login page returns.
4. Select Customer, choose Create an account, and register with a new username, a password of at least eight characters, and a selected brand.
5. Log in as that customer. Confirm their empty conversation is visible and admin/policy/AI controls are absent.
6. Send a customer message and refresh. Confirm the session and message persist.
7. Use another browser or an incognito window to log in as administrator, find the new customer conversation, and send a reply.
8. In the customer browser, refresh the conversation to see the reply. Automatic realtime updates are not implemented.
9. Log out. Protected APIs must reject further access with 401.

Using separate browser contexts prevents the administrator's login from replacing the customer's cookie in the same browser.

Build note: Implemented separate admin/customer accounts, hashed passwords, revocable login sessions, registration/login pages, and backend role/ownership permissions. Authentication tests and frontend lint/build passed. The application is still a local demo; public deployment remains.
