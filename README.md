# Gambia Judiciary E-Filing & Case Management System

National e-filing platform for The Gambia's five court tiers.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  React 18 + TypeScript + Tailwind CSS  (Vite, React Query)     │
│  Dark-theme UI  ·  Role-based navigation  ·  JWT auth          │
└─────────────────────────┬───────────────────────────────────────┘
                          │ REST API (JWT Bearer)
┌─────────────────────────▼───────────────────────────────────────┐
│  Django 5 + DRF  ·  Celery + Redis  ·  PostgreSQL 16           │
│  MUSU payment webhook  ·  SHA-256 doc integrity  ·  RBAC       │
└─────────────────────────────────────────────────────────────────┘
```

## Phase 1 Scope (current)

| Feature | Status |
|---------|--------|
| Law firm & lawyer registration | ✓ |
| Case creation wizard (court + type + forms) | ✓ |
| Court fee calculator | ✓ |
| MUSU payment integration (mock + production) | ✓ |
| Document upload with SHA-256 tamper detection | ✓ |
| Accounts Department queue & review | ✓ |
| Registrar queue, register/reject, case numbering | ✓ |
| Case status state machine | ✓ |
| Case timeline view | ✓ |
| Lawyer resubmission after rejection | ✓ |
| SMS + Email notifications (Celery async) | ✓ |
| Immutable audit log | ✓ |
| JWT auth with role-based access | ✓ |
| 11 user roles defined | ✓ |

---

## Quick Start (Docker)

```bash
# 1. Clone and enter project
cd gambia-judiciary

# 2. Create backend .env from example
cp backend/.env.example backend/.env
# Edit .env — set SECRET_KEY at minimum

# 3. Start all services
docker-compose up --build

# 4. Seed system admin (first run only)
docker-compose exec backend python manage.py shell < scripts/seed_admin.py

# 5. Load court form fee schedule
docker-compose exec backend python manage.py loaddata apps/cases/fixtures/court_forms.json
```

Access:
- **Frontend:**  http://localhost:5173
- **API docs:**  http://localhost:8000/api/docs/
- **Django admin:** http://localhost:8000/admin/
- **MinIO console:** http://localhost:9001 (judiciary / judiciary123)

Default admin login: `admin@judiciary.gm` / `Admin1234!`

---

## Manual Setup (without Docker)

```bash
# Backend
cd backend
python -m venv venv && source venv/bin/activate   # venv\Scripts\activate on Windows
pip install -r requirements.txt
cp .env.example .env                              # fill in values

createdb judiciary_db                             # PostgreSQL must be running
python manage.py migrate
python manage.py loaddata apps/cases/fixtures/court_forms.json
python manage.py shell < ../scripts/seed_admin.py
python manage.py runserver

# Celery (separate terminal)
celery -A config worker --loglevel=info

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

---

## Key URL Routes

### API (DRF)
| Method | URL | Role | Purpose |
|--------|-----|------|---------|
| POST | `/api/v1/auth/login/` | All | JWT login |
| GET | `/api/v1/cases/forms/?court=high` | All | Fee schedule |
| POST | `/api/v1/cases/` | Lawyer | Create case |
| GET | `/api/v1/cases/` | Lawyer/Staff | List cases |
| GET | `/api/v1/cases/<id>/` | Lawyer/Staff | Case detail |
| POST | `/api/v1/payments/cases/<id>/initiate/` | Lawyer | Start MUSU payment |
| POST | `/api/v1/payments/callback/` | MUSU webhook | Confirm payment |
| POST | `/api/v1/payments/mock-confirm/` | Lawyer (dev) | Mock payment confirm |
| GET | `/api/v1/cases/accounts/queue/` | Accounts | Accounts queue |
| POST | `/api/v1/cases/<id>/accounts/review/` | Accounts | Forward or flag |
| GET | `/api/v1/cases/registrar/queue/` | Registrar | Registrar queue |
| POST | `/api/v1/cases/<id>/registrar/review/` | Registrar | Register or reject |

### Frontend
| URL | Screen |
|-----|--------|
| `/login` | Login |
| `/dashboard` | Role-appropriate dashboard |
| `/cases` | Lawyer: my cases |
| `/cases/new` | Case creation wizard |
| `/cases/:id` | Case detail + timeline |
| `/cases/:id/payment` | MUSU payment screen |
| `/accounts/queue` | Accounts queue |
| `/accounts/review/:id` | Accounts review |
| `/registrar/queue` | Registrar queue |
| `/registrar/review/:id` | Registrar review |

---

## Case State Machine

```
DRAFT
  │  payment confirmed (MUSU callback)
  ▼
PENDING_ACCOUNTS
  │  Accounts forwards     │  Accounts flags
  ▼                        ▼
PENDING_REGISTRAR       REJECTED ──► RESUBMITTED ──► PENDING_ACCOUNTS
  │  Registrar registers   │  Registrar rejects
  ▼                        ▼
REGISTERED              REJECTED
  │ (Phase 2)
  ▼
ASSIGNED → HEARING_SCHEDULED → ACTIVE → JUDGMENT_PENDING
  → JUDGMENT_DELIVERED → APPEAL_FILED / CLOSED → ARCHIVED
```

---

## User Roles

| Role | Key Permissions |
|------|----------------|
| `system_admin` | Full access — user management, firm approval, all queues |
| `accounts_dept` | Accounts queue, fee verification, forward/flag |
| `registrar` | Registrar queue, register/reject, case numbering |
| `chief_justice` | Case assignment to judges (Phase 2) |
| `judge` | Assigned cases, hearings, judgments (Phase 2) |
| `judge_clerk` | Hearing notices, scheduling (Phase 2) |
| `lawyer` | Create cases, pay, upload documents, track timeline |
| `public_user` | Self-file (limited), case tracking |

---

## Security Design

- **Auth:** JWT (8-hour access tokens, 7-day refresh, blacklisted on logout)
- **Role enforcement:** Every view declares `permission_classes` explicitly — no default fallthrough
- **Document integrity:** SHA-256 computed server-side on upload, verified on demand
- **Payment webhooks:** HMAC-SHA256 signature verified before processing
- **Audit trail:** Insert-only `AuditLog` table — no UPDATE/DELETE allowed at model level
- **State machine:** All case transitions enforced in `Case.transition_to()` — no direct status writes
- **CORS:** Explicit allowlist in settings
- **File uploads:** MIME type + size validated; stored in S3-compatible storage (not served directly)

---

## Phase Roadmap

| Phase | Timeline | Scope |
|-------|----------|-------|
| **1 — Foundation** (current) | 8–12 weeks | Filing portal: Lawyer → MUSU → Accounts → Registrar |
| **2 — Court Operations** | 12–20 weeks | Chief Justice assignment, hearings, judgments |
| **3 — Intelligence & Security** | 20–32 weeks | Appeals, AI screening, sealed cases, SLA dashboard |
| **4 — National Scale** | 32–48 weeks | USSD, public portal, analytics, open API |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Django 5 + Django REST Framework |
| Database | PostgreSQL 16 |
| Task queue | Celery + Redis |
| Frontend | React 18 + TypeScript + Vite + Tailwind CSS |
| State | Zustand + React Query |
| Payments | MUSU API (HMAC webhook) |
| Notifications | SendGrid (email) + Twilio/Gamcel (SMS) |
| File storage | S3-compatible (MinIO local, AWS S3 prod) |
| Auth | JWT (simplejwt) + role-based permissions |
| Proxy | Nginx + Gunicorn |
| Infrastructure | Self-hosted VPS (Gambia data sovereignty) |
