from flask import Blueprint, jsonify, request
from app.models.ticket import Ticket
from app.models.ticket_status_history import TicketStatusHistory
from app.core.database import db
from app.core.constants import TicketStatus
from app.utils.time_utils import utcnow
from app.services.notification_service import NotificationService
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

webhook_bp = Blueprint('webhooks', __name__, url_prefix='/api/v1/github')

@webhook_bp.route('/webhook', methods=['POST'])
def github_webhook():
    event_type = request.headers.get('X-GitHub-Event', 'pull_request')
    payload = request.json or {}
    
    if event_type != 'pull_request':
        return jsonify({"status": "ignored", "reason": f"Unhandled event type {event_type}"}), 200
        
    action = payload.get('action')
    pr = payload.get('pull_request', {})
    
    if action == 'closed' and pr.get('merged') is True:
        pr_url = pr.get('html_url')
        if not pr_url:
            return jsonify({"status": "ignored", "reason": "No PR HTML URL"}), 200
            
        ticket = Ticket.query.filter_by(github_pr_url=pr_url).first()
        if not ticket:
            return jsonify({"status": "ignored", "reason": f"No ticket linked to PR {pr_url}"}), 200
            
        if ticket.status in [TicketStatus.RESOLVED, TicketStatus.CLOSED]:
            return jsonify({"status": "ignored", "reason": f"Ticket {ticket.id} already resolved or closed"}), 200
            
        old_status = ticket.status
        ticket.status = TicketStatus.RESOLVED
        
        merged_at_str = pr.get('merged_at')
        if merged_at_str:
            if merged_at_str.endswith('Z'):
                merged_at_str = merged_at_str[:-1] + '+00:00'
            try:
                merged_at = datetime.fromisoformat(merged_at_str)
            except Exception:
                merged_at = utcnow()
        else:
            merged_at = utcnow()
            
        ticket.updated_at = merged_at
        
        history = TicketStatusHistory(
            ticket_id=ticket.id,
            old_status=old_status,
            new_status=TicketStatus.RESOLVED,
            changed_by_id=None,
            changed_at=merged_at
        )
        db.session.add(history)
        db.session.commit()
        
        try:
            NotificationService.notify_status_change(ticket, old_status, TicketStatus.RESOLVED)
        except Exception as e:
            logger.error(f"Failed to notify status change for webhook: {e}")
            
        try:
            old_status_val = old_status.value if hasattr(old_status, 'value') else str(old_status)
            NotificationService.broadcast_live_activity(
                category="status_change",
                ticket_id=ticket.id,
                message=f"Ticket T-{1000 + ticket.id} resolved via GitHub PR Merge: {pr_url}",
                created_by="GitHub Webhook"
            )
        except Exception as e:
            logger.error(f"Failed to broadcast webhook status change: {e}")
            
        return jsonify({"status": "success", "ticket_id": ticket.id, "new_status": "Resolved"}), 200
        
    return jsonify({"status": "ignored", "reason": f"Action {action} or merged status unhandled"}), 200
