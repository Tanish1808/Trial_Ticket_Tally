from flask import Blueprint, jsonify
from app.middleware.auth_middleware import role_required, token_required
from app.core.constants import UserRole, TicketStatus
from app.models.ticket import Ticket
from app.models.user import User

analytics_bp = Blueprint('analytics', __name__, url_prefix='/api/v1/analytics')

@analytics_bp.route('/dashboard', methods=['GET'])
@role_required([UserRole.ADMIN])
def get_dashboard_stats():
    from app.core.database import db
    from sqlalchemy import func
    from datetime import datetime, timedelta

    # 1. Ticket Status Counts (Efficient Group By)
    status_counts = db.session.query(Ticket.status, func.count(Ticket.id)).group_by(Ticket.status).all()
    status_map = {s: c for s, c in status_counts}
    
    # Safe mapping helper
    def get_count(status_enum):
        return status_map.get(status_enum, 0)

    today_date = datetime.utcnow().date()
    resolved_today = Ticket.query.filter(
        Ticket.status == TicketStatus.RESOLVED,
        func.date(Ticket.updated_at) == today_date
    ).count()

    total_tickets = Ticket.query.count()
    open_tickets = get_count(TicketStatus.OPEN)
    in_progress_tickets = get_count(TicketStatus.IN_PROGRESS)
    resolved_tickets = get_count(TicketStatus.RESOLVED)
    users_count = User.query.count()
    
    # 2. Category Distribution
    cat_counts = db.session.query(Ticket.category, func.count(Ticket.id)).group_by(Ticket.category).all()
    categories = {cat or "Uncategorized": count for cat, count in cat_counts}
        
    # 3. Priority Breakdown
    prio_counts = db.session.query(Ticket.priority, func.count(Ticket.id)).group_by(Ticket.priority).all()
    priorities = {prio.value: count for prio, count in prio_counts}

    # 4. Trends (Last 7 days)
    # Only fetch tickets modified or created in last 7 days to reduce load
    today = datetime.utcnow().date()
    seven_days_ago = today - timedelta(days=7)
    
    # We need tickets created recently OR resolved recently
    # To keep identical logic to before (iterating all), we can optimize by filtering
    # But for exact parity with previous logic, we need to check all tickets?
    # No, previous logic checked 'if 0 <= days_ago < 7'. 
    # So we ONLY need tickets where created_at or updated_at is >= 7 days ago.
    
    relevant_tickets = Ticket.query.filter(
        (Ticket.created_at >= seven_days_ago) | 
        (Ticket.updated_at >= seven_days_ago)
    ).all()

    dates = [(today - timedelta(days=i)).isoformat() for i in range(6, -1, -1)]
    created_trend = [0] * 7
    resolved_trend = [0] * 7
    
    for t in relevant_tickets:
        if t.created_at:
            t_date = t.created_at.date()
            days_ago = (today - t_date).days
            if 0 <= days_ago < 7:
                created_trend[6 - days_ago] += 1
                
        if t.status == TicketStatus.RESOLVED and t.updated_at:
             t_date = t.updated_at.date()
             days_ago = (today - t_date).days
             if 0 <= days_ago < 7:
                 resolved_trend[6 - days_ago] += 1

    return jsonify({
        "total_tickets": total_tickets,
        "open_tickets": open_tickets,
        "in_progress_tickets": in_progress_tickets,
        "resolved_tickets": resolved_tickets,
        "resolved_today": resolved_today,
        "total_users": users_count,
        "categories": categories,
        "priorities": priorities,
        "trends": {
            "dates": dates,
            "created": created_trend,
            "resolved": resolved_trend
        }
    })

@analytics_bp.route('/it-dashboard', methods=['GET'])
@token_required
def get_it_dashboard_stats():
    from app.core.database import db
    from sqlalchemy import func, or_
    from datetime import datetime, timedelta
    from flask import g
    from app.models.ticket import Ticket
    from app.core.constants import TicketStatus, TicketPriority, UserRole

    user = g.user
    today_date = datetime.utcnow().date()
    
    # Base query for the user's scope (Team or All if no team)
    query = Ticket.query
    if user.role == UserRole.IT_STAFF and user.team_id:
        query = query.filter(or_(Ticket.team_id == user.team_id, Ticket.assigned_to_id == user.id))
    
    # 1. Assigned to Team (Active: Open or In Progress)
    assigned_to_team = query.filter(Ticket.status.in_([TicketStatus.OPEN, TicketStatus.IN_PROGRESS])).count()
    
    # 2. In Progress
    in_progress = query.filter(Ticket.status == TicketStatus.IN_PROGRESS).count()
    
    # 3. Resolved Today
    resolved_today = query.filter(
        Ticket.status == TicketStatus.RESOLVED,
        func.date(Ticket.updated_at) == today_date
    ).count()
    
    # 4. SLA Breaches
    # SLA: Critical > 4h, High > 8h
    critical_breach_time = datetime.utcnow() - timedelta(hours=4)
    high_breach_time = datetime.utcnow() - timedelta(hours=8)
    
    sla_breaches = query.filter(
        Ticket.status.in_([TicketStatus.OPEN, TicketStatus.IN_PROGRESS]),
        or_(
            (Ticket.priority == TicketPriority.CRITICAL) & (Ticket.created_at <= critical_breach_time),
            (Ticket.priority == TicketPriority.HIGH) & (Ticket.created_at <= high_breach_time)
        )
    ).count()

    # 5. Weekly Performance Trends (Assigned vs Resolved)
    # Get last 7 days dates
    # 5. Weekly Performance Trends (Assigned vs Resolved)
    # Get last 7 days dates
    dates = [(today_date - timedelta(days=i)).isoformat() for i in range(6, -1, -1)]
    assigned_trend = [0] * 7
    resolved_trend = [0] * 7

    seven_days_ago = today_date - timedelta(days=7)
    
    # Re-use base query filter logic but applying date range
    trend_tickets = query.filter(
        (Ticket.created_at >= seven_days_ago) | 
        ((Ticket.updated_at >= seven_days_ago) & (Ticket.status == TicketStatus.RESOLVED))
    ).all()
    
    for t in trend_tickets:
        if t.created_at:
            t_date = t.created_at.date()
            days_ago = (today_date - t_date).days
            if 0 <= days_ago < 7:
               assigned_trend[6 - days_ago] += 1
        
        if t.status == TicketStatus.RESOLVED and t.updated_at:
            t_date = t.updated_at.date()
            days_ago = (today_date - t_date).days
            if 0 <= days_ago < 7:
               resolved_trend[6 - days_ago] += 1

    return jsonify({
        "assigned_tickets": assigned_to_team,
        "in_progress_tickets": in_progress,
        "resolved_tickets": resolved_today,
        "sla_breaches": sla_breaches,
        "weekly_activity": {
            "dates": dates,
            "assigned": assigned_trend,
            "resolved": resolved_trend
        }
    })

