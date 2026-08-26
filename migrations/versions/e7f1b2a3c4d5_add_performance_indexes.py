"""add_performance_indexes

Revision ID: e7f1b2a3c4d5
Revises: b4d1e7f23a09
Create Date: 2026-08-26 19:41:00.000000

Purpose:
    Adds database indexes on foreign keys, status/priority fields, and created_at timestamps
    to eliminate full table sequential scans in PostgreSQL (Neon) and optimize join/filter queries.

Indexes added:
    - tickets: created_by_id, assigned_to_id, team_id, status, priority, is_demo, created_at
    - comments: ticket_id, user_id, created_at
    - ticket_status_history: ticket_id, changed_at
    - notifications: user_id, is_read, created_at
    - csat_feedbacks: user_id, created_at
    - reopen_requests: ticket_id, requested_by_id, status, requested_at
    - events: created_by_id, is_demo, start_time, created_at
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e7f1b2a3c4d5'
down_revision = 'b4d1e7f23a09'
branch_labels = None
depends_on = None


def upgrade():
    # Tickets indexes
    op.create_index('ix_tickets_created_by_id', 'tickets', ['created_by_id'], unique=False, if_not_exists=True)
    op.create_index('ix_tickets_assigned_to_id', 'tickets', ['assigned_to_id'], unique=False, if_not_exists=True)
    op.create_index('ix_tickets_team_id', 'tickets', ['team_id'], unique=False, if_not_exists=True)
    op.create_index('ix_tickets_status', 'tickets', ['status'], unique=False, if_not_exists=True)
    op.create_index('ix_tickets_priority', 'tickets', ['priority'], unique=False, if_not_exists=True)
    op.create_index('ix_tickets_is_demo', 'tickets', ['is_demo'], unique=False, if_not_exists=True)
    op.create_index('ix_tickets_created_at', 'tickets', ['created_at'], unique=False, if_not_exists=True)

    # Comments indexes
    op.create_index('ix_comments_ticket_id', 'comments', ['ticket_id'], unique=False, if_not_exists=True)
    op.create_index('ix_comments_user_id', 'comments', ['user_id'], unique=False, if_not_exists=True)
    op.create_index('ix_comments_created_at', 'comments', ['created_at'], unique=False, if_not_exists=True)

    # Ticket Status History indexes
    op.create_index('ix_ticket_status_history_ticket_id', 'ticket_status_history', ['ticket_id'], unique=False, if_not_exists=True)
    op.create_index('ix_ticket_status_history_changed_at', 'ticket_status_history', ['changed_at'], unique=False, if_not_exists=True)

    # Notifications indexes
    op.create_index('ix_notifications_user_id', 'notifications', ['user_id'], unique=False, if_not_exists=True)
    op.create_index('ix_notifications_is_read', 'notifications', ['is_read'], unique=False, if_not_exists=True)
    op.create_index('ix_notifications_created_at', 'notifications', ['created_at'], unique=False, if_not_exists=True)

    # CSAT Feedbacks indexes
    op.create_index('ix_csat_feedbacks_user_id', 'csat_feedbacks', ['user_id'], unique=False, if_not_exists=True)
    op.create_index('ix_csat_feedbacks_created_at', 'csat_feedbacks', ['created_at'], unique=False, if_not_exists=True)

    # Reopen Requests indexes
    op.create_index('ix_reopen_requests_ticket_id', 'reopen_requests', ['ticket_id'], unique=False, if_not_exists=True)
    op.create_index('ix_reopen_requests_requested_by_id', 'reopen_requests', ['requested_by_id'], unique=False, if_not_exists=True)
    op.create_index('ix_reopen_requests_status', 'reopen_requests', ['status'], unique=False, if_not_exists=True)
    op.create_index('ix_reopen_requests_requested_at', 'reopen_requests', ['requested_at'], unique=False, if_not_exists=True)

    # Events indexes
    op.create_index('ix_events_created_by_id', 'events', ['created_by_id'], unique=False, if_not_exists=True)
    op.create_index('ix_events_is_demo', 'events', ['is_demo'], unique=False, if_not_exists=True)
    op.create_index('ix_events_start_time', 'events', ['start_time'], unique=False, if_not_exists=True)
    op.create_index('ix_events_created_at', 'events', ['created_at'], unique=False, if_not_exists=True)


def downgrade():
    op.drop_index('ix_events_created_at', table_name='events', if_exists=True)
    op.drop_index('ix_events_start_time', table_name='events', if_exists=True)
    op.drop_index('ix_events_is_demo', table_name='events', if_exists=True)
    op.drop_index('ix_events_created_by_id', table_name='events', if_exists=True)

    op.drop_index('ix_reopen_requests_requested_at', table_name='reopen_requests', if_exists=True)
    op.drop_index('ix_reopen_requests_status', table_name='reopen_requests', if_exists=True)
    op.drop_index('ix_reopen_requests_requested_by_id', table_name='reopen_requests', if_exists=True)
    op.drop_index('ix_reopen_requests_ticket_id', table_name='reopen_requests', if_exists=True)

    op.drop_index('ix_csat_feedbacks_created_at', table_name='csat_feedbacks', if_exists=True)
    op.drop_index('ix_csat_feedbacks_user_id', table_name='csat_feedbacks', if_exists=True)

    op.drop_index('ix_notifications_created_at', table_name='notifications', if_exists=True)
    op.drop_index('ix_notifications_is_read', table_name='notifications', if_exists=True)
    op.drop_index('ix_notifications_user_id', table_name='notifications', if_exists=True)

    op.drop_index('ix_ticket_status_history_changed_at', table_name='ticket_status_history', if_exists=True)
    op.drop_index('ix_ticket_status_history_ticket_id', table_name='ticket_status_history', if_exists=True)

    op.drop_index('ix_comments_created_at', table_name='comments', if_exists=True)
    op.drop_index('ix_comments_user_id', table_name='comments', if_exists=True)
    op.drop_index('ix_comments_ticket_id', table_name='comments', if_exists=True)

    op.drop_index('ix_tickets_created_at', table_name='tickets', if_exists=True)
    op.drop_index('ix_tickets_is_demo', table_name='tickets', if_exists=True)
    op.drop_index('ix_tickets_priority', table_name='tickets', if_exists=True)
    op.drop_index('ix_tickets_status', table_name='tickets', if_exists=True)
    op.drop_index('ix_tickets_team_id', table_name='tickets', if_exists=True)
    op.drop_index('ix_tickets_assigned_to_id', table_name='tickets', if_exists=True)
    op.drop_index('ix_tickets_created_by_id', table_name='tickets', if_exists=True)
