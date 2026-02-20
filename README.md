# <div align="center">🎟️ Ticket-Tally</div>

<div align="center">
  <h3><strong>Modern • Theme-Aware • Intelligent ITSM</strong></h3>
  <em>A production-grade IT Service Management platform with real-time analytics and automated workflows.</em>
</div>

<br />

<div align="center">
  <img src="https://img.shields.io/badge/Python-3.9+-3776AB?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/Flask-Current-000000?style=for-the-badge&logo=flask&logoColor=white" />
  <img src="https://img.shields.io/badge/SQLAlchemy-ORM-red?style=for-the-badge" />
  <img src="https://img.shields.io/badge/Bootstrap-5.3-7952B3?style=for-the-badge&logo=bootstrap&logoColor=white" />
  <img src="https://img.shields.io/badge/Socket.io-Real--Time-010101?style=for-the-badge&logo=socket.io&logoColor=white" />
</div>

---

## 📋 Table of Contents

- [🚀 Vision & Key Features](#-vision--key-features)
- [📸 Screenshots](#-screenshots)
- [🏗️ System Architecture](#️-system-architecture)
- [📂 Project Structure Map](#-project-structure-map)
- [🛠️ Stack Analysis](#️-stack-analysis)
- [📚 API Documentation](#-api-documentation)
- [⚙️ Quick Start Guide](#️-quick-start-guide)
- [🤝 Contributing](#-contributing)
- [📄 License](#-license)

---

## 🚀 Vision & Key Features

**Ticket-Tally** is meticulously engineered to streamline the bridge between end-users and technical support. It goes beyond simple ticket tracking, offering a data-driven approach to incident management.

### 🌓 Aesthetic Excellence
*   **Dual-Theme Intelligence:** Advanced CSS logic for seamless Light/Dark mode transitions with zero contrast loss.
*   **Premium Components:** Glassmorphic notifications, interactive Chart.js dashboards, and pill-shaped pagination.
*   **Responsive Core:** Pixel-perfect layout across mobile, tablet, and desktop using Bootstrap 5.3.

### ⚙️ Core Functionality
*   **Triple-Role Access:** Dedicated modules for **Admin** (Control), **IT Staff** (Resolution), and **Employee** (Request).
*   **Smart Lifecycle:** Automated ticket assignment, claim system, SLA tracking, and resolution reporting.
*   **Project Management:** Full CRUD operations for projects with team assignments, progress tracking, and deadline management.
*   **Integrated Communications:** SMTP-driven email triggers with dynamic PDF report generation and in-app notifications.
*   **Safe-Concurrency:** Protection against race conditions when multiple staff approach the same ticket (workload limits, claim system).
*   **Comment & Timeline:** Full conversation history on tickets with status change tracking.

---

## 🏗️ System Architecture

The project adheres to a clean, modular architecture, ensuring separation of concerns and effortless scalability.

```
mermaid
graph TD
    User((User)) -->|Auth/Requests| Flask[Flask Backend]
    Flask -->|Logic| Services[Service Layer]
    Services -->|Emails| SMTP[[SMTP Server]]
    Services -->|PDFs| ReportLab[[ReportLab Engine]]
    Flask -->|Persistence| DB[(SQLAlchemy DB)]
    Flask -->|Real-time| SIO[Socket.io Hub]
    SIO -->|Updates| User
```

---

## 📂 Project Structure Map

```
Trial_Ticket_Tally_01/
├── app/                        # 📦 Core Application Bundle
│   ├── api/v1/                 # 🚀 RESTful API Layer
│   │   ├── admin_routes.py     # System & Performance metrics, message management
│   │   ├── analytics_routes.py # Analytics and reporting endpoints
│   │   ├── auth_routes.py      # Authentication, login, register, password reset
│   │   ├── it_staff_routes.py # IT Staff specific operations
│   │   ├── notification_routes.py # Notification handling
│   │   ├── project_routes.py   # Project CRUD with team assignment
│   │   ├── ticket_routes.py    # Ticket lifecycle, comments, PDF generation
│   │   └── user_routes.py      # User profile management
│   ├── core/                   # 🧠 System Backbone
│   │   ├── config.py           # Application configuration & environment
│   │   ├── constants.py        # Enums (UserRole, TicketStatus, TicketPriority, ProjectStatus, SLAStatus)
│   │   ├── database.py         # SQLAlchemy engine & session setup
│   │   └── extensions.py       # Flask extensions initialization
│   ├── middleware/             # 🛡️ Request Processing
│   │   └── auth_middleware.py  # JWT token validation & role-based access
│   ├── models/                 # 💾 Persistent Data Models (ORM)
│   │   ├── comment.py          # Ticket comments
│   │   ├── message.py          # Contact form messages
│   │   ├── notification.py     # In-app notifications
│   │   ├── project.py          # Projects with team management
│   │   ├── sla.py              # SLA definitions
│   │   ├── team.py             # Team definitions
│   │   ├── ticket.py           # Main ticket model
│   │   ├── ticket_status_history.py # Status change tracking
│   │   └── user.py             # User accounts with roles
│   ├── schemas/                # 📝 Data Validation (Pydantic)
│   ├── services/               # 🛠️ Decoupled Business Handlers
│   │   ├── auth_service.py     # Authentication logic
│   │   ├── email_service.py    # SMTP email sending
│   │   ├── email_templates.py  # HTML email templates
│   │   ├── notification_service.py # Push notifications
│   │   ├── pdf_service.py      # PDF generation with ReportLab
│   │   ├── sla_service.py      # SLA management
│   │   ├── ticket_pdf_service.py # Ticket-specific PDF reports
│   │   └── ticket_service.py   # Core ticket operations
│   ├── static/                 # 🎨 UI Assets
│   │   ├── css/                # Theme-aware styling (auth, dashboard, tickets, landing)
│   │   └── js/                 # Client-side logic (theme, dashboards, notifications)
│   ├── templates/              # 🖼️ Presentation Layer (Jinja2 HTML)
│   ├── utils/                  # 🔧 Utility Functions
│   │   ├── jwt.py              # JWT token handling
│   │   ├── password.py         # Password hashing
│   │   ├── pdf_generator.py   # PDF generation utilities
│   │   ├── time_utils.py       # Date/time helpers
│   │   └── token.py            # Token management
│   ├── websocket/              # 📡 Real-time Push Handlers
│   │   └── ticket_socket.py   # Socket.io event handlers
│   ├── __init__.py            # App factory setup
│   ├── main.py                 # Application Factory (create_app)
│   └── web_routes.py           # Page View Controller
├── migrations/                 # 📜 Versioned DB Schema Evolution (Alembic)
├── tests/                      # 🧪 Unit Tests
├── instance/                   # 📁 Local Storage (SQLite)
├── run.py                      # ⚡ Entry Point (0.0.0.0:5000)
├── requirements.txt            # 📦 External Dependencies
└── README.md                   # 📄 Project Documentation
```

---

## 🛠️ Stack Analysis

| Layer | Technology | Rationale |
| :--- | :--- | :--- |
| **Logic** | **Flask** | Lightweight, high-extensibility Python framework. |
| **Storage** | **SQLAlchemy** | Professional ORM for seamless DB migrations/switching. |
| **Interface** | **Bootstrap 5.3** | Clean, responsive components and grid system. |
| **Updates** | **Socket.io** | Low-latency real-time notification push. |
| **Analytics** | **Chart.js** | Interactive, lightweight data visualization. |

---

## 📚 API Documentation

Ticket-Tally provides a comprehensive REST API for managing IT service tickets. Below are the key endpoints:

### Authentication Endpoints
- `POST /api/v1/auth/login` - User authentication
- `POST /api/v1/auth/signup` - User registration
- `POST /api/v1/auth/logout` - User logout
- `POST /api/v1/auth/demo-login` - Demo user login (for testing)
- `POST /api/v1/auth/forgot-password` - Initiate password reset
- `POST /api/v1/auth/reset-password` - Complete password reset

### Ticket Management
- `GET /api/v1/tickets` - List tickets (filtered by user role)
- `POST /api/v1/tickets` - Create new ticket
- `GET /api/v1/tickets/{id}` - Get ticket details with comments and timeline
- `PUT /api/v1/tickets/{id}` - Update ticket
- `PATCH /api/v1/tickets/{id}` - Partially update ticket
- `POST /api/v1/tickets/{id}/comments` - Add comment to ticket
- `GET /api/v1/tickets/{id}/pdf` - Download ticket PDF report
- `POST /api/v1/tickets/{id}/withdraw` - Withdraw ticket (creator only)
- `POST /api/v1/tickets/{id}/claim` - Claim ticket (IT staff)
- `POST /api/v1/tickets/check-duplicate` - Check for duplicate tickets

### Project Management
- `GET /api/v1/projects` - List all projects
- `POST /api/v1/projects` - Create new project (Admin only)
- `GET /api/v1/projects/{id}` - Get project details
- `PATCH /api/v1/projects/{id}` - Update project (Admin only)
- `DELETE /api/v1/projects/{id}` - Delete project (Admin only)

### User Management
- `GET /api/v1/users` - List users (admin only)
- `GET /api/v1/users/{id}` - Get user profile
- `PUT /api/v1/users/{id}` - Update user profile

### Admin Endpoints
- `GET /api/v1/admin/analytics` - System analytics and metrics
- `GET /api/v1/admin/users` - User management
- `POST /api/v1/admin/users` - Create user
- `DELETE /api/v1/admin/users/{id}` - Delete user
- `GET /api/v1/admin/messages` - Get contact form messages
- `PATCH /api/v1/admin/messages/{id}/read` - Mark message as read

### Notification Endpoints
- `GET /api/v1/notifications` - Get user notifications
- `PUT /api/v1/notifications/{id}/read` - Mark notification as read

> [!NOTE]
> All API endpoints require authentication via JWT tokens. Include the token in the `Authorization` header as `Bearer <token>`.

For detailed API specifications, visit `/api/docs` when the application is running.

---

## ⚙️ Quick Start Guide

### Prerequisites
- Python 3.9 or higher
- pip package manager
- Git (for cloning the repository)

### 1. Clone the Repository
```
bash
git clone https://github.com/your-username/Ticket-Tally.git
cd Ticket-Tally
```

### 2. Environment Setup
```
bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Unix/MacOS:
source venv/bin/activate
```

### 3. Install Dependencies
```
bash
pip install -r requirements.txt
```

### 4. Database Initialization
```
bash
# Run database migrations
python run.py db upgrade

# Seed initial data (optional)
python seed_teams.py
python create_admin.py
```

### 5. Run the Application
```
bash
python run.py
```

The application will be available at `http://localhost:5000`

### 6. Access the Application
- **Web Interface:** Navigate to `http://localhost:5000`
- **API Documentation:** Visit `http://localhost:5000/api/docs`

> [!TIP]
> **Demo Login:** Use the demo login feature to explore the application with pre-configured test accounts.
> 
> **Demo Credentials:** 
> - Email: `demo@tickettally.com`
> - Password: `demo_password_secure_2026`

---

## 🤝 Contributing

We welcome contributions to Ticket-Tally! Here's how you can get involved:

### Development Setup
1. Fork the repository
2. Clone your fork: `git clone https://github.com/your-username/Ticket-Tally.git`
3. Create a feature branch: `git checkout -b feature/amazing-feature`
4. Follow the Quick Start Guide above to set up the environment

### Guidelines
- **Code Style:** Follow PEP 8 for Python code
- **Commits:** Use clear, descriptive commit messages
- **Testing:** Add tests for new features
- **Documentation:** Update README and docstrings as needed

### Pull Request Process
1. Ensure your code passes all tests
2. Update the README.md if necessary
3. Create a pull request with a clear description
4. Wait for review and address any feedback

### Reporting Issues
- Use the GitHub Issues tab
- Provide detailed steps to reproduce
- Include screenshots if applicable
- Specify your environment (OS, Python version, etc.)

---

## 📄 License

This project is licensed under the **MIT License**. See the [LICENSE](LICENSE) file for details.

---

<div align="center">
  <p><strong>Made with ❤️ for efficient IT service management</strong></p>
  <p>
    <a href="#-vision--key-features">Features</a> •
    <a href="#️-quick-start-guide">Quick Start</a> •
    <a href="#-api-documentation">API Docs</a> •
    <a href="#-contributing">Contributing</a>
  </p>
</div>
