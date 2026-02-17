# File Tree: Trial_Ticket_Tally_01

**Generated:** 2/10/2026, 3:22:45 AM
**Root Path:** `d:\Trial_Ticket_Tally_01`

```
├── app
│   ├── api
│   │   ├── v1
│   │   │   ├── __init__.py
│   │   │   ├── admin_routes.py
│   │   │   ├── analytics_routes.py
│   │   │   ├── auth_routes.py
│   │   │   ├── it_staff_routes.py
│   │   │   ├── notification_routes.py
│   │   │   ├── project_routes.py
│   │   │   ├── ticket_routes.py
│   │   │   └── user_routes.py
│   │   └── __init__.py
│   ├── core
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── constants.py
│   │   ├── database.py
│   │   └── extensions.py
│   ├── middleware
│   │   ├── __init__.py
│   │   └── auth_middleware.py
│   ├── models
│   │   ├── __init__.py
│   │   ├── comment.py
│   │   ├── message.py
│   │   ├── notification.py
│   │   ├── project.py
│   │   ├── sla.py
│   │   ├── team.py
│   │   ├── ticket.py
│   │   ├── ticket_status_history.py
│   │   └── user.py
│   ├── schemas
│   │   ├── __init__.py
│   │   ├── auth_schema.py
│   │   ├── dashboard_schema.py
│   │   ├── team_schema.py
│   │   └── ticket_schema.py
│   ├── services
│   │   ├── __init__.py
│   │   ├── auth_service.py
│   │   ├── email_service.py
│   │   ├── email_templates.py
│   │   ├── notification_service.py
│   │   ├── pdf_service.py
│   │   ├── sla_service.py
│   │   ├── ticket_pdf_service.py
│   │   └── ticket_service.py
│   ├── static
│   │   ├── css
│   │   │   ├── auth.css
│   │   │   ├── dashboard.css
│   │   │   ├── fixes.css
│   │   │   ├── landing.css
│   │   │   ├── main.css
│   │   │   └── tickets.css
│   │   └── js
│   │       ├── admin-dashboard.js
│   │       ├── auth.js
│   │       ├── employee-dashboard.js
│   │       ├── itstaff-dashboard.js
│   │       ├── landing.js
│   │       ├── notifications.js
│   │       ├── profile.js
│   │       ├── projects.js
│   │       ├── theme.js
│   │       └── ticket-details.js
│   ├── templates
│   │   ├── admin-dashboard.html
│   │   ├── contact.html
│   │   ├── employee-dashboard.html
│   │   ├── forgot_password.html
│   │   ├── index.html
│   │   ├── itstaff-dashboard.html
│   │   ├── legal.html
│   │   ├── login.html
│   │   ├── profile.html
│   │   ├── projects.html
│   │   ├── reset_password.html
│   │   ├── signup.html
│   │   ├── status_modal_snippet.html
│   │   └── ticket-details.html
│   ├── utils
│   │   ├── __init__.py
│   │   ├── jwt.py
│   │   ├── password.py
│   │   ├── pdf_generator.py
│   │   ├── time_utils.py
│   │   └── token.py
│   ├── websocket
│   │   ├── __init__.py
│   │   └── ticket_socket.py
│   ├── __init__.py
│   ├── main.py
│   └── web_routes.py
├── migrations
│   ├── versions
│   │   ├── 808296bbfc5b_initial_migration.py
│   │   ├── 8b4ce391f20a_add_department_to_user.py
│   │   └── d52eea373c05_add_notification_model.py
│   ├── README
│   ├── alembic.ini
│   ├── env.py
│   └── script.py.mako
├── static
│   └── css
│       └── main.css
├── tests
│   ├── test_project_restriction.py
│   └── test_team_assignment.py
├── .gitignore
├── PROJECT_EXPLANATION.txt
├── README.md
├── check_users.py
├── create_admin.py
├── debug_users.py
├── delete_test_users.py
├── dump.txt
├── dump_users.py
├── fix_assignments.py
├── fix_db.py
├── migrate_comments.py
├── requirements.txt
├── reset_db.py
├── run.py
├── seed_teams.py
├── simulate_users.py
├── simulate_workflow.py
├── test_api.py
├── test_api_v2.py
├── update_db.py
└── user_list.txt
```

