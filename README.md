<div align="center">

<br>

# 🎟️ TICKET‑TALLY

<h3>Enterprise‑grade IT ticketing — engineered, not templated.</h3>

**SLA‑driven workflows. Live Socket.IO updates. Role‑based control from employee to admin.**
<br>Submit → Auto‑Route → Claim → Resolve → Measure — the full lifecycle, in one system.

<br>

### 🌐 [**ticket-tally.onrender.com**](https://ticket-tally.onrender.com)

*No signup needed to look around — use the built‑in read‑only demo login and see it live.*

<br>

<p>
  <a href="https://ticket-tally.onrender.com"><img src="https://img.shields.io/badge/🚀_LIVE_DEMO-Visit_Now-ff6b6b?style=for-the-badge&labelColor=1a1a1a" alt="Live Demo" /></a>
</p>

<p>
  <img src="https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.12" />
  <img src="https://img.shields.io/badge/Flask-3.1-000000?style=for-the-badge&logo=flask&logoColor=white" alt="Flask 3.1" />
  <img src="https://img.shields.io/badge/PostgreSQL-15-4169E1?style=for-the-badge&logo=postgresql&logoColor=white" alt="PostgreSQL 15" />
  <img src="https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker Compose" />
  <img src="https://img.shields.io/badge/Socket.IO-Real--Time-010101?style=for-the-badge&logo=socket.io&logoColor=white" alt="Socket.IO Real-Time" />
</p>

<p><sub>Monolithic Flask core · Versioned REST API · Server‑rendered dashboards · Live event stream over WebSockets</sub></p>

<br>

<table>
<tr>
<td align="center" width="25%">🎫<br><b>Auto‑Routed Tickets</b><br><sub>category → team mapping</sub></td>
<td align="center" width="25%">⏱️<br><b>Live SLA Engine</b><br><sub>4 priority tiers, real deadlines</sub></td>
<td align="center" width="25%">🔔<br><b>Real‑Time Everything</b><br><sub>Socket.IO push, zero polling</sub></td>
<td align="center" width="25%">🛡️<br><b>Role‑Locked Security</b><br><sub>JWT + anti‑enumeration</sub></td>
</tr>
</table>

</div>

<br>

> [!NOTE]
> **How to read this document.** Every diagram, table, and claim below is derived directly from the code in this repository — route decorators, service methods, models, and config files, not aspiration. Where something is a known gap rather than a feature, it's labeled as such in [Known Limitations](#-known-limitations--future-improvements). Nothing here is decoration for its own sake.

<br>

## 🧭 Table of Contents

<table>
<tr>
<td valign="top" width="33%">

**The Product**
1. [Overview](#-overview)
2. [Key Features](#-key-features)
3. [Ticket Lifecycle](#-ticket-lifecycle)
4. [Role & Permission Model](#-role-and-permission-model)
5. [Feature Workflows](#-feature-workflows)

</td>
<td valign="top" width="33%">

**The Engineering**
6. [System Architecture](#-system-architecture)
7. [Request Flow](#-application-request-flow)
8. [Technology Stack](#-technology-stack)
9. [Project Structure](#-project-structure)
10. [Database Design](#-database-design)
11. [API Overview](#-api-overview)
12. [Real‑Time Architecture](#-real-time-architecture)
13. [Security](#-security)
14. [Claim Concurrency](#-ticket-claim-concurrency-protection)
15. [SLA Management](#-sla-management)

</td>
<td valign="top" width="33%">

**Running It**
16. [Environment Variables](#-environment-variables)
17. [Local Setup](#-installation-and-local-setup)
18. [Docker Setup](#-docker-setup)
19. [SQLite → Postgres Migration](#-database-migration-sqlite--postgresql)
20. [Deployment](#-deployment)
21. [Testing](#-testing)
22. [Development Workflow](#-development-workflow)
23. [Known Limitations](#-known-limitations--future-improvements)
24. [Contributing](#-contributing)
25. [License](#-license)

</td>
</tr>
</table>

---

## 🎫 Overview

**Ticket‑Tally** is an internal IT service management (ITSM) tool — built the way a real support desk actually needs to run, not the way a tutorial says it should. Employees submit tickets describing an issue (category, description, priority); the system automatically routes the ticket to the right team based on a configurable category → team mapping; IT staff claim and work tickets against SLA response/resolution targets; and admins get analytics, team configuration, and moderation controls.

> 👉 **See it for yourself:** [ticket-tally.onrender.com](https://ticket-tally.onrender.com) — spin up the demo login and walk through a ticket end to end in under a minute.

It combines three things that are usually separate tools:

| | |
|---|---|
| 🎫 **Ticket management** | Creation, categorization, auto‑routing, claiming, commenting, status history, PDF export. |
| 📁 **A lightweight project tracker** | Projects with a team roster, status, priority, and progress percentage — separate from the ticket system. |
| 📊 **An admin / analytics console** | Dashboards, CSAT tracking, SLA compliance, team‑to‑category mappings, announcements, and a shared calendar. |

The application is server‑rendered (Jinja2 templates + vanilla JS/Bootstrap, served from `app/templates` and `app/static`) on top of a versioned JSON REST API (`/api/v1/...`), with Socket.IO pushing live ticket/notification/calendar events to connected browsers.

---

## ⚙️ Key Features

<details open>
<summary><b>🎫 Ticket Management</b></summary>
<br>

- Ticket creation with title, description, category, and priority, with automatic team assignment via a `TeamMapping` category → team lookup (falls back to an "IT Support" team if no mapping exists).
- Duplicate‑ticket detection: before creating a ticket, the frontend can call `POST /api/v1/tickets/check-duplicate`, which does a fuzzy (`ILIKE`) title match against the current user's own open tickets.
- Threaded comments (self‑referential `parent_id` for replies), blocked once a ticket is `Closed`.
- Full status‑change history (`TicketStatusHistory`) recorded on every transition, including system‑driven changes (`changed_by_id = NULL`).
- PDF export of an individual ticket (`GET /api/v1/tickets/<id>/pdf`), restricted to the creator, assignee, the assigned team's members, or an admin.
- CSAT (customer satisfaction) 1–5 star feedback, restricted to the ticket creator and only once the ticket is `Resolved` or `Closed`.
- Reopen requests: an employee can request a resolved ticket be reopened within 7 days of last activity (minimum 15‑character reason); admins approve or decline.

</details>

<details>
<summary><b>🔐 Role‑Based Access</b></summary>
<br>

Three roles — `employee`, `it_staff`, `admin` — enforced by JWT‑based `token_required`/`role_required` decorators on every protected route.

</details>

<details>
<summary><b>⏱️ SLA & Workflow Management</b></summary>
<br>

- Per‑priority SLA response/resolution targets (auto‑seeded on first use: Critical 4h, High 8h, Medium 24h, Low 48h resolution).
- Live SLA status per ticket: `Pending`, `Approaching` (>80% of the window elapsed), `Achieved`, or `Breached`.
- Automatic daily job that closes tickets left in `Resolved` status for more than 7 days.
- Automatic daily data‑retention job that archives (to JSON) and permanently purges old `Closed`/`Withdrawn`/soft‑deleted tickets past a configurable retention window.

</details>

<details>
<summary><b>📁 Project Management</b></summary>
<br>

- Admin‑only project CRUD with status (`Planning`, `Active`, `On Hold`, `Completed`), priority, start/deadline dates, progress percentage, and a many‑to‑many team roster.
- Completed projects are locked from edits except reopening via a status change.
- Email notifications to newly assigned team members.

</details>

<details>
<summary><b>🔔 Notifications & Real‑Time</b></summary>
<br>

- Persistent in‑app notifications (`Notification` model) generated for ticket creation, status changes, new comments, password resets, and reopen requests.
- Notifications are pushed live over Socket.IO in addition to being stored for later retrieval.
- Socket.IO events for new notifications, a global "live activity" feed (ticket created/claimed/status‑changed/commented/etc.), and calendar event updates.

</details>

<details>
<summary><b>📊 Analytics & Reporting</b></summary>
<br>

- **Admin dashboard:** ticket counts by status/category/priority, 7‑day created/resolved trend, SLA compliance breakdown, CSAT average/breakdown/recent feedback, pending reopen‑request count.
- **IT staff dashboard:** personal/team‑scoped assigned/in‑progress/resolved‑today counts, SLA breach count, and a 7‑day assigned‑vs‑resolved trend.
- Admin performance export and a full dashboard report export (`app/api/v1/admin_routes.py`).
- Per‑user data export as JSON, CSV, or PDF (`GET /api/v1/users/export`).

</details>

<details>
<summary><b>🛡️ Security</b></summary>
<br>

- Passwords hashed with Werkzeug's `generate_password_hash`/`check_password_hash` (PBKDF2).
- Stateless JWT (HS256) bearer‑token authentication with configurable expiry.
- Password reset via a signed, time‑limited token (`app/utils/token.py`), with the response deliberately identical whether or not the email exists (anti‑enumeration).
- A read‑only "demo" account is blocked from any `POST`/`PUT`/`PATCH`/`DELETE` request at the middleware level.
- Per‑route rate limiting (Flask‑Limiter) on auth and ticket‑creation endpoints.
- Soft‑delete support (`SoftDeleteMixin`) on `Ticket` and `Project`, with a SQLAlchemy `do_orm_execute` hook that transparently filters out soft‑deleted rows unless explicitly requested.

</details>

<details>
<summary><b>🚀 Deployment</b></summary>
<br>

Multi‑stage Docker build, Docker Compose stack (app + Postgres + Redis + Nginx reverse proxy), and a ready‑to‑use `render.yaml` for Render.com.

</details>

---

## 🧠 System Architecture

*How the browser, the Flask app, and its external dependencies (database, SMTP, GitHub) fit together.*

```mermaid
flowchart TB
    User[User Browser]

    User -->|HTML pages| Web[Web Routes - Jinja2 Templates]
    User -->|fetch calls| API[REST API /api/v1]
    User <-->|WebSocket| Socket[Socket.IO]

    Web --> AppFactory[Flask App Factory]
    API --> Middleware[JWT Auth / Role Middleware]
    Middleware --> Services[Service Layer]
    AppFactory --> Services

    Services --> Models[SQLAlchemy Models]
    Models --> DB[(PostgreSQL / SQLite)]

    Services --> Email[SMTP Email Service]
    Services --> PDF[ReportLab PDF Service]
    Services --> Scheduler[APScheduler Background Jobs]

    Socket --> Services
    Services -.emit events.-> Socket

    External[GitHub] -->|PR merge webhook| API

    Nginx[Nginx Reverse Proxy] --> AppFactory
    Nginx --> StaticFiles[Static Assets]
```

> [!IMPORTANT]
> Ticket‑Tally is a **monolithic Flask application**, not a microservice architecture. Web pages and the JSON API are served by the same Flask app and share the same service layer; Nginx (in the Docker Compose stack) sits in front only as a static‑file cache and reverse proxy, not as an API gateway.

---

## 🔄 Application Request Flow

*The path a single HTTP request takes through auth middleware, the service layer, and back — plus where a real‑time event gets fired off along the way.*

```mermaid
sequenceDiagram
    participant U as Browser
    participant R as Flask Route (API/Web)
    participant M as token_required / role_required
    participant S as Service Layer
    participant DB as SQLAlchemy / Database
    participant WS as Socket.IO

    U->>R: HTTP request (Bearer JWT for API routes)
    R->>M: Decode & validate JWT, load g.user
    M-->>R: 401 if missing/invalid, 403 if role denied
    R->>S: Call service method (e.g. TicketService.create_ticket)
    S->>DB: Read / write via SQLAlchemy
    DB-->>S: Result
    S-->>WS: emit('new_notification' / 'live_activity' / 'calendar_update')
    S-->>R: Return domain object / raise ValueError
    R-->>U: JSON response
    WS-->>U: Pushed real-time update
```

Routes are thin: they parse/validate the request (Pydantic schemas where present), delegate business logic entirely to a static‑method service class (`TicketService`, `AuthService`, `NotificationService`, `SLAService`, `PDFService`, ...), and translate service results/exceptions into HTTP responses.

---

## 🎯 Ticket Lifecycle

*Every status a ticket can be in, and the specific actions/jobs that move it between them.*

```mermaid
stateDiagram-v2
    [*] --> Open : Ticket created
    Open --> InProgress : IT staff claims ticket
    Open --> Withdrawn : Creator withdraws (Open only)
    InProgress --> Resolved : Status updated by IT staff/admin
    InProgress --> Resolved : GitHub PR merged (webhook, if linked)
    Resolved --> Closed : Auto-closed after 7 days
    Resolved --> Open : Reopen request approved by admin (within 7 days)
    Closed --> [*]
    Withdrawn --> [*]
```

Notes verified from `TicketService` and `ticket_routes.py`:

- A **manual** transition directly to `Closed` is rejected by `TicketService.update_ticket` (`ValueError: "Manual status transition to Closed is not allowed"`) — closing only happens via the automated 7‑day job.
- Moving a ticket to `In Progress` without an assignee auto‑assigns it to the updating user, if that user is `it_staff` or `admin`.
- `Withdrawn` is only reachable from `Open`, and only by the ticket's creator.
- Once `Closed`, a ticket cannot be updated and no new comments can be added.
- A GitHub webhook (`POST /api/v1/github/webhook`) automatically transitions a ticket to `Resolved` when a linked pull request (matched by `github_pr_url`) is merged, unless the ticket is already `Resolved` or `Closed`.

---

## 👥 Role and Permission Model

<div align="center">

| Capability | 👤 Employee | 🧑‍💻 IT Staff | 👑 Admin |
|---|:---:|:---:|:---:|
| Create tickets | ✅ | ✅ | ✅ |
| View own/created tickets | ✅ | ✅ | ✅ |
| View team / assigned tickets | ❌ | ✅ | ✅ (all) |
| Claim tickets | ❌ | ✅ | ✅* |
| Update ticket status/priority/assignee | ✅ (own updates via API) | ✅ | ✅ |
| Withdraw own Open ticket | ✅ | — | — |
| Request ticket reopen | ✅ (as creator) | ❌ | ❌ |
| Approve/decline reopen requests | ❌ | ❌ | ✅ |
| Submit CSAT feedback | ✅ (as ticket creator) | ❌ | ❌ |
| Download ticket PDF | Creator only | Assignee/team only | ✅ (any) |
| View IT‑staff dashboard | ❌ | ✅ | ✅ |
| View admin analytics dashboard | ❌ | ❌ | ✅ |
| Manage team‑to‑category mappings | ❌ | ❌ | ✅ |
| Manage announcements | ❌ | ❌ | ✅ |
| Manage calendar events (create/edit/delete) | ❌ | ❌ | ✅ |
| View calendar events | ✅ | ✅ | ✅ |
| Create/update/delete projects | ❌ | ❌ | ✅ |
| View projects | ✅ | ✅ | ✅ |
| Manage users (list/create/edit) | ❌ | ❌ | ✅ |
| Trigger data retention purge | ❌ | ❌ | ✅ |
| Export personal data (JSON/CSV/PDF) | ✅ | ✅ | ✅ |
| Export performance/dashboard reports | ❌ | ❌ | ✅ |

</div>

<sub>\* The claim route itself only requires `token_required` (any authenticated role), but `TicketService.claim_ticket` applies workload/eligibility checks to whichever user calls it — in practice the UI only exposes claiming to IT staff and admins.</sub>

> Every row above is derived directly from `@role_required([...])` decorators in `app/api/v1/*.py` and inline `g.user.role` / ownership checks inside route handlers and `TicketService`/`AuthService`.

---

## 🔀 Feature Workflows

*Five workflows worth visualizing because of their branching logic.*

<br>

### 🎫 Ticket Creation Flow

*What happens between an employee submitting a ticket and the confirmation email landing in their inbox.*

```mermaid
flowchart LR
    A[Employee submits ticket] --> B[Pydantic validation - TicketCreate]
    B --> C{Category mapped to a team?}
    C -->|Yes| D[Assign mapped team]
    C -->|No mapping| E[Default to 'IT Support' team]
    D --> F[Create Ticket + initial status history]
    E --> F
    F --> G[Notify creator, admins, and team's IT staff]
    G --> H[Broadcast live_activity over Socket.IO]
    H --> I[Send confirmation email to creator]
```

<br>

### 🔒 Ticket Claim / Concurrency Flow

*How the system decides who wins when two agents try to claim the same ticket at once.*

```mermaid
sequenceDiagram
    participant Agent as IT Staff
    participant API as claim_ticket route
    participant Svc as TicketService.claim_ticket
    participant DB as Database

    Agent->>API: POST /api/v1/tickets/<id>/claim
    API->>Svc: claim_ticket(ticket_id, user_id)
    Svc->>DB: Load ticket by id
    alt Ticket withdrawn
        Svc-->>API: ValueError("Ticket has been withdrawn")
    else Already In Progress / Resolved / Closed / assigned
        Svc-->>API: ValueError("already in progress or claimed")
        API-->>Agent: 409 Conflict
    else Agent already has 3+ active (In Progress) tickets
        Svc-->>API: ValueError("Workload limit reached")
        API-->>Agent: 400 Bad Request
    else Eligible
        Svc->>DB: Set status=In Progress, assigned_to_id=agent, commit
        Svc->>DB: Insert TicketStatusHistory row
        Svc-->>API: Ticket claimed
        API-->>Agent: 200 OK
    end
```

<br>

### 🔔 Notification Flow

*A ticket event fires once, and reaches the user two ways at once — live if they're online, persisted if they're not.*

```mermaid
flowchart LR
    A[Domain event occurs\ne.g. status change, comment] --> B[NotificationService]
    B --> C[Persist Notification row in DB]
    B --> D[emit new_notification over Socket.IO]
    C --> E[User opens notification bell later]
    D --> F[Connected client updates live]
```

<br>

### 🔑 Password Reset Flow

*The forgot‑password → reset‑password round trip, including the anti‑enumeration behavior on the request side.*

```mermaid
sequenceDiagram
    participant U as User
    participant API as auth_routes
    participant Svc as AuthService
    participant Email as EmailService

    U->>API: POST /api/v1/auth/forgot-password {email}
    API->>Svc: initiate_password_reset(email)
    Svc->>Svc: Look up user (silently no-op if not found)
    Svc->>Email: Send reset link with signed token
    Svc-->>API: Always returns success (anti-enumeration)
    API-->>U: "If an account exists..." message

    U->>API: POST /api/v1/auth/reset-password {token, new_password}
    API->>Svc: complete_password_reset(token, new_password)
    Svc->>Svc: Verify token, resolve email
    Svc->>Svc: Hash and store new password
    Svc-->>API: Success or ValueError (invalid/expired token)
```

<br>

### 📁 Project Management Flow

*Project creation/assignment, and the guardrail that locks a Completed project from further edits.*

```mermaid
flowchart LR
    A[Admin creates project] --> B[Set status/priority/dates/progress]
    B --> C[Resolve team members by email or name]
    C --> D[Persist Project + project_team rows]
    D --> E[Email admin: project created]
    D --> F[Email each new team member: assignment]
    G[Admin updates project] --> H{Status == Completed?}
    H -->|Yes, non-status field changed| I[Reject: 400 - locked]
    H -->|No| J[Apply changes, email newly added members]
```

---

## 🧰 Technology Stack

| Category | Technology | Purpose |
|---|---|---|
| Backend framework | Flask 3.1 | Application server, routing, request handling |
| ORM | SQLAlchemy 2.0 (Flask‑SQLAlchemy) | Data models, relationships, query layer |
| Migrations | Flask‑Migrate / Alembic | Versioned schema migrations |
| Database (dev) | SQLite | Zero‑setup local development database |
| Database (prod) | PostgreSQL 15 (via `psycopg2-binary`) | Production relational database |
| Authentication | PyJWT | Stateless bearer‑token authentication |
| Password hashing | Werkzeug security | PBKDF2 password hashing/verification |
| Validation | Pydantic v2 | Request body validation/parsing (`schemas/`) |
| Real‑time | Flask‑SocketIO (threading mode) | Live notifications, activity feed, calendar updates |
| Rate limiting | Flask‑Limiter | Per‑route request throttling |
| Scheduled jobs | Flask‑APScheduler | Daily auto‑close and data‑retention jobs |
| API docs | Flasgger (Swagger/OpenAPI 2.0) | Interactive API documentation at `/api/docs` |
| PDF generation | ReportLab | Ticket detail PDFs, resolution‑email attachments, user data export PDFs |
| Email | `smtplib` (stdlib) | Transactional emails (ticket, project, password reset, contact form) |
| Frontend | Jinja2 templates + Bootstrap 5 + vanilla JS | Server‑rendered dashboards and forms |
| Charts | Chart.js (loaded in dashboard templates) | Analytics visualizations |
| CORS | Flask‑CORS | Cross‑origin access control |
| WSGI server | Gunicorn (`gthread` worker) | Production process manager |
| Reverse proxy | Nginx | Static asset serving + WebSocket‑aware proxy (Docker Compose) |
| Caching / queue backend | Redis | Optional Socket.IO message queue and rate‑limit storage backend |
| Testing | Pytest | Unit/integration tests against an in‑memory SQLite app instance |
| CI | GitHub Actions | Runs the Pytest suite on push/PR to `main` |
| Deployment | Docker, Docker Compose, Render | Containerized and Render.com‑native deployment paths |

---

## 🗂️ Project Structure

<details open>
<summary><b>Expand full tree</b></summary>

```text
Trial_Ticket_Tally/
├── app/
│   ├── api/v1/                  # REST API blueprints (versioned)
│   │   ├── auth_routes.py       # Signup, login, password reset, demo login
│   │   ├── ticket_routes.py     # Ticket CRUD, claim, withdraw, comments, PDF, feedback
│   │   ├── user_routes.py       # Profile, admin user management, agent directory, export
│   │   ├── admin_routes.py      # Analytics, messages, team mappings, announcements, reports
│   │   ├── it_staff_routes.py   # Assigned/team ticket views for IT staff
│   │   ├── analytics_routes.py  # Admin + IT-staff analytics dashboards
│   │   ├── project_routes.py    # Project CRUD with team assignment
│   │   ├── event_routes.py      # Shared calendar events
│   │   ├── announcement_routes.py  # Active announcement feed
│   │   ├── notification_routes.py  # In-app notification retrieval/read/clear
│   │   └── webhook_routes.py    # GitHub PR-merge webhook
│   ├── core/                    # Application backbone
│   │   ├── config.py            # Env-driven configuration (Config, TestingConfig)
│   │   ├── constants.py         # UserRole, TicketStatus, TicketPriority, SLAStatus, ProjectStatus enums
│   │   ├── database.py          # SQLAlchemy/Migrate setup + soft-delete query hook
│   │   └── extensions.py        # SocketIO, APScheduler, Limiter singletons
│   ├── middleware/
│   │   └── auth_middleware.py   # token_required / role_required decorators
│   ├── models/                  # SQLAlchemy ORM models (see Database Design)
│   ├── schemas/                 # Pydantic request/response schemas
│   ├── services/                # Business logic (Ticket, Auth, Notification, SLA, PDF, Email)
│   ├── static/                  # CSS, JS, and vendored Socket.IO client
│   ├── templates/                # Jinja2 dashboard/auth/legal pages
│   ├── utils/                    # JWT, password hashing, tokens, time helpers, PDF generator
│   ├── websocket/
│   │   └── ticket_socket.py     # Socket.IO connect/disconnect handlers
│   ├── main.py                  # Flask application factory (create_app)
│   └── web_routes.py             # Server-rendered page routes
├── migrations/                  # Alembic migration environment + versions
├── nginx/
│   └── nginx.conf                # Reverse proxy config used by docker-compose
├── tests/                        # Pytest suite (see Testing)
├── static/css/                   # Legacy top-level static assets (landing page)
├── .github/workflows/            # CI (pytest on push/PR to main)
├── Dockerfile                    # Multi-stage build (builder + slim runtime)
├── docker-compose.yml            # app + PostgreSQL + Redis + Nginx stack
├── entrypoint.sh                 # Runs `flask db upgrade` before starting Gunicorn
├── render.yaml                   # Render.com service definition
├── migrate_sqlite_to_postgres.py # One-off SQLite → Postgres data migration script
├── requirements.txt
└── run.py                        # Local entrypoint (imports create_app, runs Socket.IO server)
```

</details>

> [!WARNING]
> `PROJECT_STRUCTURE.md` in the repository predates several models and routes (e.g. `Event`, `Announcement`, `ActivityLog`, `CSATFeedback`, `ReopenRequest`, `Project`, `webhook_routes.py`, `analytics_routes.py`, several schema files) and should be regenerated — the tree above reflects the current repository.

---

## 🗄️ Database Design

*Entities and relationships as actually defined in `app/models/` — every edge below maps to a real foreign key or association table.*

```mermaid
erDiagram
    USER ||--o{ TICKET : creates
    USER ||--o{ TICKET : "is assigned"
    USER ||--o{ COMMENT : writes
    USER ||--o{ NOTIFICATION : receives
    USER ||--o{ CSAT_FEEDBACK : submits
    USER ||--o{ REOPEN_REQUEST : requests
    USER ||--o{ ANNOUNCEMENT : creates
    USER ||--o{ EVENT : creates
    USER }o--o{ PROJECT : "team member"
    USER ||--o{ PROJECT : creates
    TEAM ||--o{ USER : "has members"
    TEAM ||--o{ TICKET : "owns"
    TEAM ||--o{ TEAM_MAPPING : "maps to"
    TICKET ||--o{ COMMENT : contains
    TICKET ||--o{ TICKET_STATUS_HISTORY : tracks
    TICKET ||--o{ ACTIVITY_LOG : logs
    TICKET ||--o| CSAT_FEEDBACK : "rated by"
    TICKET ||--o{ REOPEN_REQUEST : "requested for"
    COMMENT ||--o{ COMMENT : "replies to"
```

<details>
<summary><b>Key models (from <code>app/models/</code>) — expand</b></summary>

| Model | Purpose |
|---|---|
| `User` | Accounts with `role` (employee/it_staff/admin), department, team, JSON `preferences` and `specializations`. |
| `Team` | Named support team; owns tickets and members. |
| `TeamMapping` | Maps a ticket `category` string to a `Team` for auto‑routing. |
| `Ticket` | Core ticket entity (title, description, category, status, priority, creator, assignee, team, optional linked GitHub PR URL). Includes `SoftDeleteMixin`. |
| `TicketStatusHistory` | Immutable audit trail of every status transition, including system‑driven ones. |
| `Comment` | Ticket comments with self‑referential `parent_id` for threaded replies. |
| `CSATFeedback` | One‑to‑one 1–5 star rating + optional comment per ticket, tied to the creator. |
| `ReopenRequest` | Employee‑submitted request to reopen a resolved ticket; tracks approval/decline and reason. |
| `Notification` | Per‑user in‑app notification (title, message, type, read state). |
| `ActivityLog` | Persisted feed of the same events broadcast live over Socket.IO. |
| `Announcement` | Admin‑authored, optionally time‑limited system‑wide banner messages. |
| `Event` | Shared calendar events (maintenance, training, system updates, other). |
| `Project` | Lightweight project tracker with a many‑to‑many `project_team` roster. Includes `SoftDeleteMixin`. |
| `SLA` | Per‑priority response/resolution time targets (hours), auto‑seeded with defaults if empty. |
| `Message` | Contact‑form submissions from the public `/contact` page. |

</details>

Soft deletes are implemented via a `SoftDeleteMixin` (`is_deleted`, `deleted_at`) combined with a SQLAlchemy `do_orm_execute` event listener that automatically excludes soft‑deleted rows from every query unless `execution_options(include_deleted=True)` is explicitly set (used by the archive/purge job).

---

## 🔌 API Overview

All API routes are versioned under `/api/v1`. Bearer JWT auth (`Authorization: Bearer <token>`) is required unless noted. Interactive Swagger UI is available at **`/api/docs`** (spec JSON at `/api/docs/spec.json`) once the app is running.

<details>
<summary><b>Authentication</b> — <code>/api/v1/auth</code></summary>

| Method | Endpoint | Description | Access |
|---|---|---|---|
| POST | `/signup` | Register a new user, auto‑login | Public (5/min) |
| POST | `/login` | Login with email/password | Public (5/min) |
| POST | `/forgot-password` | Request a password reset email | Public (3/min) |
| POST | `/reset-password` | Complete password reset with a token | Public (3/min) |
| POST | `/demo-login` | Log in as the read‑only demo employee | Public |

</details>

<details>
<summary><b>Tickets</b> — <code>/api/v1/tickets</code></summary>

| Method | Endpoint | Description | Access |
|---|---|---|---|
| POST | `` | Create a ticket | Authenticated (10/min) |
| GET | `` | List tickets, paginated, scoped by role | Authenticated |
| GET | `/<id>` | Get full ticket detail (comments, history, SLA, feedback, reopen status) | Authenticated |
| PUT/PATCH | `/<id>` | Update status/priority/category/assignee/team/PR link | Authenticated |
| POST | `/<id>/comments` | Add a (optionally threaded) comment | Authenticated |
| GET | `/<id>/pdf` | Download a PDF ticket report | Creator, assignee, team member, or admin |
| POST | `/check-duplicate` | Fuzzy‑check for an existing open ticket by title | Authenticated |
| POST | `/<id>/withdraw` | Withdraw own Open ticket | Creator only |
| POST | `/<id>/claim` | Claim an unclaimed ticket | Authenticated (effectively IT staff/admin) |
| POST | `/<id>/feedback` | Submit CSAT rating/comment | Ticket creator, ticket must be Resolved/Closed |
| POST | `/<id>/reopen-request` | Request reopening a Resolved ticket | Employee creator, within 7 days |

</details>

<details>
<summary><b>Users</b> — <code>/api/v1/users</code></summary>

| Method | Endpoint | Description | Access |
|---|---|---|---|
| GET | `/me` | Current user profile | Authenticated |
| PATCH | `/me` | Update own profile/preferences/specializations | Authenticated |
| POST | `/me/password` | Change own password | Authenticated |
| GET | `` | List/search/filter all users | Admin |
| POST | `` | Create a user | Admin |
| PATCH | `/<id>` | Update a user | Admin |
| GET | `/export` | Export own tickets/comments as JSON, CSV, or PDF | Authenticated |
| GET | `/agents` | Directory of active IT staff/admin agents | Authenticated |
| GET | `/specialties` | Distinct agent specialization tags | Authenticated |
| GET | `/teams` | List all teams | Authenticated |

</details>

<details>
<summary><b>IT Staff</b> — <code>/api/v1/it-staff</code></summary>

| Method | Endpoint | Description | Access |
|---|---|---|---|
| GET | `/assigned-tickets` | Tickets assigned to the current agent | IT Staff, Admin |
| GET | `/team-tickets` | Tickets belonging to the agent's team | IT Staff, Admin |

</details>

<details>
<summary><b>Projects</b> — <code>/api/v1/projects</code></summary>

| Method | Endpoint | Description | Access |
|---|---|---|---|
| GET | `` | List all projects | Authenticated |
| POST | `` | Create a project | Admin |
| GET | `/<id>` | Get project detail | Authenticated |
| PATCH | `/<id>` | Update project (locked once Completed, except status) | Admin |
| DELETE | `/<id>` | Soft‑delete a project | Admin |

</details>

<details>
<summary><b>Events</b> — <code>/api/v1/events</code></summary>

| Method | Endpoint | Description | Access |
|---|---|---|---|
| GET | `` | List calendar events | Authenticated |
| POST | `` | Create a calendar event | Admin |
| PATCH | `/<id>` | Update a calendar event | Admin |
| DELETE | `/<id>` | Delete a calendar event | Admin |

</details>

<details>
<summary><b>Announcements</b> — <code>/api/v1/announcements</code></summary>

| Method | Endpoint | Description | Access |
|---|---|---|---|
| GET | `` | Active, non‑expired announcements | Authenticated |

</details>

<details>
<summary><b>Notifications</b> — <code>/api/v1/notifications</code></summary>

| Method | Endpoint | Description | Access |
|---|---|---|---|
| GET | `/` | List notifications + unread count | Authenticated |
| POST | `/<id>/read` | Mark one notification read | Authenticated |
| POST | `/read-all` | Mark all notifications read | Authenticated |
| DELETE | `/` | Clear all notifications | Authenticated |

</details>

<details>
<summary><b>Analytics</b> — <code>/api/v1/analytics</code></summary>

| Method | Endpoint | Description | Access |
|---|---|---|---|
| GET | `/dashboard` | Org‑wide analytics (status/category/priority breakdowns, trends, SLA, CSAT) | Admin |
| GET | `/it-dashboard` | Personal/team‑scoped agent analytics | Authenticated |

</details>

<details>
<summary><b>Admin</b> — <code>/api/v1/admin</code></summary>

| Method | Endpoint | Description | Access |
|---|---|---|---|
| GET | `/analytics` | Aggregate admin metrics | Admin |
| GET | `/messages` | List contact‑form submissions | Admin |
| PATCH | `/messages/<id>/read` | Mark a message read | Admin |
| GET / POST | `/team-mappings` | List / create category → team mappings | Admin |
| PUT/PATCH / DELETE | `/team-mappings/<id>` | Update / delete a mapping | Admin |
| POST | `/purge` | Manually trigger the data‑retention purge job | Admin |
| POST / GET | `/announcements` | Create / list all announcements | Admin |
| DELETE | `/announcements/<id>` | Delete an announcement | Admin |
| GET | `/activities` | Recent activity log feed | Admin |
| GET | `/export-performance` | Export IT staff performance report | Admin |
| GET | `/export-dashboard-report` | Export full dashboard report | Admin |
| GET | `/reopen-requests` | List pending reopen requests | Admin |
| POST | `/reopen-requests/<id>/approve` | Approve a reopen request | Admin |
| POST | `/reopen-requests/<id>/decline` | Decline a reopen request | Admin |

</details>

<details>
<summary><b>GitHub Integration</b> — <code>/api/v1/github</code></summary>

| Method | Endpoint | Description | Access |
|---|---|---|---|
| POST | `/webhook` | Receives GitHub `pull_request` events; resolves the linked ticket on merge | Public (webhook) |

</details>

---

## 📡 Real‑Time Architecture

Ticket‑Tally uses **Flask‑SocketIO** in `threading` async mode. Socket registration happens in `app/websocket/ticket_socket.py`, which currently only logs `connect`/`disconnect` events — all business events are **server‑initiated broadcasts** emitted from the service layer (`NotificationService`), not client‑triggered socket messages.

Verified event names emitted by `NotificationService`:

| Event | Emitted when | Payload |
|---|---|---|
| `new_notification` | Any `Notification` row is created | Serialized notification object |
| `live_activity` | Ticket created, claimed, status changed, priority changed, assigned, commented on, feedback submitted, reopen requested | `{ timestamp, category, ticket_id, message, created_by, is_demo }` |
| `calendar_update` | A calendar `Event` is created/updated/deleted | `{ action, event }` |

> [!NOTE]
> All events are currently broadcast to **every connected client** (no per‑user Socket.IO rooms); the frontend is responsible for filtering by `user_id`/`is_demo` where relevant. For horizontal scaling across multiple app instances, `SocketIO` is configured to use a Redis‑backed `message_queue` when `REDIS_URL` is set, so broadcasts fan out correctly across processes.

---

## 🛡️ Security

- **Password hashing** — Werkzeug's `generate_password_hash`/`check_password_hash` (PBKDF2‑based), never stored or logged in plaintext.
- **Authentication** — Stateless JWTs signed with `JWT_SECRET_KEY` (HS256), carrying the user ID as `sub`, validated on every protected request via `token_required`.
- **Authorization** — Role checks (`role_required`) at the route level for admin/IT‑staff‑only endpoints, plus ownership checks inside services (e.g. only a ticket's creator can withdraw it or submit feedback).
- **Password reset tokens** — Generated/verified via `app/utils/token.py` and never expose whether an email exists in the system.
- **Demo account isolation** — The seeded demo employee account is blocked from all mutating (`POST`/`PUT`/`PATCH`/`DELETE`) requests at the middleware layer, and sees only demo‑flagged data (tickets, announcements, events) so it can't view or alter real records.
- **Rate limiting** — Flask‑Limiter caps auth endpoints (login/signup/reset) and ticket creation to reduce brute‑force and spam risk; storage backend is Redis in production or in‑memory for local/dev.
- **Input validation** — Pydantic schemas validate and coerce request bodies for auth, tickets, events, announcements, CSAT feedback, and team mappings before they reach the service layer.
- **CORS** — Explicit allow‑list via `CORS_ALLOWED_ORIGINS` (comma‑separated), applied through Flask‑CORS.

---

## 🔐 Ticket Claim Concurrency Protection

*How the system decides who wins when two agents try to claim the same ticket at once.*

```mermaid
sequenceDiagram
    participant A as IT Staff A
    participant B as IT Staff B
    participant Svc as TicketService.claim_ticket
    participant DB as Database

    A->>Svc: claim_ticket(id, A)
    B->>Svc: claim_ticket(id, B)
    Svc->>DB: A: load ticket, still Open
    Svc->>DB: A: set In Progress, assigned_to=A, commit
    Svc->>DB: B: load ticket, already In Progress
    DB-->>A: 200 Claimed
    DB-->>B: 409 already in progress or claimed by another member
```

Alongside the claim check, `claim_ticket` also enforces:

- **Withdrawn tickets can't be claimed** — raises `ValueError("Ticket has been withdrawn")`.
- **Workload limit** — an agent with 3 or more tickets currently `In Progress` is blocked from claiming another (`ValueError("Workload limit reached...")`, mapped to HTTP 400).
- **On success** — the ticket's `status` becomes `In Progress`, `assigned_to_id` is set to the claiming user, a `TicketStatusHistory` row is added, and a `live_activity` event plus status‑change notification/email are sent.

> [!NOTE]
> This is sound for the application's expected load (an internal support tool), but it's worth documenting honestly: it relies on SQLAlchemy's normal commit semantics rather than an explicit row‑level lock, so it is **not** immune to a rare race under very high concurrent write pressure on the same row. See [Known Limitations](#-known-limitations--future-improvements).

---

## ⏱️ SLA Management

SLA targets live in the `SLA` table, keyed by `TicketPriority`, and are auto‑seeded (`SLAService.seed_default_slas`) the first time they're needed if the table is empty:

| Priority | Response Target | Resolution Target |
|---|---|---|
| 🔴 Critical | 1 hour | 4 hours |
| 🟠 High | 2 hours | 8 hours |
| 🟡 Medium | 4 hours | 24 hours |
| 🟢 Low | 8 hours | 48 hours |

- **Deadline calculation** — `SLAService.get_deadline(ticket)` = `ticket.created_at + resolution_time_hours` (simple wall‑clock addition — no business‑hours/holiday calendar logic).
- **Status calculation** (`SLAService.check_sla_status`):
  - If the ticket has ever been `Resolved`, the earliest `Resolved` timestamp from `TicketStatusHistory` is compared to the deadline → `Achieved` or `Breached`.
  - If not yet resolved and the deadline has passed → `Breached`.
  - If not yet resolved and more than 80% of the SLA window has elapsed → `Approaching`.
  - Otherwise → `Pending`.
- SLA status/deadline is computed **on read** (in `ticket_routes.py`, `analytics_routes.py`) rather than stored and updated by a background job — there is no separate SLA‑breach notification job; breaches are only visible when a ticket is viewed or the dashboards are queried.
- The IT‑staff dashboard additionally computes an aggregate "SLA breaches" count directly from priority/`created_at` for tickets still `Open`/`In Progress`.

---

## 🔑 Environment Variables

<details open>
<summary><b>From <code>.env.example</code> and <code>app/core/config.py</code> — expand</b></summary>

| Variable | Required | Description | Example |
|---|---|---|---|
| `FLASK_APP` | Recommended | Flask app factory entrypoint | `app.main:create_app` |
| `FLASK_ENV` | Recommended | Environment name; `production` enables JSON logging | `production` |
| `SECRET_KEY` | Yes (prod) | Flask session/signing secret | `change-me` |
| `DATABASE_URL` | Yes | SQLAlchemy database URI (Postgres in prod, or `sqlite:///ticket_tally.db`) | `postgresql://user:pass@host:5432/ticket_tally` |
| `JWT_SECRET_KEY` | Yes (prod) | Secret used to sign/verify JWTs | `change-me` |
| `JWT_ACCESS_TOKEN_EXPIRES` | No | Access token lifetime in seconds (default `3600`) | `3600` |
| `MAIL_SERVER` | No | SMTP host; emails are skipped (logged only) if unset | `smtp.gmail.com` |
| `MAIL_PORT` | No | SMTP port (default `587`) | `587` |
| `MAIL_USE_TLS` | No | Whether to use STARTTLS (`True`/`False`) | `True` |
| `MAIL_USERNAME` | No | SMTP auth username / from‑address | `your-email@example.com` |
| `MAIL_PASSWORD` | No | SMTP auth password / app password | `your-app-password` |
| `BASE_URL` | No | Public base URL, used to build reset‑password links | `http://localhost:5000` |
| `CORS_ALLOWED_ORIGINS` | No | Comma‑separated allowed origins, or `*` | `http://localhost:5000,http://127.0.0.1:5000` |
| `REDIS_URL` | No | Redis connection string; enables Socket.IO message queue + rate‑limit storage | `redis://redis:6379/0` |
| `RETENTION_DAYS` | No | Days before Closed/Withdrawn tickets are archived and purged (default `365`) | `365` |
| `ARCHIVE_FOLDER` | No | Directory where purged ticket JSON archives are written | `./archive` |

</details>

> [!NOTE]
> The demo credentials (`DEMO_EMAIL` / `DEMO_PASSWORD`) are hardcoded constants in `Config`, not environment variables — they exist only to seed the built‑in "Try Demo" experience and should not be treated as a production login.

---

## 🚀 Installation and Local Setup

> [!TIP]
> Want to skip straight to clicking around instead of setting up locally? The live instance is running right now at **[ticket-tally.onrender.com](https://ticket-tally.onrender.com)** — use the demo login and explore before you clone anything.

### Prerequisites
- Python 3.12 (the CI pipeline tests against 3.10; the Docker image uses 3.12)
- pip
- *(Optional)* PostgreSQL 15 if you don't want to use the default SQLite database
- *(Optional)* Redis if you want Socket.IO message‑queue support or persistent rate‑limit storage

<br>

```bash
# 1. Clone
git clone https://github.com/Tanish1808/Trial_Ticket_Tally.git
cd Trial_Ticket_Tally

# 2. Create a virtual environment
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables
cp .env.example .env
# Edit .env — at minimum set SECRET_KEY and JWT_SECRET_KEY.
# Leave DATABASE_URL commented out (or point it at sqlite:///ticket_tally.db) to use SQLite locally.

# 5. Run migrations
flask db upgrade

# 6. Start the application
python run.py
```

By default, `Config.SQLALCHEMY_DATABASE_URI` falls back to `sqlite:///ticket_tally.db` if `DATABASE_URL` is not set — no separate database server is required for local development. `flask db upgrade` applies all revisions under `migrations/versions/` and creates the SQLite (or Postgres) schema. `python run.py` starts the Socket.IO‑wrapped Flask dev server on `http://127.0.0.1:5000`.

**Verify installation:**
- Open `http://127.0.0.1:5000/` for the landing page.
- Open `http://127.0.0.1:5000/api/docs` for the interactive Swagger UI.
- Use `POST /api/v1/auth/demo-login` (no body required) to get an instant read‑only demo session, or `POST /api/v1/auth/signup` to create a real account.

---

## 🐳 Docker Setup

The Docker Compose stack (`docker-compose.yml`) runs the app alongside PostgreSQL, Redis, and Nginx.

```bash
cp .env.example .env   # set SECRET_KEY / JWT_SECRET_KEY / mail settings as needed
docker compose up --build
```

This starts:

| Service | Role |
|---|---|
| `db` | PostgreSQL 15, with a healthcheck, exposing data on a named volume. |
| `redis` | Redis 7, used for the Socket.IO message queue and rate limiting. |
| `app` | The Flask app, built from the repo `Dockerfile`, connected to `db`/`redis`, listening on port `5000`. |
| `nginx` | Reverse proxy on port `80`, serving `/static/` directly and proxying everything else (including `/socket.io`) to `app`. |

> [!NOTE]
> The `app` service's `DATABASE_URL` is hardcoded in `docker-compose.yml` to point at the `db` service (`postgresql://ticket_tally_user:ticket_tally_password@db:5432/ticket_tally`) — override it in `.env` if you need a different database.

<details>
<summary><b>Build/run the app image alone</b></summary>

```bash
docker build -t ticket-tally .
docker run -p 5000:5000 --env-file .env ticket-tally
```

`entrypoint.sh` runs `flask db upgrade` before starting Gunicorn, so migrations are applied automatically on every container start. The final process is:

```bash
gunicorn --worker-class gthread --workers=1 --threads=4 --bind 0.0.0.0:${PORT:-5000} run:app
```

The `gthread` worker class with a single worker/multiple threads is used deliberately for compatibility with Flask‑SocketIO's threading async mode.

</details>

---

## 🔁 Database Migration (SQLite → PostgreSQL)

`migrate_sqlite_to_postgres.py` is a standalone, non‑ORM data migration script for moving an existing local SQLite database into PostgreSQL.

- Opens the SQLite file **read‑only** and never modifies it.
- Wraps all PostgreSQL writes in a single transaction, rolling back entirely on any failure.
- Preserves primary key IDs and validates enum values (`UserRole`, `TicketStatus`, `TicketPriority`) before inserting.
- Does not use the ORM, Flask, or Alembic — it talks to Postgres directly via `psycopg2`.

> [!TIP]
> **When to use it:** only if you have existing data in a local `ticket_tally.db` SQLite file that you want to carry over when switching to PostgreSQL (e.g. moving from local development to a Postgres‑backed deployment). Fresh deployments (Docker Compose, Render) don't need it — `flask db upgrade` alone builds an empty Postgres schema.

> [!WARNING]
> **Required setup:** the script reads `DATABASE_URL` from a `.env` file and expects a local SQLite database on disk; the paths in the script's header (`SQLITE_PATH`, `ENV_PATH`) are Windows‑style absolute paths from the original author's machine and **must be edited** to match your environment before running it.
>
> **Precautions:** back up both databases first. This script performs real writes against PostgreSQL — review it end‑to‑end before running against anything other than a disposable/test database.

---

## ☁️ Deployment

> [!NOTE]
> This exact configuration is what's running the live deployment at **[ticket-tally.onrender.com](https://ticket-tally.onrender.com)** — the steps below aren't theoretical, they're the real pipeline.

### Render.com

`render.yaml` defines a single Python web service:

| Stage | Command / Behavior |
|---|---|
| Build | `pip install --upgrade pip && pip install -r requirements.txt` |
| Pre‑deploy | `flask db upgrade` — migrations run automatically before each deploy |
| Start | `gunicorn --worker-class gthread --workers=1 --threads=4 --bind 0.0.0.0:$PORT run:app` |
| Auto‑generated secrets | `SECRET_KEY` and `JWT_SECRET_KEY`, generated by Render on first deploy |
| Manually‑set secrets (`sync: false`) | `DATABASE_URL`, `MAIL_SERVER`, `MAIL_USERNAME`, `MAIL_PASSWORD`, `BASE_URL`, `CORS_ALLOWED_ORIGINS` |
| Logging | `JSON_LOGGING=True` — structured JSON log output (custom `JSONFormatter` in `app/main.py`) |

To deploy: connect the repository to Render, let it pick up `render.yaml`, then fill in the `sync: false` environment variables (including a managed PostgreSQL `DATABASE_URL`) in the Render dashboard before the first deploy.

### Docker / Self‑Hosted

Use `docker-compose.yml` as a starting point for a self‑hosted deployment behind your own reverse proxy/TLS terminator, or adapt the `Dockerfile` directly for other container platforms (e.g. Kubernetes, ECS) — see [Docker Setup](#-docker-setup).

### CI

`.github/workflows/python-app.yml` runs on every push and pull request to `main`: it installs `requirements.txt` plus `pytest`/`pytest-mock`, and runs `python -m pytest tests/`. It does **not** build/push a Docker image or deploy — it is a test‑only CI gate, not a full CD pipeline.

---

## 🧪 Testing

| | |
|---|---|
| **Framework** | Pytest, using Flask's test client against an app created with `TestingConfig` (in‑memory SQLite, rate limiting disabled). |
| **Location** | `tests/` — 18 files, each targeting a specific feature area: auth, announcements, agent directory, CSAT, dashboard/performance report export, data retention, event handling, GitHub integration, project restrictions, rate limiting, reopen requests, SLA, team assignment/mapping, ticket ageing, and a general "casing standardization"/"phase 1 remediation" regression suite. |
| **Type** | Primarily integration‑style tests — they spin up a real (in‑memory) Flask app and database per test via a `db.create_all()` / `db.drop_all()` fixture, and exercise routes end‑to‑end through the test client rather than mocking the ORM. |
| **Fixtures** | Each test module defines its own `app`/`client` pytest fixtures (no shared `conftest.py`); most also create the specific users/tickets/teams they need inline. |

```bash
# Run the full suite
pytest

# Run a single file or test
pytest tests/test_sla.py
pytest tests/test_sla.py::test_sla_breach_detection
```

> [!TIP]
> **Verified result:** running `pytest tests/` against this repository (Python 3.12, dependencies from `requirements.txt`) produces **81 passed** with no failures.

---

## 🔧 Development Workflow

1. Create a feature branch off `main`.
2. Make your changes.
3. Run the test suite (`pytest`) and add/update tests for any behavior change.
4. Commit with a clear, descriptive message.
5. Open a pull request against `main` — the GitHub Actions workflow will automatically run the test suite.

The repository does not currently include a linter or code‑formatter configuration (no `.flake8`, `pyproject.toml` lint config, `black`, or `pre-commit` setup was found), so no formatting/linting step is enforced beyond what CI runs (tests only).

---

## ⚠️ Known Limitations / Future Improvements

> [!IMPORTANT]
> Listed here deliberately and honestly — these are documented engineering trade‑offs, not hidden gaps.

- **Ticket claim concurrency** relies on an application‑level re‑check rather than a database row lock (`SELECT ... FOR UPDATE`) or optimistic‑locking version column; acceptable for typical internal‑tool load, but not airtight under very high write concurrency on a single ticket.
- **SLA breach detection is read‑time only** — there's no background job that proactively notifies staff the moment an SLA is breached; breaches surface only when a ticket or dashboard is viewed.
- **Real‑time events are globally broadcast**, not scoped to Socket.IO rooms per user/team, so all connected clients receive every `live_activity`/`calendar_update` event and must filter client‑side.
- **No automated code formatting or linting** is configured in CI beyond the Pytest suite.
- **No API versioning strategy beyond the current `/api/v1` prefix** — there's no visible plan/tooling for a `v2` migration path.
- **Email delivery is synchronous** and best‑effort (`smtplib` calls are wrapped in try/except and logged on failure) — there is no retry queue or dead‑letter handling if SMTP is temporarily unavailable.
- **No caching layer** for expensive analytics queries; dashboard endpoints recompute aggregates on every request.
- **Migration script paths are hardcoded** to the original author's Windows environment and require manual editing before use (see [Database Migration](#-database-migration-sqlite--postgresql)).
- **No explicit database indexing strategy** documented beyond primary/foreign keys and the unique constraints defined on models (e.g. `User.email`, `SLA.priority`).
- **No dedicated observability/APM integration** — logging is JSON‑structured in production but there's no tracing, metrics export, or error‑tracking service wired in.

---

## 🤝 Contributing

1. Fork the repository.
2. Create a branch for your change: `git checkout -b feature/your-feature`.
3. Make your changes, following the existing service‑layer/route‑thin pattern.
4. Add or update tests under `tests/` for any behavioral change.
5. Ensure `pytest` passes locally.
6. Open a pull request describing the change and its motivation.

---

## 📄 License

No license has currently been specified for this repository. No `LICENSE` file was found at the repository root or elsewhere in the codebase.

---

<div align="center">

<br>

## 🎟️ Ticket‑Tally is live. Go break it.

### 🌐 [**ticket-tally.onrender.com**](https://ticket-tally.onrender.com)

<sub>Demo login required — no signup, no setup, no waiting.</sub>

<br>

---

<br>

**Author / Acknowledgments**

Maintained under the GitHub account [`Tanish1808`](https://github.com/Tanish1808). No additional contributor or acknowledgment information beyond the repository's own commit history could be verified from the codebase.

<sub>Built with Flask, SQLAlchemy, and Socket.IO — architected, deployed, and hardened end to end.</sub>

</div>