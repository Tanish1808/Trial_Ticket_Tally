"""
SQLite → PostgreSQL Data Migration Script
Project: Ticket-Tally
Prepared: 2026-08-20

SAFETY CONTRACT:
  - SQLite is opened READ-ONLY (uri=True, mode=ro). Never modified.
  - All PostgreSQL changes are in ONE transaction. ROLLBACK on any failure.
  - No ORM, no Flask, no Alembic, no flask db commands.
  - No TRUNCATE, DROP TABLE, DELETE, or CASCADE.
  - Preserves all primary-key IDs.
  - Do NOT run this script without explicit approval.

USAGE (when approved):
  cd d:/Trial_Ticket_Tally_01
  .\\venv\\Scripts\\python.exe migrate_sqlite_to_postgres.py

EXIT CODES:
  0 = Migration committed successfully
  1 = Pre-flight check failed (nothing inserted)
  2 = Migration failed mid-way (rolled back)
"""

import os
import sys
import json
import sqlite3
from datetime import datetime

import psycopg2
from dotenv import load_dotenv

# ─── CONFIG ───────────────────────────────────────────────────────────────────

SQLITE_PATH = "d:/Trial_Ticket_Tally_01/instance/ticket_tally.db"
ENV_PATH    = "d:/Trial_Ticket_Tally_01/.env"

load_dotenv(ENV_PATH)
DATABASE_URL = os.getenv("DATABASE_URL", "")

if not DATABASE_URL:
    print("ERROR: DATABASE_URL is not set in .env")
    sys.exit(1)

# psycopg2 needs postgresql:// not postgresql+psycopg2://
PG_URL = DATABASE_URL.replace("postgresql+psycopg2://", "postgresql://")

# ─── KNOWN VALID ENUM VALUES ──────────────────────────────────────────────────

VALID_USER_ROLES      = {"ADMIN", "EMPLOYEE", "IT_STAFF"}
VALID_TICKET_STATUS   = {"OPEN", "IN_PROGRESS", "RESOLVED", "CLOSED", "WITHDRAWN"}
VALID_TICKET_PRIORITY = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}

# ─── HELPERS ──────────────────────────────────────────────────────────────────

def to_bool(val):
    """Convert SQLite integer 0/1 (or None) to Python bool / None."""
    if val is None:
        return None
    return bool(int(val))

def to_json_str(val):
    """Validate and return JSON string, or None. Raises ValueError on bad JSON."""
    if val is None:
        return None
    if isinstance(val, str):
        json.loads(val)   # validate — raises ValueError if corrupt
        return val
    return json.dumps(val)  # shouldn't happen from SQLite, but handle it

def validate_enum(val, valid_set, field_name, row_id):
    """Assert val is in valid_set. Raises ValueError on mismatch."""
    if val is None:
        return None
    if val not in valid_set:
        raise ValueError(
            f"Invalid enum value for {field_name}: {val!r} "
            f"(row id={row_id}, valid={valid_set})"
        )
    return val

def log(msg):
    ts = datetime.utcnow().strftime("%H:%M:%S")
    print(f"[{ts}]  {msg}")

def abort(pg_conn, msg, code=2):
    log(f"ABORT: {msg}")
    if pg_conn:
        pg_conn.rollback()
        log("PostgreSQL transaction ROLLED BACK.")
    sys.exit(code)

# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    print("=" * 65)
    print("  Ticket-Tally  SQLite -> PostgreSQL Data Migration")
    print("=" * 65)
    log("Script started. Nothing will be committed until all checks pass.")

    # ── Open SQLite READ-ONLY ─────────────────────────────────────────────────
    log("Opening SQLite in read-only mode...")
    try:
        sq_conn = sqlite3.connect(
            f"file:{SQLITE_PATH}?mode=ro",
            uri=True,
            check_same_thread=False,
        )
        sq_conn.row_factory = sqlite3.Row
        sq = sq_conn.cursor()
    except Exception as e:
        print(f"ERROR opening SQLite: {e}")
        sys.exit(1)
    log(f"SQLite opened (read-only): {SQLITE_PATH}")

    # ── Connect to PostgreSQL ─────────────────────────────────────────────────
    log("Connecting to PostgreSQL...")
    pg_conn = None
    try:
        pg_conn = psycopg2.connect(PG_URL)
        pg_conn.autocommit = False          # manual transaction control
        pg = pg_conn.cursor()
    except Exception as e:
        print(f"ERROR connecting to PostgreSQL: {e}")
        sys.exit(1)
    from urllib.parse import urlparse
    p = urlparse(PG_URL)
    log(f"PostgreSQL connected: {p.scheme}://***@{p.hostname}{p.path}")

    # =========================================================================
    # PRE-FLIGHT CHECKS  (read-only — no inserts yet)
    # =========================================================================
    log("\n--- PRE-FLIGHT CHECKS ---")

    # Check 1: PG baseline — only 8 seeded rows allowed outside teams/team_mappings
    log("Check 1: Verifying PostgreSQL baseline (only 8 seeded rows expected)...")
    data_tables = [
        "slas", "teams", "team_mappings", "users", "tickets", "projects",
        "project_team", "ticket_status_history", "comments", "notifications",
        "reopen_requests", "csat_feedbacks", "activity_logs",
        "announcements", "events", "messages",
    ]
    pg_counts = {}
    for t in data_tables:
        pg.execute(f'SELECT COUNT(*) FROM "{t}"')
        pg_counts[t] = pg.fetchone()[0]

    unexpected = {t: n for t, n in pg_counts.items()
                  if t not in ("teams", "team_mappings") and n != 0}
    if unexpected:
        abort(pg_conn,
              f"PostgreSQL already has unexpected data: {unexpected}. "
              f"Aborting to protect existing data.",
              code=1)

    if pg_counts.get("teams", 0) != 4:
        abort(pg_conn,
              f"Expected exactly 4 seeded rows in teams, found {pg_counts.get('teams')}",
              code=1)
    if pg_counts.get("team_mappings", 0) != 4:
        abort(pg_conn,
              f"Expected exactly 4 seeded rows in team_mappings, "
              f"found {pg_counts.get('team_mappings')}",
              code=1)
    log("  Check 1 PASS: PostgreSQL has only expected 8 seeded rows.")

    # Check 2: teams ids 1-4 match SQLite exactly
    log("Check 2: Verifying teams ids 1-4 match between SQLite and PostgreSQL...")
    sq.execute("SELECT id, name FROM teams WHERE id <= 4 ORDER BY id")
    sq_teams = {r["id"]: r["name"] for r in sq.fetchall()}
    pg.execute("SELECT id, name FROM teams ORDER BY id")
    pg_teams = {r[0]: r[1] for r in pg.fetchall()}

    for tid in range(1, 5):
        if sq_teams.get(tid) != pg_teams.get(tid):
            abort(pg_conn,
                  f"teams mismatch at id={tid}: "
                  f"SQLite={sq_teams.get(tid)!r}, PG={pg_teams.get(tid)!r}",
                  code=1)
    log("  Check 2 PASS: teams ids 1-4 are identical.")

    # Check 3: team_mappings ids 1-4 match SQLite exactly
    log("Check 3: Verifying team_mappings ids 1-4 match SQLite...")
    sq.execute("SELECT id, category, team_id FROM team_mappings ORDER BY id")
    sq_tm = {r["id"]: (r["category"], r["team_id"]) for r in sq.fetchall()}
    pg.execute("SELECT id, category, team_id FROM team_mappings ORDER BY id")
    pg_tm = {r[0]: (r[1], r[2]) for r in pg.fetchall()}

    for mid in range(1, 5):
        if sq_tm.get(mid) != pg_tm.get(mid):
            abort(pg_conn,
                  f"team_mappings mismatch at id={mid}: "
                  f"SQLite={sq_tm.get(mid)}, PG={pg_tm.get(mid)}",
                  code=1)
    log("  Check 3 PASS: team_mappings ids 1-4 are identical.")

    # Check 4: SQLite is truly read-only
    log("Check 4: Confirming SQLite is read-only...")
    try:
        sq.execute("INSERT INTO teams (name) VALUES ('__readonly_test__')")
        sq_conn.rollback()
        abort(pg_conn,
              "CRITICAL: SQLite did NOT reject a write! Safety contract violated.",
              code=1)
    except sqlite3.OperationalError as e:
        if "readonly" in str(e).lower():
            log("  Check 4 PASS: SQLite correctly rejected a write (read-only confirmed).")
        else:
            raise

    log("--- ALL PRE-FLIGHT CHECKS PASSED ---\n")

    # =========================================================================
    # BEGIN SINGLE POSTGRESQL TRANSACTION
    # (autocommit=False means we are already in an implicit transaction)
    # =========================================================================
    log("PostgreSQL transaction is active (autocommit=False).")
    total_inserted = 0

    try:

        # ── PHASE 1a: slas ────────────────────────────────────────────────────
        log("Phase 1a: slas (no FK dependencies)...")
        sq.execute(
            "SELECT id, priority, response_time_hours, resolution_time_hours, created_at "
            "FROM slas ORDER BY id"
        )
        for r in sq.fetchall():
            validate_enum(r["priority"], VALID_TICKET_PRIORITY, "slas.priority", r["id"])
            pg.execute(
                "INSERT INTO slas (id, priority, response_time_hours, "
                "resolution_time_hours, created_at) "
                "VALUES (%s, %s::ticketpriority, %s, %s, %s)",
                (r["id"], r["priority"],
                 r["response_time_hours"], r["resolution_time_hours"],
                 r["created_at"])
            )
            total_inserted += 1
        log(f"  slas: 4 rows inserted.")

        # ── PHASE 1b: messages ────────────────────────────────────────────────
        log("Phase 1b: messages (no FK dependencies)...")
        sq.execute(
            "SELECT id, name, email, subject, message, created_at, is_read "
            "FROM messages ORDER BY id"
        )
        for r in sq.fetchall():
            pg.execute(
                "INSERT INTO messages (id, name, email, subject, message, created_at, is_read) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (r["id"], r["name"], r["email"], r["subject"],
                 r["message"], r["created_at"], to_bool(r["is_read"]))
            )
            total_inserted += 1
        log(f"  messages: 8 rows inserted.")

        # ── PHASE 2: teams — INSERT ONLY id=5 ────────────────────────────────
        log("Phase 2: teams (inserting only id=5 'Human Resources'; ids 1-4 already seeded)...")
        sq.execute("SELECT id, name, created_at FROM teams WHERE id = 5")
        row = sq.fetchone()
        if row is None:
            abort(pg_conn,
                  "Expected team id=5 in SQLite but not found. Aborting.",
                  code=2)
        pg.execute(
            "INSERT INTO teams (id, name, created_at) VALUES (%s, %s, %s)",
            (row["id"], row["name"], row["created_at"])
        )
        total_inserted += 1
        log(f"  Inserted team: id={row['id']}, name={row['name']!r}")

        # ── team_mappings — SKIP (seeded rows verified identical) ─────────────
        log("team_mappings: SKIPPED — 4 seeded rows already verified identical to SQLite.")

        # ── PHASE 3: users ────────────────────────────────────────────────────
        log("Phase 3: users (preserving IDs, bcrypt hashes, all fields)...")
        sq.execute(
            "SELECT id, email, password_hash, full_name, role, department, "
            "team_id, created_at, is_active, preferences, specializations "
            "FROM users ORDER BY id"
        )
        user_count = 0
        for r in sq.fetchall():
            validate_enum(r["role"], VALID_USER_ROLES, "users.role", r["id"])
            pg.execute(
                "INSERT INTO users (id, email, password_hash, full_name, role, "
                "department, team_id, created_at, is_active, preferences, specializations) "
                "VALUES (%s, %s, %s, %s, %s::userrole, %s, %s, %s, %s, %s, %s)",
                (
                    r["id"],
                    r["email"],
                    r["password_hash"],            # bcrypt — copied verbatim, never re-hashed
                    r["full_name"],
                    r["role"],
                    r["department"],
                    r["team_id"],
                    r["created_at"],
                    to_bool(r["is_active"]),
                    to_json_str(r["preferences"]),
                    to_json_str(r["specializations"]),
                )
            )
            user_count += 1
            total_inserted += 1
        log(f"  users: {user_count} rows inserted (passwords preserved, never printed).")

        # ── PHASE 4a: tickets ─────────────────────────────────────────────────
        log("Phase 4a: tickets (including category and is_demo explicitly)...")
        sq.execute(
            "SELECT id, title, description, category, status, priority, "
            "is_demo, created_by_id, assigned_to_id, team_id, "
            "github_pr_url, created_at, updated_at, is_deleted, deleted_at "
            "FROM tickets ORDER BY id"
        )
        ticket_count = 0
        for r in sq.fetchall():
            validate_enum(r["status"],   VALID_TICKET_STATUS,   "tickets.status",   r["id"])
            validate_enum(r["priority"], VALID_TICKET_PRIORITY, "tickets.priority", r["id"])
            pg.execute(
                "INSERT INTO tickets (id, title, description, category, status, priority, "
                "is_demo, created_by_id, assigned_to_id, team_id, github_pr_url, "
                "created_at, updated_at, is_deleted, deleted_at) "
                "VALUES (%s, %s, %s, %s, %s::ticketstatus, %s::ticketpriority, "
                "%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (
                    r["id"],
                    r["title"],
                    r["description"],
                    r["category"],                 # explicit — NOT NULL
                    r["status"],
                    r["priority"],
                    to_bool(r["is_demo"]),          # explicit — NOT NULL, boolean
                    r["created_by_id"],
                    r["assigned_to_id"],
                    r["team_id"],
                    r["github_pr_url"],
                    r["created_at"],
                    r["updated_at"],
                    to_bool(r["is_deleted"]),
                    r["deleted_at"],
                )
            )
            ticket_count += 1
            total_inserted += 1
        log(f"  tickets: {ticket_count} rows inserted.")

        # ── PHASE 4b: projects ────────────────────────────────────────────────
        log("Phase 4b: projects...")
        sq.execute(
            "SELECT id, name, description, status, priority, start_date, "
            "deadline, progress, created_by_id, created_at, updated_at, "
            "is_deleted, deleted_at "
            "FROM projects ORDER BY id"
        )
        for r in sq.fetchall():
            pg.execute(
                "INSERT INTO projects (id, name, description, status, priority, "
                "start_date, deadline, progress, created_by_id, created_at, "
                "updated_at, is_deleted, deleted_at) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (
                    r["id"], r["name"], r["description"],
                    r["status"], r["priority"],
                    r["start_date"], r["deadline"], r["progress"],
                    r["created_by_id"], r["created_at"], r["updated_at"],
                    to_bool(r["is_deleted"]), r["deleted_at"],
                )
            )
            total_inserted += 1
        log(f"  projects: 3 rows inserted.")

        # ── PHASE 5a: project_team (composite PK — no id column) ──────────────
        log("Phase 5a: project_team (composite key; no id column)...")
        sq.execute("SELECT project_id, user_id FROM project_team")
        pt_count = 0
        for r in sq.fetchall():
            pg.execute(
                "INSERT INTO project_team (project_id, user_id) VALUES (%s, %s)",
                (r["project_id"], r["user_id"])
            )
            pt_count += 1
            total_inserted += 1
        log(f"  project_team: {pt_count} rows inserted.")

        # ── PHASE 5b: ticket_status_history ───────────────────────────────────
        log("Phase 5b: ticket_status_history...")
        sq.execute(
            "SELECT id, ticket_id, old_status, new_status, changed_by_id, changed_at "
            "FROM ticket_status_history ORDER BY id"
        )
        tsh_count = 0
        for r in sq.fetchall():
            if r["old_status"] is not None:
                validate_enum(r["old_status"], VALID_TICKET_STATUS,
                              "ticket_status_history.old_status", r["id"])
            validate_enum(r["new_status"], VALID_TICKET_STATUS,
                          "ticket_status_history.new_status", r["id"])
            # Cast None safely for nullable enum column
            old_s = r["old_status"]
            pg.execute(
                "INSERT INTO ticket_status_history "
                "(id, ticket_id, old_status, new_status, changed_by_id, changed_at) "
                "VALUES (%s, %s, "
                + ("NULL" if old_s is None else "%s::ticketstatus") +
                ", %s::ticketstatus, %s, %s)",
                ([r["id"], r["ticket_id"]] +
                 ([] if old_s is None else [old_s]) +
                 [r["new_status"], r["changed_by_id"], r["changed_at"]])
            )
            tsh_count += 1
            total_inserted += 1
        log(f"  ticket_status_history: {tsh_count} rows inserted.")

        # ── PHASE 5c: reopen_requests ─────────────────────────────────────────
        log("Phase 5c: reopen_requests...")
        sq.execute(
            "SELECT id, reason, status, decline_reason, requested_at, "
            "resolved_at, ticket_id, requested_by_id, resolved_by_id "
            "FROM reopen_requests ORDER BY id"
        )
        for r in sq.fetchall():
            pg.execute(
                "INSERT INTO reopen_requests "
                "(id, reason, status, decline_reason, requested_at, "
                "resolved_at, ticket_id, requested_by_id, resolved_by_id) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (
                    r["id"], r["reason"], r["status"], r["decline_reason"],
                    r["requested_at"], r["resolved_at"],
                    r["ticket_id"], r["requested_by_id"], r["resolved_by_id"],
                )
            )
            total_inserted += 1
        log(f"  reopen_requests: 2 rows inserted.")

        # ── PHASE 5d: csat_feedbacks ──────────────────────────────────────────
        log("Phase 5d: csat_feedbacks...")
        sq.execute(
            "SELECT id, rating, comment, created_at, ticket_id, user_id "
            "FROM csat_feedbacks ORDER BY id"
        )
        for r in sq.fetchall():
            pg.execute(
                "INSERT INTO csat_feedbacks (id, rating, comment, created_at, ticket_id, user_id) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                (r["id"], r["rating"], r["comment"],
                 r["created_at"], r["ticket_id"], r["user_id"])
            )
            total_inserted += 1
        log(f"  csat_feedbacks: 4 rows inserted.")

        # ── PHASE 5e: announcements ───────────────────────────────────────────
        log("Phase 5e: announcements...")
        sq.execute(
            "SELECT id, title, message, is_active, expires_at, created_at, created_by_id "
            "FROM announcements ORDER BY id"
        )
        for r in sq.fetchall():
            if r["created_at"] is None:
                abort(pg_conn,
                      f"announcements id={r['id']} has NULL created_at "
                      f"but PostgreSQL column is NOT NULL.",
                      code=2)
            pg.execute(
                "INSERT INTO announcements "
                "(id, title, message, is_active, expires_at, created_at, created_by_id) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (
                    r["id"], r["title"], r["message"],
                    to_bool(r["is_active"]),
                    r["expires_at"], r["created_at"],
                    r["created_by_id"],
                )
            )
            total_inserted += 1
        log(f"  announcements: 3 rows inserted.")

        # ── PHASE 5f: events ──────────────────────────────────────────────────
        log("Phase 5f: events...")
        sq.execute(
            "SELECT id, title, description, event_type, start_time, end_time, "
            "created_by_id, created_at, updated_at, is_demo "
            "FROM events ORDER BY id"
        )
        for r in sq.fetchall():
            pg.execute(
                "INSERT INTO events "
                "(id, title, description, event_type, start_time, end_time, "
                "created_by_id, created_at, updated_at, is_demo) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (
                    r["id"], r["title"], r["description"],
                    r["event_type"], r["start_time"], r["end_time"],
                    r["created_by_id"], r["created_at"], r["updated_at"],
                    to_bool(r["is_demo"]),
                )
            )
            total_inserted += 1
        log(f"  events: 4 rows inserted.")

        # ── PHASE 5g: notifications ───────────────────────────────────────────
        # Only migrate notifications whose user_id exists in the users table.
        # Notifications referencing deleted users are orphaned rows; they have
        # no valid recipient and cannot be inserted without violating the
        # notifications_user_id_fkey FK constraint (user_id NOT NULL).
        log("Phase 5g: notifications (migrating only rows with valid user_id)...")
        sq.execute(
            "SELECT id, user_id, title, message, type, is_read, created_at "
            "FROM notifications "
            "WHERE user_id IN (SELECT id FROM users) "
            "ORDER BY id"
        )
        notif_count = 0
        for r in sq.fetchall():
            pg.execute(
                "INSERT INTO notifications (id, user_id, title, message, type, is_read, created_at) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (
                    r["id"], r["user_id"], r["title"], r["message"],
                    r["type"], to_bool(r["is_read"]), r["created_at"],
                )
            )
            notif_count += 1
            total_inserted += 1
        log(f"  notifications: {notif_count} valid rows inserted (orphans with missing user_id skipped).")

        # ── PHASE 5h: activity_logs ───────────────────────────────────────────
        log("Phase 5h: activity_logs (106 rows)...")
        sq.execute(
            "SELECT id, category, ticket_id, message, created_by, timestamp "
            "FROM activity_logs ORDER BY id"
        )
        al_count = 0
        for r in sq.fetchall():
            pg.execute(
                "INSERT INTO activity_logs (id, category, ticket_id, message, created_by, timestamp) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                (
                    r["id"], r["category"], r["ticket_id"],
                    r["message"], r["created_by"], r["timestamp"],
                )
            )
            al_count += 1
            total_inserted += 1
        log(f"  activity_logs: {al_count} rows inserted.")

        # ── PHASE 6: comments (top-level first, then nested) ──────────────────
        log("Phase 6: comments (top-level before nested to satisfy self-FK)...")

        # 6a: top-level comments (parent_id IS NULL)
        sq.execute(
            "SELECT id, text, created_at, ticket_id, user_id, parent_id "
            "FROM comments WHERE parent_id IS NULL ORDER BY id"
        )
        top_level = sq.fetchall()
        for r in top_level:
            pg.execute(
                "INSERT INTO comments (id, text, created_at, ticket_id, user_id, parent_id) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                (r["id"], r["text"], r["created_at"],
                 r["ticket_id"], r["user_id"], None)
            )
            total_inserted += 1
        log(f"  Inserted {len(top_level)} top-level comments.")

        # 6b: nested replies (parent_id IS NOT NULL) — parents now exist
        sq.execute(
            "SELECT id, text, created_at, ticket_id, user_id, parent_id "
            "FROM comments WHERE parent_id IS NOT NULL ORDER BY id"
        )
        nested = sq.fetchall()
        for r in nested:
            pg.execute(
                "INSERT INTO comments (id, text, created_at, ticket_id, user_id, parent_id) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                (r["id"], r["text"], r["created_at"],
                 r["ticket_id"], r["user_id"], r["parent_id"])
            )
            total_inserted += 1
        log(f"  Inserted {len(nested)} nested reply comments.")

        log(f"\n--- ALL INSERTS COMPLETE: {total_inserted} total rows inserted ---")

        # =====================================================================
        # POST-INSERT VALIDATION (within the same transaction)
        # =====================================================================
        log("\n--- POST-INSERT VALIDATION ---")

        expected_counts = {
            "slas":                   4,
            "teams":                  5,
            "team_mappings":          4,
            "users":                 13,
            "tickets":               24,
            "projects":               3,
            "project_team":           7,
            "ticket_status_history": 91,
            "comments":               8,
            "notifications":         98,  # 99 in SQLite; 1 orphan (user_id=14) intentionally skipped
            "reopen_requests":        2,
            "csat_feedbacks":         4,
            "activity_logs":        106,
            "announcements":          3,
            "events":                 4,
            "messages":               8,
        }

        all_counts_valid = True
        for table, expected in expected_counts.items():
            pg.execute(f'SELECT COUNT(*) FROM "{table}"')
            actual = pg.fetchone()[0]
            ok = actual == expected
            if not ok:
                all_counts_valid = False
            log(f"  [{'PASS' if ok else 'FAIL'}]  {table}: "
                f"expected={expected}, actual={actual}")

        if not all_counts_valid:
            abort(pg_conn,
                  "Row count validation FAILED — rolling back entire migration.",
                  code=2)

        # FK spot checks
        log("\n  FK integrity checks...")

        # Orphaned tickets
        pg.execute(
            "SELECT COUNT(*) FROM tickets t "
            "LEFT JOIN users u ON t.created_by_id = u.id WHERE u.id IS NULL"
        )
        c = pg.fetchone()[0]
        log(f"  [{'PASS' if c==0 else 'FAIL'}]  Orphaned tickets.created_by_id: {c}")
        if c != 0:
            abort(pg_conn, "Orphaned ticket FK. Rolling back.", code=2)

        # Orphaned comments
        pg.execute(
            "SELECT COUNT(*) FROM comments c "
            "LEFT JOIN tickets t ON c.ticket_id = t.id WHERE t.id IS NULL"
        )
        c = pg.fetchone()[0]
        log(f"  [{'PASS' if c==0 else 'FAIL'}]  Orphaned comments.ticket_id: {c}")
        if c != 0:
            abort(pg_conn, "Orphaned comment FK. Rolling back.", code=2)

        # Nested comments parents exist
        pg.execute(
            "SELECT COUNT(*) FROM comments c "
            "LEFT JOIN comments p ON c.parent_id = p.id "
            "WHERE c.parent_id IS NOT NULL AND p.id IS NULL"
        )
        c = pg.fetchone()[0]
        log(f"  [{'PASS' if c==0 else 'FAIL'}]  Orphaned nested comment parents: {c}")
        if c != 0:
            abort(pg_conn, "Nested comment parent missing. Rolling back.", code=2)

        # Admin user present with correct id
        pg.execute("SELECT id, role FROM users WHERE id = 2")
        row = pg.fetchone()
        admin_ok = row is not None and row[1] == "ADMIN"
        log(f"  [{'PASS' if admin_ok else 'FAIL'}]  Admin user id=2 role=ADMIN present: {admin_ok}")
        if not admin_ok:
            abort(pg_conn, "Admin user check FAILED. Rolling back.", code=2)

        # Alembic revision untouched
        pg.execute("SELECT version_num FROM alembic_version")
        rev = pg.fetchone()[0]
        rev_ok = rev == "b4d1e7f23a09"
        log(f"  [{'PASS' if rev_ok else 'FAIL'}]  Alembic revision: {rev}")
        if not rev_ok:
            abort(pg_conn, "Alembic revision changed! Rolling back.", code=2)

        log("\n  --- ALL VALIDATION CHECKS PASSED ---")

        # =====================================================================
        # SEQUENCE RESETS (within same transaction, after all inserts)
        # =====================================================================
        log("\n--- RESETTING POSTGRESQL SEQUENCES ---")
        sequences = [
            ("slas_id_seq",                   "slas"),
            ("teams_id_seq",                  "teams"),
            ("team_mappings_id_seq",           "team_mappings"),
            ("users_id_seq",                  "users"),
            ("tickets_id_seq",                "tickets"),
            ("projects_id_seq",               "projects"),
            ("ticket_status_history_id_seq",  "ticket_status_history"),
            ("comments_id_seq",               "comments"),
            ("notifications_id_seq",          "notifications"),
            ("reopen_requests_id_seq",        "reopen_requests"),
            ("csat_feedbacks_id_seq",         "csat_feedbacks"),
            ("activity_logs_id_seq",          "activity_logs"),
            ("announcements_id_seq",          "announcements"),
            ("events_id_seq",                 "events"),
            ("messages_id_seq",               "messages"),
        ]
        for seq_name, table_name in sequences:
            pg.execute(
                f"SELECT setval('{seq_name}', (SELECT MAX(id) FROM \"{table_name}\"))"
            )
            new_val = pg.fetchone()[0]
            log(f"  {seq_name} -> {new_val}")

        log("  project_team: no id column, no sequence — skipped.")

        # =====================================================================
        # COMMIT
        # =====================================================================
        pg_conn.commit()

        print("\n" + "=" * 65)
        log("  COMMIT SUCCESSFUL")
        log(f"  Total rows inserted: {total_inserted}")
        log("  SQLite: NOT modified.")
        log("  Alembic revision: b4d1e7f23a09 (unchanged).")
        print("=" * 65)

    except Exception as e:
        abort(pg_conn, f"Unexpected error: {type(e).__name__}: {e}", code=2)

    finally:
        try:
            sq_conn.close()
        except Exception:
            pass
        try:
            pg_conn.close()
        except Exception:
            pass

    sys.exit(0)


if __name__ == "__main__":
    main()
